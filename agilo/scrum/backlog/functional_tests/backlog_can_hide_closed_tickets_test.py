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
from agilo.utils.config import AgiloConfig
from agilo.test.functional import AgiloFunctionalTestCase

class TestCanHideClosedTickets(AgiloFunctionalTestCase):
    testtype = 'windmill'
    
    def setUp(self):
        self.super()
        self.tester.login_as(Usernames.admin)
        self.tester.create_sprint_with_team(self.sprint_name())
        self.story1_id = self.create_story("First closed parent")
        self.task1_id = self.create_task("First child", self.story1_id)
        self.story2_id = self.create_story("Second parent")
        self.task2_id = self.create_task('Second child', self.story2_id)
        
        self.tester.close_ticket(self.story1_id)
        self.tester.close_ticket(self.task2_id)
    
    def create_story(self, summary):
        return self.tester.create_new_agilo_userstory(summary, sprint=self.sprint_name())
    
    def create_task(self, summary, parent_id):
        return self.tester.create_new_agilo_task(summary, link=parent_id, sprint=self.sprint_name())
    
    def runTest(self):
        self.windmill_tester.login_as(Usernames.team_member)
        backlog = self.windmill_tester.go_to_new_sprint_backlog(self.sprint_name())
        self.assert_equals(backlog.order_of_tickets(), 
            [self.story1_id, self.task1_id, self.story2_id, self.task2_id])
        backlog.toggle_hide_closed_tickets()
        self.assert_equals(backlog.order_of_tickets(), 
            [self.story1_id, self.task1_id, self.story2_id])
        backlog.toggle_hide_closed_tickets()
        self.assert_equals(backlog.order_of_tickets(), 
            [self.story1_id, self.task1_id, self.story2_id, self.task2_id])
    

if __name__ == '__main__':
    from agilo.test import run_all_tests
    run_all_tests(__file__)

