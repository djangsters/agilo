# -*- coding: utf8 -*-
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
#        - Martin Häcker <martin.haecker__at__agile42.com>

import agilo.utils.filterwarnings

from agilo.api import ValueObject
from agilo.test import Usernames
from agilo.test.functional import AgiloFunctionalTestCase, AgiloJSONTester
from agilo.utils.compat import json
from agilo.utils.json_client import GenericHTTPException

# Helper to migrate Functional tests from pro to open without much changes to them at first
# MH: I would like to change the tests directly, but I also want them with as little changes
# as possible at first to make sure that I don't create new regressions in the migration - 
# even though that means that I need to do that later...
class JSONFunctionalTestCase(AgiloFunctionalTestCase):
    is_abstract_test = True
    
    def setUp(self):
        self.super()
        self.env = self.testenv.get_trac_environment()
        self.json_tester = AgiloJSONTester(self.tester.url, self.env)
    
    # REFACT: this is already in the tester class - move to using that
    def create_sprint_with_team(self):
        self.tester.login_as(Usernames.admin)
        milestone_name = self.tester.create_milestone()
        sprint_name = self.classname() + 'Sprint'
        team_name = self.classname() + 'Team'
        self.tester.create_new_team(team_name)
        self.tester.add_member_to_team(team_name, self.current_team_member_name())
        
        self.tester.login_as(Usernames.product_owner)
        self.tester.create_sprint_for_milestone(milestone_name, sprint_name, 
                                                team=team_name)
        return sprint_name
    
    # REFACT: get rid of this method and use the tester alternatives instead
    def current_team_member_name(self):
        return self.classname()+'Dev'
    
    def assert_json_error(self, call_server, *args, **kwargs):
        """If you give code as an keyword argument, it is ensured that the 
        server responded with that HTTP code."""
        code = kwargs.pop('code', None)
        # REFACT: use assert_raises
        try:
            call_server(*args, **kwargs)
            self.fail()
        except GenericHTTPException, e:
            if code is not None:
                self.assertEqual(code, e.code)
            json_data = ValueObject(json.loads(e.detail))
            return json_data
    


