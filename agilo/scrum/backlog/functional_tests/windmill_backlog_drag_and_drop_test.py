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

from datetime import timedelta

from agilo.utils.days_time import today

from agilo.test import Usernames
from agilo.test.functional import AgiloFunctionalTestCase

class CanUseDragAndDropToReorderTicketsWithDependencies(AgiloFunctionalTestCase):
    testtype = 'windmill'
    
    def setUp(self):
        self.super()
        self.tester.login_as(Usernames.admin)
        
        # I had problems on mondays that the sprint start would sometimes be shifted
        # to the next day - definitely a bug, but not one I will solve now
        two_weeks_ago = today() - timedelta(14)
        team_name = self.tester.create_team_with_two_members()
        milestone_name = self.tester.create_milestone('MilestoneFor' + self.sprint_name())
        self.tester.create_sprint_for_milestone(milestone_name, self.sprint_name(), 
            team=team_name, start=two_weeks_ago, duration=30)
        
        story_id, task_ids = self.tester.create_userstory_with_tasks(self.sprint_name())
        second_story_id, more_task_ids = self.tester.create_userstory_with_tasks(self.sprint_name())
        self.original_order = [story_id] + task_ids + [second_story_id] + more_task_ids
    
    def runTest(self):
        self.windmill_tester.login_as(Usernames.scrum_master)
        backlog_page = self.windmill_tester.go_to_new_sprint_backlog()
        self.assertEquals(self.original_order, backlog_page.order_of_tickets())
        self.windmill.dragDropElemToElem(id='ticketID-%d' % self.original_order[0], 
            optid='ticketID-%d' % self.original_order[-1])
        new_order = self.original_order[-3:] + self.original_order[:3]
        self.assertEquals(new_order, backlog_page.order_of_tickets())
        backlog_page = self.windmill_tester.go_to_new_sprint_backlog()
        self.assertEquals(new_order, backlog_page.order_of_tickets())
    

if __name__ == '__main__':
    from agilo.test import run_all_tests
    run_all_tests(__file__)

