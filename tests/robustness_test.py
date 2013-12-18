# -*- encoding: utf-8 -*-
#   Copyright 2008 Agile42 GmbH, Berlin (Germany)
#   Copyright 2007 Andrea Tomasini <andrea.tomasini_at_agile42.com>
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
#       - Andrea Tomasini <andrea.tomasini_at_agile42.com>
"""
WARNING: This module contains classes to do some robustness tests, the goal is 
to try to break agilo somewhere and fix the code and the tests in the dedicated 
test modules.
"""

from agilo.test import AgiloTestCase
from agilo.utils import Type, Key, BacklogType


class TestTicketSprintRobustness(AgiloTestCase):
    """
    Test the robustness of the Sprint field in a Ticket, in some cases this
    field got reset, or changed, but we are not able to reproduce it, 
    systematically.
    """
    
    def testChangeTicketProperties(self):
        """
        Test the persistence of the sprint field while changing other ticket
        properties
        """
        sprint = self.teh.create_sprint('TestSprint')
        task = self.teh.create_ticket(Type.TASK, props={Key.REMAINING_TIME: '12',
                                                        Key.SPRINT: sprint.name})
        backlog = self.teh.create_backlog(name="TestBacklog", 
                                          num_of_items=50, 
                                          b_type=BacklogType.SPRINT, 
                                          ticket_types=[Type.USER_STORY, Type.TASK],
                                          scope=sprint.name)
        self.assert_length(50 + 1, backlog)
        # Now check that the task is in the backlog too
        self.assert_contains(task, backlog)
        self.assert_equals(sprint.name, task[Key.SPRINT], 
                           "Sprint in %s changed => %s after creating backlog" % \
                           (task, task[Key.SPRINT]))
        self.assert_equals(sprint.name, task[Key.SPRINT],
                           "Sprint in %s changed => %s after sorting backlog" % \
                           (task, task[Key.SPRINT]))
        # Now change the remaining time to the task
        task[Key.REMAINING_TIME] = '8'
        task.save_changes('tester', 'changed remaining time')
        self.assert_equals('8', task[Key.REMAINING_TIME])
        self.assert_equals(sprint.name, task[Key.SPRINT], 
                         "Sprint in %s changed => %s after changing remaining time" % \
                         (task, task[Key.SPRINT]))
        # Now changing the resources to the task
        self.teh.move_changetime_to_the_past([task])
        
        task[Key.RESOURCES] = 'tester, re-tester'
        task.save_changes('tester', 'changed resources')
        self.assert_equals('tester', task[Key.OWNER])
        self.assert_equals('re-tester', task[Key.RESOURCES])
        self.assert_equals(sprint.name, task[Key.SPRINT], 
                         "Sprint in %s changed => %s after changing remaining time" % \
                         (task, task[Key.SPRINT]))
        # Now create another sprint
        sprint2 = self.teh.create_sprint("AnotherSprint")
        # Reload ticket field
        task = self.teh.load_ticket(task)
        sprint_options = task.get_field(Key.SPRINT)['options']
        self.assert_contains(sprint2.name, sprint_options)
        self.assert_equals(sprint.name, task[Key.SPRINT], 
                           "Sprint in %s changed => %s after adding another sprint" % \
                            (task, task[Key.SPRINT]))
        self.assert_equals(sprint.name, task[Key.SPRINT],
                           "Sprint in %s changed => %s after reloading backlog" % \
                           (task, task[Key.SPRINT]))
        # Now change the ticket types for the Backlog and reload it...
        bug = self.teh.create_ticket(Type.BUG, props={Key.PRIORITY: 'major',
                                                      Key.SPRINT: sprint.name})
        backlog.config.ticket_types.append(Type.BUG)
        self.assert_contains(Type.BUG, backlog.config.ticket_types)
        backlog.config.save()
        self.assert_contains(bug, backlog)
        self.assert_equals(sprint.name, task[Key.SPRINT], 
                           "Sprint in %s changed => %s after reloading backlog with bug" % \
                           (task, task[Key.SPRINT]))
        self.assert_equals(sprint.name, task[Key.SPRINT],
                           "Sprint in %s changed => %s after resorting backlog with bug" % \
                           (task, task[Key.SPRINT]))
        

if __name__ == '__main__':
    from agilo.test.testfinder import run_unit_tests
    run_unit_tests(__file__)