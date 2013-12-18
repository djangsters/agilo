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
#       - Martin Häcker <martin.haecker_at_agile42.com>


from agilo.test import AgiloTestCase

from agilo.utils.jquery_13_injector import JQuery13Injector, use_jquery_13


class JQuery13InjectorTest(AgiloTestCase):
    def setUp(self):
        self.super()
        self.req = self.mock_req()
    
    def mock_req(self, scripts=None):
        if scripts is None:
            scripts = [{'href':'foo/jquery.js'}]
        req = self.teh.mock_request()
        req.chrome['scripts'] = scripts
        return req
    
    def scripts(self):
        return self.req.chrome['scripts']
    
    def set_scripts(self, scripts=None):
        self.req = self.mock_req(scripts=scripts)
    
    def test_injector_is_its_own_object(self):
        injector = JQuery13Injector()
        injector.inject(self.req)
        self.assert_equals(1, len(self.scripts()))
        self.assert_equals('/chrome/agilo/js/lib/jquery-1.3.2.min.js', self.scripts()[0]['href'])
    
    def test_throws_exception_if_jquery_12_isnt_found_in_scripts_array(self):
        injector = JQuery13Injector()
        self.set_scripts([{'href':'bar/jquery-1.3.2.min.js'}])
        self.assert_raises(ValueError, injector.inject, self.req) # missing jquery 1.2
        
        self.set_scripts([])
        self.assert_raises(ValueError, injector.inject, self.req) # missing jquery 1.2
    
    def test_has_nice_interface_for_injector(self):
        use_jquery_13(self.req)
        self.assert_equals(1, len(self.scripts()))
        self.assert_equals('/chrome/agilo/js/lib/jquery-1.3.2.min.js', self.scripts()[0]['href'])
