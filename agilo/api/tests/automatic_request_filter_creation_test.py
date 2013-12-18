# encoding: utf8
#   Copyright 2009 agile42 GmbH All rights reserved
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
#        - Martin Häcker <martin.haecker__at__agile42.com>

from trac.core import Component, implements
from trac.test import Mock

from agilo.api.view import HTTPView
from agilo.test import AgiloTestCase, BetterEnvironmentStub


class FirstTestView(HTTPView):
    
    template = 'foo.html'
    
    def do_get(self, req):
        return {}


class SecondTestView(FirstTestView):
    pass


class FirstTestViewExtension(Component):
    
    implements(IFirstTestViewRequestFilter)
    
    def __init__(self):
        self.pre_process_was_triggered = False
        self.post_process_was_triggered = False
    
    def pre_process_request(self, req):
        self.pre_process_was_triggered = True
    
    def post_process_request(self, req):
        self.post_process_was_triggered = True


class FilteredExtensionPointsTest(AgiloTestCase):
    def setUp(self):
        self.super()
        self.env = BetterEnvironmentStub(enable=[FirstTestViewExtension])
        self.assert_true(self.env.is_component_enabled(FirstTestViewExtension))
        self.req = self.teh.mock_request(method='GET')
    
    def test_smoke(self):
        FirstTestView(self.env).process_request(self.req)
        self.assert_true(FirstTestViewExtension(self.env).pre_process_was_triggered)
        self.assert_true(FirstTestViewExtension(self.env).post_process_was_triggered)
    
    def test_dont_trigger_on_other_views(self):
        SecondTestView(self.env).process_request(self.req)
        self.assert_false(FirstTestViewExtension(self.env).pre_process_was_triggered)
        self.assert_false(FirstTestViewExtension(self.env).post_process_was_triggered)

