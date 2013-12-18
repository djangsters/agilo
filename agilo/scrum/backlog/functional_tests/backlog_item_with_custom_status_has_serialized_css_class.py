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
from agilo.scrum.backlog.backlog_config import BacklogConfiguration
from agilo.utils import Key

from agilo.test import Usernames
from agilo.test.functional import AgiloFunctionalTestCase

class BacklogItemWithCustomStatusHasSerializedCssClass(AgiloFunctionalTestCase):
    testtype = 'windmill'

    def setUp(self):
        self.super()
        env = self.testenv.get_trac_environment()
        env.config.set('ticket-workflow', 'fnordify', '* -> fnord i fied')
        backlog_config = BacklogConfiguration(env, Key.SPRINT_BACKLOG)
        backlog_config.backlog_columns = [Key.STATUS,]
        env.config.save()

        self.tester.login_as(Usernames.admin)
        ids = self.tester.create_sprint_with_small_backlog()
        self.task_id = ids[2][0]

    def _task_has_class(self, css_class):
        jquery = '$("#ticketID-%s").hasClass("%s")' % (self.task_id, css_class)
        return self.windmill_tester.output_for_js(jquery)

    def runTest(self):
        self.windmill_tester.login_as(Usernames.team_member)

        page = self.windmill_tester.go_to_new_sprint_backlog()
        page.update_inline_editor_field_for_ticket(Key.STATUS, self.task_id, 'fnord i fied')

        self.assert_false(self._task_has_class("fied"))
        self.assert_true(self._task_has_class("ticketstatus-fnord-i-fied"))

