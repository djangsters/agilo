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

from agilo.test import Usernames
from agilo.test.functional import AgiloFunctionalTestCase

class DraggingLeavesInPlaceEditorClosed(AgiloFunctionalTestCase):
    testtype = 'windmill'
    
    def setUp(self):
        self.super()
        self.tester.login_as(Usernames.admin)
        ids = self.tester.create_sprint_with_small_backlog()
        self.story_id = ids[1]
        self.second_task_id = ids[2][1]
    
    def runTest(self):
        self.windmill_tester.login_as(Usernames.team_member)
        page = self.windmill_tester.go_to_new_sprint_backlog()
        self.windmill.dragDropElemToElem(jquery="('#ticketID-%d .summary')[0]" % self.second_task_id, 
            optid='ticketID-%d' % self.story_id)
        is_editor_open = page.output_for_js("$('#ticketID-%d .summary').is(':has(:input)')" % self.second_task_id)
        self.assert_false(is_editor_open)
    

if __name__ == '__main__':
    from agilo.test import run_all_tests
    run_all_tests(__file__)

