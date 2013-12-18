# -*- encoding: utf-8 -*-
#   Copyright 2010 Agile42 GmbH, Berlin (Germany)
#   Copyright 2011 Agilo Software GmbH All rights reserved
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use self file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import agilo.utils.filterwarnings

from agilo.api import ValueObject

from agilo.test import Usernames
from agilo.test.functional import AgiloFunctionalTestCase

class MovingStoryFromOrToBacklogWillAlsoMoveChildren(AgiloFunctionalTestCase):
    testtype = 'twill'
    
    def setUp(self):
        self.super()
        self.tester.login_as(Usernames.admin)
        ids = self.tester.create_sprint_with_small_backlog()
        self.story_id = ids[1]
        self.task1_id = ids[2][0]
        self.task2_id = ids[2][1]
    
    def _ticket(self, ticket_id):
        return self.tester.navigate_to_ticket_page(ticket_id).ticket()
    
    def runTest(self):
        self._test_removes_tasks_with_story()
        self._test_adds_tasks_with_story()
    
    def _test_removes_tasks_with_story(self):
        self.tester.edit_ticket(self.story_id, sprint='')
        self.assert_equals('n.a.', self._ticket(self.story_id).sprint)
        self.assert_equals('n.a.', self._ticket(self.task1_id).sprint)
        self.assert_equals('n.a.', self._ticket(self.task2_id).sprint)
    
    def _test_adds_tasks_with_story(self):
        self.tester.edit_ticket(self.story_id, sprint=self.sprint_name())
        self.assert_equals(self.sprint_name(), self._ticket(self.story_id).sprint)
        self.assert_equals(self.sprint_name(), self._ticket(self.task1_id).sprint)
        self.assert_equals(self.sprint_name(), self._ticket(self.task2_id).sprint)
    

if __name__ == '__main__':
    from agilo.test import run_all_tests
    run_all_tests(__file__)

