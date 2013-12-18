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

from agilo.test import Usernames
from agilo.test.functional import AgiloFunctionalTestCase

class CanHaveTicketsWithMultipleLinks(AgiloFunctionalTestCase):
    testtype = 'windmill'
    
    def setUp(self):
        self.super()
        self.tester.login_as(Usernames.admin)
        self.tester.create_sprint_with_team(self.sprint_name())
        story1_id = self.create_story('First Parent')
        story2_id = self.create_story('Second Parent')
        self.task = self.create_task('Child with two parents', [story1_id, story2_id])
        self.story1 = self.tester.navigate_to_ticket_page(story1_id).ticket()
        self.story2 = self.tester.navigate_to_ticket_page(story2_id).ticket()
        self.story1.children = [self.task]
        self.story2.children = [self.task]
        self.backlog = [self.story1, self.story2]
    
    def create_story(self, summary):
        return self.tester.create_new_agilo_userstory(summary, sprint=self.sprint_name())
    
    def create_task(self, summary, link_ids):
        task_id = self.tester.create_new_agilo_task(summary, 
            sprint=self.sprint_name(), remaining_time=2)
        for link_id in link_ids:
            self.tester.link_tickets(link_id, task_id)
        return self.tester.navigate_to_ticket_page(task_id).ticket()
    
    def runTest(self):
        self.windmill_tester.login_as(Usernames.team_member)
        backlog = self.windmill_tester.go_to_new_sprint_backlog()
        
        # Shows task two times
        backlog.assert_shows_only(self.backlog)
        self.assert_equals(2, backlog.count_renderings_of_ticket_with_id(self.task.id))
        
        # Changes are reflected everywhere
        backlog.update_remaining_time_for_ticket(self.task.id, 23)
        self.task.remaining_time = '23h'
        self.story1.total_remaining_time = '23h'
        self.story2.total_remaining_time = '23h'
        # wait for backlog background reload
        backlog.wait_for_field_to_have_content(self.story1.id, 'total_remaining_time', 23)
        # updated both parents, backlog is reloaded
        backlog.assert_shows_only(self.backlog)
    
