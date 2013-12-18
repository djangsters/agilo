# -*- encoding: utf-8 -*-
#   Copyright 2009 Agile42 GmbH, Berlin (Germany)
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
#   
#   Authors:
#        - Felix Schwarz <felix.schwarz__at__agile42.com>

from trac.test import Mock

from agilo.test import AgiloTestCase
from agilo.utils.compat import json
from agilo.utils.json_client import JSONDecodeError, ServerProxy

class ServerProxyTest(AgiloTestCase):
    
    def setUp(self):
        self.super()
        self.hostname = 'foo.example.com'
        self.path = '/json'
        self.base_url = self.hostname + self.path
        self.transport = Mock(request=self._echo_request_function)
        self.server = ServerProxy('http://' + self.base_url, 
                                  transport=self.transport)
    
    def _build_response(self, data, status=200, method=None, headers=None):
        data = list(data) + [method, headers]
        return Mock(status=status, read=lambda: json.dumps(data))
    
    def _echo_request_function(self, *args, **kwargs):
        return self._build_response(args, **kwargs)
    
    def test_serverproxy_can_chain_requests(self):
        params = dict(name='baz', value='quux')
        response = self.server.foo.bar.get(**params)
        self.assert_equals(self.hostname, response[0])
        self.assert_equals('%s/foo/bar' % self.path, response[1])
        self.assert_equals(params, response[2])
    
    def test_serverproxy_can_use_getitem_for_path_components(self):
        response = self.server.foo['bar'].baz.get()
        self.assert_equals('%s/foo/bar/baz' % self.path, response[1])
    
    def test_getitem_can_deal_with_int_for_path_components(self):
        response = self.server.foo[5].baz.get()
        self.assert_equals('%s/foo/5/baz' % self.path, response[1])
    
    def test_dont_append_slash_if_uri_ends_with_slash_already(self):
        # Check that a protocoll specification is not necessary - http will be
        # assumed
        new_hostname = self.base_url + '/'
        self.server = ServerProxy(new_hostname, transport=self.transport)
        params = dict(name='baz', value='quux')
        response = self.server.foo.bar.get(**params)
        self.assert_equals('%s/foo/bar' % self.path, response[1])
        self.assert_equals(params, response[2])
    
    def test_transport_get_authentication_data_if_provided(self):
        self.server = ServerProxy(self.base_url, transport=self.transport,
                                  username='f0o', password='b4r')
        params = dict(key='value')
        response = self.server.foo.bar.get(**params)
        self.assert_equals(params, response[2])
        headers = response[4]
        self.assert_equals('Basic ZjBvOmI0cg==\n', headers['AUTHORIZATION'])
    
    def test_transport_drops_invalid_json_response_from_server(self):
        fake_response = Mock(status=200, read=lambda: '')
        transport = Mock(request=lambda *args, **kwargs: fake_response)
        server = ServerProxy('http://' + self.base_url, transport=transport)
        self.assert_raises(JSONDecodeError, server.foo.bar.get, foo='bar')
    
    def test_can_specify_request_method(self):
        response = self.server.foo.get()
        self.assert_equals('%s/foo' % self.path, response[1])
        self.assert_equals('GET', response[3])
        
        self.assert_equals('POST', self.server.foo.post()[3])
    
    def test_can_add_arguments_in_get_and_post(self):
        self.assert_equals({'bar': '42'}, self.server.foo.get(bar='42')[2])
        self.assert_equals({'bar': '42'}, self.server.foo.post(bar='42')[2])
    
    def test_can_get_response_object(self):
        response = self.server.foo.get_json_with_response()
        self.assert_true(hasattr(response[1], 'read'))
        self.assert_equals(2, len(response))


