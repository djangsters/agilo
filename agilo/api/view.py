#   Copyright 2007 Andrea Tomasini <andrea.tomasini__at__agile42.com>
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
#
#   Authors:
#        - Andrea Tomasini <andrea.tomasini__at__agile42.com>
"""
Module containing all the API definitions to display result of a processed
request to the caller. The View is in charge of adapting the response data
to the specific client media requesting the information and managing the 
error display and handling with the client. A view should receive events
from the controller when the processing is finished.
"""
import cgi
import re
import urlparse
import sys
import cPickle

from trac.core import Component, ComponentMeta, ExtensionPoint, Interface, implements, TracError
from trac.web import IRequestHandler, chrome, RequestDone
from trac.util.text import unicode_unquote
from trac.util import datefmt

from agilo.api.controller import ValueObject, ICommand
from agilo.utils import days_time, log
from agilo.utils.compat import exception_to_unicode, json
from agilo.utils.web_ui import url_encode, url_decode

AGILO_PAGE_DATA = 'agilo_page_data'

# Utility function to perform localization and date shift from UTC
# based on the timezone which is in the request. This is a closure
# that returns the right conversion method
def generate_converter(tz_info):
    """Creates a function to convert a given datetime in UTC to the
    set timezone"""
    def convert_date(datetime_utc):
        """Returns the date converted in the locale format with the
        right timezone"""
        return datefmt.format_datetime(datetime_utc, tzinfo=tz_info)
    return convert_date


class IView(Interface):
    """Represent a generic View in charge of collecting input from a 
    specific channel/device, and after having processed it via a 
    controller has to display back the output"""
    def controller(self):
        """Must return a reference to the controller in charge of 
        processing data for this view. Normally it is a read only 
        property."""


# TODO: may be to lines of comment would help a bit here... ;-)
class IHTTPViewRequestFilter(Interface):
    def pre_process_request(self, req):
        pass
    
    def post_process_request(self, req):
        pass

# TODO: may be to lines of comment would help a bit here... ;-)
class HTTPViewRequestFilterCreationMeta(ComponentMeta):
    def __new__(cls, name, bases, class_attrs):
        interface_class = cls.create_request_filter(name)
        class_attrs['filters'] = ExtensionPoint(interface_class)
        new_class = super(HTTPViewRequestFilterCreationMeta, cls).__new__(cls, name, bases, class_attrs)
        
        setattr(sys.modules[new_class.__module__], interface_class.__name__, interface_class)
        return new_class
    
    @classmethod
    def create_request_filter(cls, class_name):
        interface_name = cls.filter_extension_point_classname(class_name)
        interface_class = type(interface_name, (IHTTPViewRequestFilter,), {})
        return interface_class
    
    @classmethod
    def filter_extension_point_classname(cls, class_name):
        return 'I%sRequestFilter' % class_name


