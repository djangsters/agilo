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
#       - Martin Häcker <martin.haecker__at__agile42.com>

import agilo.utils.filterwarnings

from datetime import timedelta


from agilo.scrum.backlog.json_ui import SprintListView
from agilo.test import AgiloTestCase
from agilo.utils import Key
from agilo.utils.days_time import now

def in_days(days=0):
    return now() + timedelta(days=days)

def before_days(days=0):
    return in_days(-days)


class CanFetchTicketPositionsInBacklogWithJSONTest(AgiloTestCase):
    
    def setUp(self):
        self.super()
        self.view = SprintListView(self.env)
    
    def call(self, name_of_last_visited_sprint=None):
        req = self.teh.mock_request(session={'agilo-1-scope': name_of_last_visited_sprint})
        return self.view.list_sprints(req)
    
    def test_can_get_list_of_sprints_from_view(self):
        self.teh.create_sprint('running 1')

        self.teh.create_sprint('to start 1', start=in_days(10), end=in_days(20))
        self.teh.create_sprint('to start 2', start=in_days(10), end=in_days(20))
        
        self.teh.create_sprint('closed 1', start=before_days(10), end=before_days(5))
        self.teh.create_sprint('closed 2', start=before_days(10), end=before_days(5))
        self.teh.create_sprint('closed 3', start=before_days(10), end=before_days(5))
        
        running, to_start, closed = self.call()
        self.assert_equals(1, len(running[Key.OPTIONS]))
        self.assert_equals(2, len(to_start[Key.OPTIONS]))
        self.assert_equals(3, len(closed[Key.OPTIONS]))
    
    def test_will_mark_last_viewed_sprint_from_session(self):
        self.teh.create_sprint('running 1')
        self.teh.create_sprint('running 2')
        
        running, to_start, closed = self.call('running 1')
        self.assert_equals(2, len(running[Key.OPTIONS]))
        self.assert_equals(0, len(to_start[Key.OPTIONS]))
        self.assert_equals(0, len(closed[Key.OPTIONS]))
        
        first, second = running[Key.OPTIONS]
        self.assert_equals('running 1', first[0])
        self.assert_true(first[1])
        self.assert_equals('running 2', second[0])
        self.assert_false(second[1])
    
