# -*- encoding: utf-8 -*-
#   Copyright 2008-2009 Agile42 GmbH, Berlin (Germany)
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
#       - Martin Häcker <martin.haecker__at__agile42.com>


import agilo.utils.filterwarnings

from agilo.scrum.backlog.backlog_toggle import BacklogToggleConfigurationJSONView
from agilo.test import AgiloTestCase, TestEnvHelper


class BacklogSwitcherTest(AgiloTestCase):
    
    def setUp(self):
        self.super()
        self.teh = TestEnvHelper(enable_agilo=False, env_key=self.env_key)
        self.env = self.teh.get_env()
        self.view = BacklogToggleConfigurationJSONView(self.env)
        self.assert_equals([], self.view.discover_backlogs())
    
    def tearDown(self):
        self.view.reset_known_backlogs()
        self.super()
    
    def call(self):
        return self.view.do_get(self.teh.mock_request(), None)
    
    def test_can_register_arbitrary_backlogs(self):
        self.view.register_backlog_with_identifier('fnord')
        self.assert_equals(['fnord', ], self.call())
    
    def test_has_special_method_for_all_known_backlogs(self):
        self.view.register_new_backlog()
        self.assert_equals(['new_backlog'], self.call())
        
        self.view.register_whiteboard()
        self.assert_equals(['new_backlog', 'whiteboard'], self.call())
    
