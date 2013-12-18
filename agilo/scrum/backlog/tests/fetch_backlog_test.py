# -*- coding: utf-8 -*-
#   Copyright 2007-2009 Agile42 GmbH 
#   Copyright 2011 Agilo Software GmbH All rights reserved
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
# 

from agilo.api import ValueObject
from agilo.scrum.backlog.json_ui import SprintBacklogJSONView
from agilo.test import AgiloTestCase
from agilo.utils import Key, Type


class CanFetchEmptySprintBacklogWithJSONTest(AgiloTestCase):
    
    def setUp(self):
        self.super()
        self.sprint_name = 'FnordSprint'
        self.teh.create_sprint(self.sprint_name)
    
    def sprint_backlog(self, req):
        json_data = SprintBacklogJSONView(self.env).do_get(req, {Key.SPRINT: self.sprint_name})
        return map(ValueObject, json_data)
    
    def test_can_fetch_empty_sprint_backlog(self):
        req = self.teh.mock_request()
        self.assert_equals(0, len(self.sprint_backlog(req)))
    
    def find_task(self, tickets, summary):
        for ticket in tickets:
            if ticket.summary == summary:
                return ticket
        self.fail('Did not find ticket with summary %s' % summary)
    
    def test_can_fetch_sprint_backlog_with_json(self):
        task1 = self.teh.create_ticket(Type.TASK, {Key.SUMMARY: 'Task 1', Key.SPRINT: self.sprint_name})
        task2 = self.teh.create_ticket(Type.TASK, {Key.SUMMARY: 'Task 2', Key.SPRINT: self.sprint_name})
        
        req = self.teh.mock_request()
        json_tickets = self.sprint_backlog(req)
        
        self.assert_equals(2, len(json_tickets))
        found_task1 = self.find_task(json_tickets, 'Task 1')
        self.assert_equals(task1.id, found_task1.id)
        self.assert_equals(self.sprint_name, found_task1.sprint)
        
        found_task2 = self.find_task(json_tickets, 'Task 2')
        self.assert_equals(task2.id, found_task2.id)
        self.assert_equals(self.sprint_name, found_task2.sprint)

## TODO: this needs to happen as a test for the json view
#self.assert_not_none(req.response.headers.get('Expires'))
#self.assert_equals('no-cache', req.response.headers.get('Pragma'))

if __name__ == '__main__':
    from agilo.test import run_all_tests
    run_all_tests(__file__)

