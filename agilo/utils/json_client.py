# -*- encoding: utf-8 -*-
#   Copyright 2009-2010 Agile42 GmbH, Berlin (Germany)
#   Copyright 2011 Agilo Software GmbH All rights reserved
#   
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#   
#       http://www.apache.org/licenses/LICENSE-2.0
#   
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import base64
from Cookie import SimpleCookie
import httplib
import urllib

from trac.web.api import HTTPException, HTTPUnauthorized

from agilo.api import ValueObject
from agilo.utils.compat import json

__all__ = ['GenericHTTPException', 'JSONDecodeError', 'ServerProxy']


class JSONDecodeError(Exception):
    """Raised when decoding of JSON data failed."""
    pass


class HTTPJSONTransport(object):
    
    def request(self, hostname, path, parameters, headers=None, method='POST'):
        """Perform a HTTP request to the server and return the response object.
        If headers were given, add these to the request."""
        json_data = json.dumps(parameters)
        server = httplib.HTTPConnection(hostname)
        server.connect()
        if method == 'POST':
            # For HTTP POST all request bodies must end with \r\n
            json_data += '\r\n'
        if not headers:
            headers = {}
        # Also add standard JSON headers to the request, so that will be usable 
        # also from other frameworks like Django
        headers.update(dict(X_REQUESTED_WITH='XMLHttpRequest',
                            ACCEPT='application/json'))
        server.request(method, path, json_data, headers=headers)
        return server.getresponse()

class JSONCall(object):
    
    def __init__(self, req_method, names):
        self._req_method = req_method
        self._names = names
    
    def __getattr__(self, name):
        self._names.append(name)
        return JSONCall(self._req_method, self._names)
    
    def __getitem__(self, name):
        return getattr(self, str(name))
    
    def get(self, **kwargs):
        return self._req_method(self._names, kwargs, method='GET')
    
    def get_json_with_response(self, **kwargs):
        return self._req_method(self._names, kwargs, method='GET', return_response=True)
    
    def post(self, **kwargs):
        return self._req_method(self._names, kwargs, method='POST')
    
    def put(self, **kwargs):
        return self._req_method(self._names, kwargs, method='PUT')


class GenericHTTPException(HTTPException):
    def __init__(self, code, detail, *args):
        self.code = code
        self.reason = None
        HTTPException.__init__(self, detail, *args)


class ServerProxy(object):
    
    def __init__(self, uri, transport=None, username=None, password=None):
        self._protocol, self._hostname, self._path = self._get_target(uri)
        if transport is None:
            transport = HTTPJSONTransport()
        self._transport = transport
        self._username = username
        self._password = password
        self._session_id = None
        self.filename_for_errors = None
    
    def _get_target(self, uri):
        protocol, uri = urllib.splittype(uri)
        assert protocol in [None, 'http', 'https']
        if protocol is None:
            uri = '//' + uri
        hostname, path = urllib.splithost(uri)
        if not path.endswith('/'):
            path += '/'
        return (protocol, hostname, path)
    
    def save_errors_to_file(self, filename):
        self.filename_for_errors = filename
    
    def set_username(self, username):
        self._username = username
    
    def set_password(self, password):
        self._password = password
    
    def set_session_id(self, session_id):
        self._session_id = session_id
    
    def _save_error_message(self, error_message):
        if self.filename_for_errors is not None:
            file(self.filename_for_errors, 'wb').write(error_message)
            #print 'Output for error written to ', self.filename_for_errors
    
    def _build_authorization_headers(self, username, password, session_id):
        """Adds the HTTP header for HTTP basic authentication if username and
        password were given."""
        headers = dict()
        if session_id is not None:
            cookie = SimpleCookie()
            cookie['trac_auth'] = session_id
            header_value = cookie.output(header='').strip()
            headers['Cookie'] = header_value
        elif username is not None and password is not None:
            userinfo = base64.encodestring('%s:%s' % (username, password))
            header_value = 'Basic ' + userinfo
            # Case matters for trac!
            headers['AUTHORIZATION'] = header_value
        return headers
    
    def _wrap_in_valueobjects(self, json_data):
        if isinstance(json_data, dict):
            return ValueObject(json_data)
        elif isinstance(json_data, list):
            return map(self._wrap_in_valueobjects, json_data)
        return json_data
    
    def _decode_json(self, data):
        try:
            decoded_json = json.loads(data)
        except Exception, e:
            # We can wrap the exception here because the traceback is not 
            # very interesting for us. Either it is a problem within simplejson
            # or something is wrong with the data.
            raise JSONDecodeError(unicode(e) + ' - undecodable json: ' + repr(data))
        return self._wrap_in_valueobjects(decoded_json)
    
    def _request_from_server(self, path, parameters, method):
        headers = self._build_authorization_headers(self._username, self._password, self._session_id)
        response = self._transport.request(self._hostname, path, parameters, 
            headers=headers, method=method)
        return response
    
    def get_json_from_request(self, path_components, parameters, method='POST', 
                              return_response=False):
        path = self._path + '/'.join(path_components)
        response = self._request_from_server(path, parameters, method)
        is_redirect = (300 <= response.status and response.status < 400)
        is_error = (response.status != 200 and not is_redirect)
        
        json_data = 'null'
        if not is_redirect:
            json_data = response.read()
        if is_error:
            self._save_error_message(json_data)
        if response.status == 401:
            # FIXME(AT): This exception is not existing in trac.web.api??
            raise HTTPUnauthorized(json_data)
        elif response.status != 200 and not is_redirect:
            raise GenericHTTPException(response.status, json_data)
        decoded_json = self._decode_json(json_data)
        if return_response:
            return (decoded_json, response)
        return decoded_json
    
    def __getattr__(self, name):
        return JSONCall(self.get_json_from_request, [name])

# TODO: We can make a MasterServer object that fetches the master URL from the
# config and checks for valid paths

