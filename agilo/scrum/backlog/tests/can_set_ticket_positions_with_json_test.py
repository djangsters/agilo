# -*- encoding: utf-8 -*-
#   Copyright 2009 Agile42 GmbH, Berlin (Germany)
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
#   
#   Author: 
#       - Felix Schwarz <felix.schwarz__at__agile42.com>

from agilo.scrum.backlog import BacklogTicketPositionView
from agilo.test import AgiloTestCase
from agilo.utils import Key


# each id only once
# at the first place its ticket is visible
# 
# [id1, id2, id3, id4, ...]


class CanSetTicketPositionsInBacklogWithJSONTest(AgiloTestCase):
    def setUp(self):
        self.super()
        self.sprint = self.teh.create_sprint('Foo')
        self.story = self.teh.create_story(sprint=self.sprint.name)
        self.task1 = self.teh.create_task(sprint=self.sprint.name)
    
    def _request_parameters(self, positions=()):
        return dict(backlog_name=Key.SPRINT_BACKLOG, backlog_scope=self.sprint.name,
                    positions=positions)
    
    def _positions(self):
        req = self.teh.mock_request()
        return BacklogTicketPositionView(self.env).do_get(req, self._request_parameters())
    
    def _set_positions(self, positions):
        args = self._request_parameters(positions)
        req = self.teh.mock_request()
        BacklogTicketPositionView(self.env).do_post(req, args)
    
    def test_can_set_all_positions_at_once(self):
        expected_positions = [self.story.id, self.task1.id]
        self._set_positions(expected_positions)
        self.assert_equals(expected_positions, self._positions())
