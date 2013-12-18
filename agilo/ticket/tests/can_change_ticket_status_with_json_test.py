# -*- coding: utf8 -*-
#   Copyright 2009-2010 Agile42 GmbH, Berlin (Germany)
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

from trac.util.datefmt import to_timestamp

from agilo.api import ValueObject
from agilo.test import Usernames
from agilo.ticket.model import AgiloTicket
from agilo.ticket.json_ui import TicketUpdateView
from agilo.utils import Key, Role, Status, Action, Type
from agilo.test.testcase import JSONAgiloTestCase


class TicketChangeTestCase(JSONAgiloTestCase):
    
    is_abstract_test = True
    
    def setUp(self):
        self.super()
        self.teh.add_field_for_type(Key.COMPONENT, Type.TASK)
        self.teh.grant_permission(Usernames.team_member, Role.SCRUM_MASTER)
        self.teh.grant_permission(Usernames.team_member, Role.TICKET_ADMIN)
        self.teh.grant_permission(Usernames.product_owner, Role.TICKET_ADMIN)
        self.sprint = self.teh.create_sprint(self.sprint_name(), team="Fnord Team")
        self.teh.create_member(Usernames.team_member, "Fnord Team")
        self.task = self.teh.create_task(sprint=self.sprint.name)
    
    def _request_for_ticket_change(self, username, **kwargs):
        # We need to load the ticket again to get the correct time of last 
        # change - otherwise trac will reject the edit...
        task = AgiloTicket(self.env, self.task.id)
        args = dict(
            ticket_id=task.id,
            time_of_last_change=to_timestamp(task.time_changed),
            ts=str(task.time_changed),
        )

        from agilo.ticket import AgiloTicketSystem
        if AgiloTicketSystem.is_trac_1_0():
            from trac.util.datefmt import to_utimestamp
            args.update({'view_time':str(to_utimestamp(task.time_changed)),'submit':True})

        args.update(kwargs)
        req = self.teh.mock_request(username, method='POST')
        req.args = args
        return req
    
    def _change_ticket(self, username, **kwargs):
        self.teh.move_changetime_to_the_past([self.task])
        req = self._request_for_ticket_change(username, **kwargs)
        json = TicketUpdateView(self.env).do_post(req, req.args)
        return ValueObject(json)
    
class CanChangeTicketStatusAccordingToWorkflow(TicketChangeTestCase):
    
    def _set_status_with_json(self, username, simple_status):
        return self._change_ticket(username, simple_status=simple_status)
    
    def test_dragging_task_to_in_progress_set_status_accepted(self):
        self.assert_not_equals(Usernames.team_member, self.task[Key.OWNER])
        json = self._set_status_with_json(Usernames.team_member, simple_status='in_progress')
        self.assert_equals(Status.ACCEPTED, json.status)
        self.assert_equals(Usernames.team_member, json.owner)
        # load from db explicitly, our cached self.task still has old values
        task_from_db = AgiloTicket(self.env, self.task.id)
        self.assert_equals(Usernames.team_member, task_from_db[Key.OWNER])
    
    def test_dragging_task_to_closed_closes_ticket_and_retains_owner(self):
        self._set_status_with_json(Usernames.team_member, simple_status='in_progress')
        json = self._set_status_with_json(Usernames.team_member, simple_status='closed')
        self.assert_equals(Status.CLOSED, json.status)
        self.assert_equals(Usernames.team_member, json.owner)

    def test_cannot_drag_task_if_not_a_team_member(self):
        req = self._request_for_ticket_change(username=Usernames.product_owner, simple_status='in_progress')
        self.teh.move_changetime_to_the_past([self.task])
        response = self.assert_method_returns_error(TicketUpdateView(self.env).do_post, req, req.args)
        self.assert_contains("doesn't belong to the team", response.errors[0])
        returned_ticket = ValueObject(response.current_data)
        self.assert_equals(Status.NEW, returned_ticket.status)
        self.assertEqual('', returned_ticket.owner)
    
    def test_get_ticket_without_cache_circumvents_cache(self):
        view = TicketUpdateView(self.env)
        newtask = self.teh.create_task()
        newtask[Key.REMAINING_TIME] = 3
        self.assert_equals('3', view._ticket(newtask.id)[Key.REMAINING_TIME])
        self.assert_equals('', view._ticket_without_cache(newtask.id)[Key.REMAINING_TIME])
    
    def test_move_ticket_to_custom_second_in_progress_status(self):
        self.teh.change_workflow_config([('fnodify', '* -> fnordified')])
        self.teh.clear_ticket_system_field_cache()
        json = self._set_status_with_json(Usernames.team_member, simple_status='fnordified')
        self.assert_equals("fnordified", json.status)
    
    def test_validates_existence_of_custom_status(self):
        self.teh.move_changetime_to_the_past([self.task])
        req = self._request_for_ticket_change(Usernames.team_member, simple_status='fnord')
        response = self.assert_method_returns_error(TicketUpdateView(self.env).do_post, req, req.args)
        self.assert_contains("Invalid status", response.errors[0])


class CanChangeTicketFieldsWithJSON(TicketChangeTestCase):
    
    def test_can_change_summary(self):
        json = self._change_ticket(Usernames.team_member, summary='new_fnord')
        self.assert_equals('new_fnord', json.summary)
    
    def test_cannot_change_custom_field_that_is_disabled_for_tasks(self):
        json = self._change_ticket(Usernames.team_member, businessvalue='100')
        self.assert_not_contains(Key.BUSINESS_VALUE, json)
        
        task_from_db = AgiloTicket(self.env, self.task.id)
        self.assert_equals('', task_from_db[Key.BUSINESS_VALUE])
    
    def test_cannot_change_to_value_that_is_not_an_option(self):
        req = self._request_for_ticket_change(Usernames.team_member, component='fnord')
        response = self.assert_method_returns_error(TicketUpdateView(self.env).do_post, req, req.args)
        self.assert_contains('is not a valid value', response.errors[0])
    
    def test_cannot_change_to_value_to_empty(self):
        self._change_ticket(Usernames.team_member, component='component1')
        task_from_db = AgiloTicket(self.env, self.task.id)
        self.assert_equals('component1', task_from_db[Key.COMPONENT])
        
        req = self._request_for_ticket_change(Usernames.team_member, component='')
        response = self.assert_method_returns_error(TicketUpdateView(self.env).do_post, req, req.args)
        self.assert_contains('must be set', response.errors[0])
        
        task_from_db = AgiloTicket(self.env, self.task.id)
        self.assert_equals('component1', task_from_db[Key.COMPONENT])
