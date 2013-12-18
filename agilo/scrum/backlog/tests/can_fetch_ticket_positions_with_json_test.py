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


from agilo.scrum.backlog import BacklogController, BacklogModelManager, BacklogTicketPositionView
from agilo.test import AgiloTestCase
from agilo.utils import Key


# each id only once
# at the first place its ticket is visible
# 
# [id1, id2, id3, id4, ...]


class CanFetchTicketPositionsInBacklogWithJSONTest(AgiloTestCase):
    def setUp(self):
        self.super()
        self.sprint = self.teh.create_sprint('Foo')
        self.story = self.teh.create_story(sprint=self.sprint.name)
        self.task1 = self.teh.create_task(sprint=self.sprint.name)
    
    def _move(self, ticket, target_position):
        cmd = BacklogController.MoveBacklogItemCommand(self.env, name=Key.SPRINT_BACKLOG, 
                       scope=self.sprint.name, ticket=ticket, to_pos=target_position)
        BacklogController(self.env).process_command(cmd)
    
    def _positions(self):
        req = self.teh.mock_request()
        args = dict(backlog_name=Key.SPRINT_BACKLOG, backlog_scope=self.sprint.name)
        return BacklogTicketPositionView(self.env).do_get(req, args)
    
    def _clear_backlog_cache(self):
        BacklogModelManager(self.env).get_cache().invalidate()
    
    
    
    def test_can_fetch_positions_for_simple_backlog(self):
        self._move(self.task1, 0)
        self._move(self.story, 1)
        self.assert_equals([self.task1.id, self.story.id], self._positions())
    

