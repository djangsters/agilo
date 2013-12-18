# -*- encoding: utf-8 -*-
#   Copyright 2011 Agile42 GmbH, Berlin (Germany)
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

class BacklogHasOwnerAsPopupWhenRestricted(AgiloFunctionalTestCase):
    testtype = 'windmill'

    def setUp(self):
        self.super()
        self.tester.login_as(Usernames.admin)
        ids = self.tester.create_sprint_with_small_backlog()
        self.task_id = ids[2][0]

    def runTest(self):
        self.windmill_tester.login_as(Usernames.team_member)
        page = self.windmill_tester.go_to_new_sprint_backlog()
        self.assert_false(page.has_select_editor_for_field_in_ticket("owner", self.task_id))

        env = self.testenv.get_trac_environment()
        env.config.set('ticket', 'restrict_owner', 'true')
        env.config.save()
        page = self.windmill_tester.go_to_new_sprint_backlog()
        self.assert_true(page.has_select_editor_for_field_in_ticket("owner", self.task_id))


