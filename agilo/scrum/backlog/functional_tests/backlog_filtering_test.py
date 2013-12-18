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
#       - Robert Buchholz <robert.buchholz__at__agile42.com>

import agilo.utils.filterwarnings

from agilo.test import Usernames
from agilo.utils import Key, Type
from agilo.utils.config import AgiloConfig
from agilo.test.functional import AgiloFunctionalTestCase

class TestFilteringByJSONValues(AgiloFunctionalTestCase):
    testtype = 'windmill'
    
    def setUp(self):
        self.super()
        self.tester.login_as(Usernames.admin)
        
        self.tester.show_field_for_type(Key.COMPONENT, Type.TASK)
        self.tester.create_sprint_with_team(self.sprint_name())
        
        self.story1 = self.create_story('First parent')
        self.task1 = self.create_task('First child', self.story1.id, component='component1', remaining_time=4)
        self.story2 = self.create_story('Second parent')
        self.task2 = self.create_task('Second child', self.story2.id, component='component2', remaining_time=3)
        
        self.tester.set_option(AgiloConfig.AGILO_GENERAL, 'backlog_filter_attribute', 'component')
    
    def tearDown(self):
        # deleting sprints is necessary as this class contains two test cases 
        # which use the same sprint name (as self.sprintname() relies on
        # the class name)
        self.tester.delete_sprints_and_milestones()
        self.tester.delete_all_tickets()
        self.super()
    
    def create_story(self, summary):
        story_id = self.tester.create_new_agilo_userstory(summary, sprint=self.sprint_name())
        return self.tester.navigate_to_ticket_page(story_id).ticket()
    
    def create_task(self, summary, link_id, component, remaining_time=None):
        task_id = self.tester.create_new_agilo_task(summary,
            sprint=self.sprint_name(), component=component, remaining_time=remaining_time)
        self.tester.link_tickets(link_id, task_id)
        return self.tester.navigate_to_ticket_page(task_id).ticket()
    
    def test_can_filter_by_component(self):
        self.windmill_tester.login_as(Usernames.team_member)
        backlog = self.windmill_tester.go_to_new_sprint_backlog(self.sprint_name())
        backlog.set_filter_value('component2')
        tickets = backlog.order_of_tickets()
        self.assert_equals([self.story2.id, self.task2.id], tickets)
        
        backlog.set_filter_value('')
        tickets = backlog.order_of_tickets()
        self.assert_equals(4, len(tickets))
    
    def test_updates_totals_when_filtering(self):
        self.windmill_tester.login_as(Usernames.team_member)
        backlog = self.windmill_tester.go_to_new_sprint_backlog(self.sprint_name())
        self.assert_equals('7', backlog.totals().remaining_time)
        backlog.set_filter_value('component2')
        self.assert_equals('3', backlog.totals().remaining_time)
        backlog.set_filter_value('')
        self.assert_equals('7', backlog.totals().remaining_time)


if __name__ == '__main__':
    from agilo.test import run_all_tests
    run_all_tests(__file__)

