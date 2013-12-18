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

import time

from agilo.test import Usernames
from agilo.test.functional import AgiloFunctionalTestCase
from agilo.api import ValueObject

class ReloadsTicketsInBackgroundAfterEdit(AgiloFunctionalTestCase):
    testtype = 'windmill'
    
    def setUp(self):
        self.super()
        self.tester.login_as(Usernames.admin)
        self.create_backlog()
        self.windmill_tester.login_as(Usernames.team_member)
        self.page = self.windmill_tester.go_to_new_sprint_backlog(self.sprint_name())
        
        # The story is created after the backlog was opened with windmill so it
        # is not shown until the backlog is reloaded
        self.new_story_id = self.tester.create_new_agilo_userstory('new story', sprint=self.sprint_name())
        
        self.assert_backlog_shows_story_with_all_tasks()
    
    def create_backlog(self):
        self.requirement_id, self.story_id, [self.task1_id, self.task2_id] = self.tester.create_sprint_with_small_backlog()
        self.unchanged_task_id = self.tester.create_new_agilo_task("won't change externally", sprint=self.sprint_name())
    
    def ticket(self, ticket_id, *children):
        ticket = self.tester.navigate_to_ticket_page(ticket_id).ticket()
        ticket.children = children
        return ticket
    
    def assert_backlog_shows_story_with_all_tasks(self):
        expected_backlog = [
            self.ticket(self.requirement_id, 
                self.ticket(self.story_id,
                    self.ticket(self.task1_id),
                    self.ticket(self.task2_id)
                )
            ),
            ValueObject(id=-1, children=[
                self.ticket(self.unchanged_task_id),
            ])
        ]
        self.page.assert_shows_only(expected_backlog)
    
    def trigger_backlog_reload(self):
        self.page.update_remaining_time_for_ticket(self.unchanged_task_id, 23)
    
    def wait_until_backlog_is_reloaded(self):
        # REFACT: We should have such a method in the windmill backlog page but
        # currently we don't know if there is still an ongoing backlog load
        js = "1 === jQuery('#ticketID-%d', windmill.testWindow.document).length" % self.new_story_id
        self.windmill_tester.windmill.waits.forJS(js=js)
    
    def assert_backlog_shows_story_with_first_task_and_new_story(self):
        expected_backlog = [
            self.ticket(self.requirement_id, 
                self.ticket(self.story_id,
                    self.ticket(self.task1_id),
                    )
            ),
            self.ticket(self.new_story_id),
            ValueObject(id=-1, children=[
                self.ticket(self.unchanged_task_id),
            ]),
        ]
        self.page.assert_shows_only(expected_backlog)
    
    def runTest(self):
        # Afterwards all the tasks for this story should be removed from the backlog
        self.tester.edit_ticket(self.story_id, sprint='')
        
        time.sleep(1)
        # Now the story should be in again because task1 is in
        self.tester.edit_ticket(self.task1_id, sprint=self.sprint_name())
        
        time.sleep(1)
        self.trigger_backlog_reload()
        self.wait_until_backlog_is_reloaded()
        self.assert_backlog_shows_story_with_first_task_and_new_story()
    

if __name__ == '__main__':
    from agilo.test import run_all_tests
    run_all_tests(__file__)

