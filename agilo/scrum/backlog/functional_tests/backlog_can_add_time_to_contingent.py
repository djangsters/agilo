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
#   Author: 
#       - Martin Häcker <martin.haecker__at__agile42.com>

import agilo.utils.filterwarnings

from agilo.api import ValueObject
from agilo.test import Usernames
from agilo.utils import Key, Type
from agilo.test.functional import AgiloFunctionalTestCase

class CanEditContingentTest(AgiloFunctionalTestCase):
    testtype = 'windmill'
    
    def setUp(self):
        self.super()
        self.tester.login_as(Usernames.admin)
        self.tester.create_sprint_with_team(self.sprint_name(), self.team_name())
        self.tester.add_member_to_team(self.team_name(), Usernames.scrum_master)
        # REFACT: rename availableTime to reservedTime
        self.contingent = ValueObject(name='contingent', availableTime='23', spentTime='0', remainingTime='23')
        self.tester.create_new_contingent(self.contingent.name, self.contingent.availableTime, self.team_name(), self.sprint_name())
    
    def runTest(self):
        self.windmill_tester.login_as(Usernames.team_member)
        self.backlog = self.windmill_tester.go_to_new_sprint_backlog(self.sprint_name())
        
        self.backlog.toggle_contingents_display()
        self.backlog.assert_contingents([self.contingent])
        
        self.contingent.spentTime = '10'
        self.contingent.remainingTime = '13'
        self.backlog.assert_and_change_remaining_time_for_contingent('10', self.contingent)
        
        self.contingent.spentTime = '7'
        self.contingent.remainingTime = '16'
        self.backlog.assert_and_change_remaining_time_for_contingent('-3', self.contingent)
    

if __name__ == '__main__':
    from agilo.test import run_all_tests
    run_all_tests(__file__)