class HTTPView(Component):
    """Represent a HTTP view, will have to take care of properly 
    display data to the client as well as managing errors display."""
    
    __metaclass__ = HTTPViewRequestFilterCreationMeta
    
    implements(IView, IRequestHandler)
    abstract = True
    # replace with the base URL at which this view is reachable, will be used
    # in the match_request method. If you need more complex URL matching than
    # override the standard match_request method
    url = None
    # Place here the name of the template file that this view is using
    template = None
    # Place here the class of the Controller that this view is using to talk
    # with the Model
    controller_class = None
    
    @property
    def controller(self):
        """Returns the controller in charge of this view"""
        if not hasattr(self, '_controller') or not self._controller:
            self._controller = self.controller_class(self.env)
        return self._controller
    
    # IRequestHandler methods
    def match_request(self, req):
        """A generic match_request implementation that uses self.url 
        and self.url_regex as well the as the request method to decide 
        if this view can handle the given request.
        If url_regex is not available, it returns true if the current 
        path starts with self.url
        
        All named match groups will be put as key in req.args, so be 
        aware not to use the same name as real form paramaters!!!"""
        if self.get_handler(req):
            if hasattr(self, 'url_regex'):
                url_pattern = '^' + self.url + self.url_regex
                match = re.search(url_pattern, req.path_info)
                if match is not None:
                    for key, value in match.groupdict().iteritems():
                        req.args[key] = value
                    return True
            elif req.path_info.startswith(self.url):
                return True
    
    def _call_filters_and_handler(self, req, handler):
        for filter in self.filters:
            filter.pre_process_request(req)
        data = handler(req) or {}
        for filter in self.filters:
            filter.post_process_request(req)
        return self.respond(data)
    
    def process_request(self, req):
        """Process the HTTP Requests and validate parameters, at least 
        basically, than send a Command Request to a Controller. The 
        response has to be rendered according to the view needs."""
        try:
            handler = self.get_handler(req)
            if handler is not None:
                return self._call_filters_and_handler(req, handler)
            else:
                raise TracError('No handler found for method %s' % req.method)
        except ICommand.NotValidError, e:
            chrome.add_warning(req, unicode(e))
            # not that we update the data, so that the set value are
            # kept safe for re-displaying a page correctly
            data = self.get_data_from_session(req)
            data.update({'error': unicode(e)})
            # This will allow to show the wrong field in a different
            # color or mark them as errors
            data.update({'errors': e.command_attributes.keys()})
            return self.respond(data)
        except ICommand.CommandError, e:
            raise TracError(unicode(e))
    
    def get_handler(self, req):
        """Return the handler for this request method (or None if no 
        such method exists."""
        handler_name = 'do_%s' % req.method.lower()
        return getattr(self, handler_name, None)
    
    def _split_path_and_parameters(self, url_with_qs):
        """Return a tuple (path, dict with parameters) which were 
        extracted from the given url with query string. All parameters 
        are encoded as UTF-8 so that they can be used in req.href 
        directly."""
        # The problem is that href needs to get the path and the 
        # parameters separately but the data is already encoded in the 
        # url_with_qs 
        parsed_url = urlparse.urlsplit(url_with_qs)
        path, query_string = parsed_url[2], parsed_url[3]
        parameters = cgi.parse_qs(query_string)
        
        http_parameters = dict()
        for key, value in parameters.items():
            utf8_key = unicode(key).encode('utf-8')
            utf8_value = unicode(''.join(value)).encode('utf-8')
            http_parameters[utf8_key] = utf8_value
        return (path, http_parameters)
    
    def _parse_date_value(self, req, a_formatted_date):
        """Returns the datetime shifted to UTC timezone for the given
        formatted date."""
        if a_formatted_date:
            the_datetime = datefmt.parse_date(a_formatted_date, 
                                              tzinfo=req.tz)
            the_datetime = days_time.shift_to_utc(the_datetime)
            return the_datetime
    
    @classmethod
    def get_url(cls, req, *args, **kwargs):
        href = req.href(cls.url, '/'.join(args), **kwargs)
        return href
    
    def redirect(self, req, another_view, *args, **kwargs):
        """
        Redirects the HTTP Request to the given View class or to the
        redirect parameter url present in the request. The redirect
        request parameter should be relative to the application path,
        the unquote and url completion will be done automatically.
        """
        assert another_view.url, \
            "The view needs to have an url specified!"
        href = another_view.get_url(req, *args, **kwargs)
        redirect_url = req.args.get('redirect')
        if redirect_url:
            url_with_qs = unicode_unquote(redirect_url)
            if '?' in url_with_qs:
                path, parameters = \
                    self._split_path_and_parameters(url_with_qs)
                href = req.href(path, **parameters)
            else:
                # Do we need to do something special if the URL 
                # contains a path (not only one component)?
                path = url_with_qs
                href = req.href(path)
        req.redirect(href)
        
    def respond(self, data):
        """Respond to the HTTP request sending to the template engine 
        the given data"""
        if not self.template:
            raise TracError("The view (%s) needs to have a " \
                            "template!" % self.__class__.__name__)
        return self.template, data, None

    def store_data_in_session(self, req, data):
        """Stores the data in the session for reuse during a failed post 
        or an exception. This will allow to refill a form in case of wrong
        data without having the user to retype everything in"""
        if hasattr(req, 'session'):
            try:
                session_data = cPickle.dumps(data)
                req.session[AGILO_PAGE_DATA] = url_encode(session_data)
            except Exception, e:
                exception_to_unicode(e)
    
    def get_data_from_session(self, req):
        """Retrieves data from the session, and delete it"""
        if hasattr(req, 'session') and req.session.has_key(AGILO_PAGE_DATA):
            try:
                session_data = url_decode(req.session[AGILO_PAGE_DATA])
                data = cPickle.loads(session_data)
                del req.session[AGILO_PAGE_DATA]
                return data
            except Exception, e:
                exception_to_unicode(e)
        return {}


