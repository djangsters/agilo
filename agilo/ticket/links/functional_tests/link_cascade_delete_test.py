# -*- encoding: utf-8 -*-
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
#       - Stefano Rago <stefano.rago__at__agilosoftware.com>

from trac.tests.functional import tc

from agilo.utils import Type

from agilo.test import Usernames
from agilo.test.functional import AgiloFunctionalTestCase

class TestCascadeDeletionReferencingTicket(AgiloFunctionalTestCase):
    def runTest(self):
        # First login, anonymous may not be allowed to do anything
        self._tester.login_as(Usernames.admin)
        self._tester.set_option('agilo-links', 'delete', 'story-task')
        story_id = self._tester.create_new_agilo_ticket(Type.USER_STORY, 'Story to delete')
        task_id = self._tester.create_referenced_ticket(story_id, Type.TASK, 'This task should be deleted as well')
        
        self._tester.go_to_view_ticket_page(story_id)
        tc.formvalue('propertyform', 'delete', 'click')
        tc.submit('delete')
        self._tester.go_to_view_ticket_page(story_id, should_fail=True)
        tc.find('Ticket %d does not exist' % story_id)
        self._tester.go_to_view_ticket_page(task_id, should_fail=True)
        tc.find('Ticket %d does not exist' % task_id)        
