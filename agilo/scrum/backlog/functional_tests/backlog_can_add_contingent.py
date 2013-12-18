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

from agilo.test import Usernames
from agilo.utils import Key, Type
from agilo.test.functional import AgiloFunctionalTestCase

class CanAddContingentTest(AgiloFunctionalTestCase):
    testtype = 'windmill'
    
    def setUp(self):
        self.super()
        self.tester.login_as(Usernames.admin)
        self.tester.create_sprint_with_team(self.sprint_name(), self.team_name())
        self.tester.add_member_to_team(self.team_name(), Usernames.scrum_master)
    
    def runTest(self):
        self.windmill_tester.login_as(Usernames.scrum_master)
        backlog = self.windmill_tester.go_to_new_sprint_backlog(self.sprint_name())
        
        backlog.toggle_contingents_display()
        backlog.assert_contingents([])
        backlog.add_contingents(name='fnord', amount=23)
        backlog.assert_contingents([dict(
            name='fnord',
            availableTime='23',
            spentTime='0',
            remainingTime='23'
        )])
    

if __name__ == '__main__':
    from agilo.test import run_all_tests
    run_all_tests(__file__)

