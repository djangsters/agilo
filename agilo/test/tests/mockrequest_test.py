# -*- encoding: utf-8 -*-
#   Copyright 2010 Agile42 GmbH, Berlin (Germany)
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


from agilo.test import AgiloTestCase

class MockRequestTest(AgiloTestCase):
    
    def setUp(self):
        self.super()
        self.body = 'this is a request body'
    
    def _request(self):
        req = self.teh.mock_request(request_body=self.body)
        return req

    def test_has_read_method(self):
        req = self.teh.mock_request()
        self.assert_equals('', req.read())
    
    def test_can_read_request_body(self):
        self.assert_equals(self.body, self._request().read())
    
    def test_has_get_header_method(self):
        req = self.teh.mock_request()
        self.assert_true(hasattr(req, 'get_header'))
        self.assert_true(callable(req.get_header))

    def test_header_names_are_case_insensitive(self):
        self.assert_equals(str(len(self.body)), self._request().get_header('contEnt-lEngth'))

    def test_content_length_is_set_automatically(self):
        self.assert_equals(str(len(self.body)), self._request().get_header('content-length'))

    def test_get_header_behaves_like_trac_request_if_header_not_sent(self):
        self.assert_none(self._request().get_header('fnord'))

