# -*- encoding: utf-8 -*-
#   Copyright 2008 Agile42 GmbH, Berlin (Germany)
#   Copyright 2011 Agilo Software GmbH All rights reserved
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


import agilo.utils.filterwarnings

from agilo.scrum.backlog.tests.backlog_info_test import BacklogInfoTest
from agilo.utils.constants import BacklogType


class BacklogInfoContainerTest(BacklogInfoTest):
    def setUp(self):
        self.super()
        self.backlog = self._create_sprint_backlog()
    
    def test_backlog_info_conforms_to_application_protocol(self):
        backlog = self.teh.create_backlog_without_tickets('Sprint Backlog', BacklogType.SPRINT, scope=self.sprint_name)
        backlog_info = self.json_view.backlog_info_for_backlog(self.req, backlog)
        self.assert_equals('backlog_info', backlog_info['content_type'])
        self.assert_not_none(backlog_info['content'])
        self.assert_not_none(backlog_info['permissions'])
    
