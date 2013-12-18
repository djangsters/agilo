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
#       - Felix Schwarz <felix.schwarz__at__agile42.com>
#       - Martin Häcker <martin.haecker__at__agile42.com>


from agilo.test import Usernames
from agilo.test.functional import AgiloFunctionalTestCase


class BacklogCanDisplayTickets(AgiloFunctionalTestCase):
    testtype = 'windmill'
    
    def setUp(self):
        self.super()
        self.tester.login_as(Usernames.admin)
        requirement_id, story_id, task_ids = self.tester.create_sprint_with_small_backlog()
        self.requirement = self.tester.navigate_to_ticket_page(requirement_id).ticket()
        story = self.tester.navigate_to_ticket_page(story_id).ticket()
        first_task = self.tester.navigate_to_ticket_page(task_ids[0]).ticket()
        second_task = self.tester.navigate_to_ticket_page(task_ids[1]).ticket()
        self.requirement.children = [story]
        story.children = [first_task, second_task]
    
    def runTest(self):
        self.windmill_tester.login_as(Usernames.scrum_master)
        backlog_page = self.windmill_tester.go_to_new_sprint_backlog()
        self.assertEqual(1+1+2, backlog_page.number_of_shown_tickets())
        backlog_page.assert_shows_only([self.requirement])
        self.assert_equals('10', backlog_page.totals().remaining_time)

if __name__ == '__main__':
    from agilo.test import run_all_tests
    run_all_tests(__file__)

