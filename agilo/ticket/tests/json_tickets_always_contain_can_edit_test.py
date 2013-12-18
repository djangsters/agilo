# -*- coding: utf8 -*-
#   Copyright 2009 agile42 GmbH All rights reserved
#   Copyright 2011 Agilo Software GmbH All rights reserved
#
#   Authors:
#        - Martin Häcker <martin.haecker__at__agile42.com>

import agilo.utils.filterwarnings

from datetime import timedelta

from trac.web import RequestDone

from agilo.test import AgiloTestCase
from agilo.ticket.json_ui import TicketUpdateView, TicketCreateView
from agilo.utils import Type, Action
from agilo.utils.days_time import now
from agilo.utils.compat import json


class TestAllJSONConversionsOfTicketsContainCanEdit(AgiloTestCase):
    
    def setUp(self):
        self.super()
        self.task = self.teh.create_ticket(Type.TASK)
        self.task.last_changed = now() - timedelta(seconds=3)
        self.req = self.teh.mock_request(username='foo', args={'ticket_id':self.task.id}, method='POST')
    
    def ticket_as_json(self, a_ticket):
        ticket_json = a_ticket.as_dict()
        ticket_json['ticket_id'] = ticket_json['id']
        return ticket_json
    
    def update_contains_can_edit(self, args):
        json = self.ticket_as_json(self.task)
        json.update(args)
        from agilo.ticket import AgiloTicketSystem
        if AgiloTicketSystem.is_trac_1_0():
            from trac.util.datefmt import to_utimestamp
            json.update(dict(view_time=str(to_utimestamp(self.task.time_changed)), submit=True))

        view = TicketUpdateView(self.env)
        result = view.do_post(self.req, json)
        return result['can_edit']
    
    def test_contains_can_edit_on_error(self):
        self.assert_raises(RequestDone, self.update_contains_can_edit, {})
        ticket = json.loads(self.req.response.body)['current_data']
        self.assert_false(ticket['can_edit'])
    
    def test_contains_can_edit_on_success(self):
        self.teh.grant_permission('foo', Action.TRAC_ADMIN)
        self.assert_true(self.update_contains_can_edit(dict(summary='foo')))
    
    def test_contains_can_edit_on_ticket_creation(self):
        self.teh.grant_permission('foo', Action.TRAC_ADMIN)
        json = self.ticket_as_json(self.task)
        view = TicketCreateView(self.env)
        result = view.do_put(self.req, json)
        self.assert_true(result['can_edit'])



if __name__ == '__main__':
    from agilo.test import run_unit_tests
    run_unit_tests(__file__)
