# -*- coding: utf8 -*-
#   Copyright 2009 agile42 GmbH All rights reserved
#   Copyright 2011 Agilo Software GmbH All rights reserved
#
#   Authors:
#        - Martin Häcker <martin.haecker__at__agile42.com>

from trac.test import MockPerm

from agilo.api import ValueObject
from agilo.utils import Type, Action
from agilo.test import AgiloTestCase
from agilo.ticket.json_ui import TicketUpdateView, TicketCreateView


# Tracs MockPerm has to few parameters for has_permission which takes an action _and_ a resource
# See Trac #8590 <http://trac.edgewall.org/ticket/8590>
class AgiloMockPerm(MockPerm):
    """Fake permission class. Copied and changed from trac.perm"""
    
    def __init__(self, *allowed_permissions):
        self.allowed_permissions = allowed_permissions
    
    def has_permission(self, action, realm_or_resource=None, id=False, version=False):
        return action in self.allowed_permissions
    __contains__ = has_permission


class TestErrorHandlingAlwaysIncludesLatestTicketData(AgiloTestCase):
    
    def setUp(self):
        self.super()
        self.task = self.teh.create_ticket(Type.TASK)
        self.req = self.teh.mock_request(username='foo', 
                                         args={'ticket_id':self.task.id},
                                         perm=AgiloMockPerm(Action.TICKET_VIEW))
    
    def mock(self, klass):
        view = klass(self.env)
        def mock_respond(req, data, code=200):
            self.data = ValueObject(data)
            self.code = code
            assert 'errors' in data
            self.errors = self.data.errors
            assert 'current_data' in data
            self.current_data = self.data.current_data
        
        view.respond = mock_respond
        return view
    
    def ticket_as_json(self, task):
        ticket_json = task.as_dict()
        ticket_json['can_edit'] = False
        return ticket_json
    
    def test_smoke(self):
        self.mock(TicketUpdateView).error_response(self.req, {}, 'fake error', 500)
        self.assert_equals(self.code, 500)
        self.assert_equals(self.data['errors'], 'fake error')
        self.assert_equals(self.errors, 'fake error')
        json = self.ticket_as_json(self.task)
        self.assert_equals(json, self.data['current_data'])
        self.assert_equals(json, self.current_data)
    
    def test_only_adds_ticket_if_no_current_data_is_there(self):
        fnord = {'fnord': 'fnord'}
        self.mock(TicketUpdateView).error_response(self.req, fnord, 'unused')
        self.assert_equals(fnord, self.current_data)
    
    def test_leaves_current_data_empty_if_no_ticket_id_can_be_found(self):
        view = self.mock(TicketUpdateView)
        view.get_ticket_id = lambda unused: None
        view.error_response(self.req, {}, 'unused')
        self.assert_equals({}, self.current_data)
    
    def test_only_adds_current_ticket_data_if_view_permission_is_there(self):
        self.req.perm = AgiloMockPerm()
        self.assert_equals(self.req.perm.has_permission(Action.TICKET_VIEW, self.task), False)
        self.mock(TicketUpdateView).error_response(self.req, {}, 'unused')
        self.assert_equals({}, self.current_data)
    
    def test_also_works_on_TicketCreateView(self):
        view = self.mock(TicketCreateView)
        del self.req.args['ticket_id']
        view.error_response(self.req, {}, 'unused')
        self.assert_equals({}, self.current_data)
        
        self.req.args['ticket_id'] = self.task.id
        view.error_response(self.req, {}, 'unused')
        self.assert_equals(self.ticket_as_json(self.task), self.current_data)
    
