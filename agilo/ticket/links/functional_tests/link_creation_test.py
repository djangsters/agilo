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
#       - Felix Schwarz <felix.schwarz__at__agile42.com>

from trac.tests.functional import tc

from agilo.utils import Type
from agilo.test import Usernames
from agilo.test.functional import AgiloFunctionalTestCase

class TestLinkCreation(AgiloFunctionalTestCase):
    def _assert_task_is_linked_to_bug(self, target_id, source_id):
        self._tester.go_to_view_ticket_page(target_id)
        tc.find('#%d</a>' % source_id)
        
        self._tester.go_to_view_ticket_page(source_id)
        tc.find('#%d</a>' % target_id)
    
    def runTest(self):
        # First login :-)
        self._tester.login_as(Usernames.admin)
        bug_id = self._tester.create_new_agilo_ticket('bug', 'Nothing happens')
        task_id = self._tester.create_referenced_ticket(bug_id, Type.TASK, 'Think about fixing it')
        self._assert_task_is_linked_to_bug(task_id, bug_id)


if __name__ == '__main__':
    from agilo.test.testfinder import run_all_tests
    run_all_tests(__file__)