class JSONView(HTTPView):
    """Represent a JSON view which gets data from the client and sends back 
    JSON data."""
    
    abstract = True
    
    # IRequestHandler methods
    def match_request(self, req):
        """Returns true if the given request matches the URL at which this View 
        is reachable."""
        if req.path_info.startswith('/json'):
            return super(JSONView, self).match_request(req)
    
    def _load_json_data(self, http_body):
        try:
            data = json.loads(http_body)
        except Exception, e:
            msg = u'Received invalid JSON request %s' % \
                exception_to_unicode(e)
            log.warning(self, msg)
            data = None
        return data
    
    def process_request(self, req):
        call_handler = False
        
        if req.method in ('PUT', 'DELETE', 'POST'):
            if self._contains_data(req):
                http_body = req.read()
                data = dict(req.args)
                body_data = self._load_json_data(http_body)
                if body_data is not None:
                    # REFACT: consider to make the whole body available under a special key
                    # so we can send other types than dictionaries directly to the server and so
                    # we can distinguish between parameters from the url and parameters that where 
                    # sent from the body without reparsing it. (not sure if that would even be possible)
                    data.update(body_data)
                    call_handler = True
        else:
            # AT: we need to take even with data 0 cause the command
            # Get on /json/<models>/ is valid, has to return the list
            # of models
            data = req.args
            call_handler = (len(data) >= 0)
        
        if call_handler:
            code = 200
            try:
                response = self.get_handler(req)(req, data)
                if isinstance(response, tuple):
                    response, code = response
                self.respond(req, response, code=code)
            except Exception, e:
                if isinstance(e, RequestDone):
                    raise
                msg = exception_to_unicode(e)
                log.error(self, msg)
                self.error_response(req, {}, [msg])
        self.respond(req, {'msg': 'Bad request'}, code=400)
    
    
    def _contains_data(self, req):
        content_length = req.get_header('Content-Length')
        if content_length is not None:
            try:
                size = int(content_length)
            except (ValueError, TypeError):
                size = 0
            return (size > 0)
        return False
    
    def error_response(self, req, current_data, errors, code=500):
        json_response = {'current_data': current_data, 'errors': errors}
        self.respond(req, json_response, code)
    
    def exception_response(self, req, current_data, exception):
        self.error_response(req, current_data, [exception_to_unicode(exception)])
    
    # -------------------------------------------------------------------------
    # JSON protocol
    
    def as_json(self, data):
        return json.dumps(data)
    
    def dbobject_to_json(self, req, dbdata, typename, permissions):
        if hasattr(dbdata, 'as_dict'):
            dbdata = dbdata.as_dict()
        
        privileges = []
        for action_name in permissions:
            if req.perm.has_permission(action_name):
                privileges.append(action_name)
        json_data = dict(content_type=typename, content=ValueObject(dbdata), 
                         permissions=privileges,)
        return ValueObject(json_data)
    
    def list_to_json(self, req, dbdata_list, typename, dbdata_to_json, permissions=None):
        if permissions is None:
            permissions = []
        json_content_list = []
        for dbdata in dbdata_list:
            json_content_list.append(dbdata_to_json(req, dbdata, self))
        return dict(permissions=permissions, content_type=typename, content=json_content_list)
    
    # -------------------------------------------------------------------------
    # Custom View methods
    
    def get_handler(self, req):
        """Return the handler for this request method (or None if no such method
        exists."""
        handler_name = 'do_%s' % req.method.lower()
        return getattr(self, handler_name, None)
    
    def respond(self, req, data, code=200):
        """Respond to the JSON request by sending the JSON-encoded data back."""
        json_data = self.as_json(data)
        req.send_response(code)
        req.send_header('Content-Type', 'application/json')
        req.send_header('Content-Length', len(json_data))
        req.send_header('Expires', 'Thu, 01 Jan 1970 00:00:00 GMT')
        # HTTP/1.0 header
        req.send_header('Pragma', 'no-cache')
        # HTTP/1.1 header
        req.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
        req.write(json_data)
        raise RequestDone

