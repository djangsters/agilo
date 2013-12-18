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
#   Author: 
#       - Martin Häcker <martin.haecker__at__agile42.com>

import agilo.utils.filterwarnings

from agilo.api import ValueObject

from agilo.test import Usernames
from agilo.test.functional import AgiloFunctionalTestCase

class CanEditRemainingTimeInlineTest(AgiloFunctionalTestCase):
    testtype = 'windmill'
    
    def setUp(self):
        self.super()
        self.tester.delete_all_tickets()
        self.tester.login_as(Usernames.admin)
        team_name = self.tester.create_team_with_two_members()
        self.tester.add_member_to_team(team_name, Usernames.team_member)
        self.tester.add_member_to_team(team_name, Usernames.second_team_member)
        self.tester.create_sprint_with_team(self.sprint_name(), team_name)
        self.task1 = self.create_task('Task without owner', '')
        self.task2 = self.create_task('Task for team_member', Usernames.team_member)
        self.task3 = self.create_task('Task for second_team_member', Usernames.second_team_member)
        self.backlog = [ValueObject(id=-1, children=[self.task1, self.task2, self.task3])]
    
    def create_task(self, summary, owner=None):
        task_id = self.tester.create_new_agilo_task(summary, 
            sprint=self.sprint_name(), owner=owner, remaining_time=2)
        return self.tester.navigate_to_ticket_page(task_id).ticket()
    
    def _test_scrum_master_can_change_all_tickets(self):
        self.windmill_tester.login_as(Usernames.scrum_master)
        new_backlog = self.windmill_tester.go_to_new_sprint_backlog()
        new_backlog.assert_shows_only(self.backlog)
        
        # change remaining time of both tasks
        new_backlog.update_remaining_time_for_ticket(self.task1.id, 4)
        new_backlog.update_remaining_time_for_ticket(self.task2.id, 4)
        new_backlog.update_remaining_time_for_ticket(self.task3.id, 4)
    
    def _test_team_member_can_only_change_his_or_new_tickets(self):
        self.windmill_tester.login_as(Usernames.team_member)
        new_backlog = self.windmill_tester.go_to_new_sprint_backlog()
        new_backlog.update_remaining_time_for_ticket(self.task1.id, 6)
        new_backlog.update_remaining_time_for_ticket(self.task2.id, 6)
        # TODO: this test could be even more fine grained in seing that the edit field doesn't even come up
        new_backlog.update_remaining_time_for_ticket(self.task3.id, 6, should_fail=True)
    
    def _test_can_reset_remaining_time_to_emtpy_string(self):
        self.windmill_tester.login_as(Usernames.scrum_master)
        new_backlog = self.windmill_tester.go_to_new_sprint_backlog()
        new_backlog.update_remaining_time_for_ticket(self.task1.id, '')
    
    def runTest(self):
        self._test_scrum_master_can_change_all_tickets()
        self._test_team_member_can_only_change_his_or_new_tickets()
        self._test_can_reset_remaining_time_to_emtpy_string()
    

if __name__ == '__main__':
    from agilo.test import run_all_tests
    run_all_tests(__file__)

