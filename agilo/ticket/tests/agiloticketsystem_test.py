# -*- encoding: utf-8 -*-
#   Copyright 2009 Agile42 GmbH, Berlin (Germany)
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
#   
#   Author: 
#       - Felix Schwarz <felix.schwarz__at__agile42.com>


from trac.ticket.api import TicketSystem

from agilo.test import AgiloTestCase
from agilo.ticket.api import AgiloTicketSystem
from agilo.utils import Key, Type
from agilo.utils.config import AgiloConfig
from trac.ticket.default_workflow import ConfigurableTicketWorkflow,\
    get_workflow_config

class AgiloTicketSystemTest(AgiloTestCase):
    
    def test_agiloticketsystem_returns_the_same_number_of_custom_fields_as_trac(self):
        # This uncovered a bug in AgiloConfig when the AgiloTicketSystem was not
        # notified about config changes so it kept outdated caches.
        agilo_custom_fields = AgiloTicketSystem(self.env).get_custom_fields()
        trac_custom_fields = TicketSystem(self.env).get_custom_fields()
        self.assert_equals(len(agilo_custom_fields), len(trac_custom_fields))
    
    def test_knows_which_fieldnames_are_valid_for_a_ticket_type(self):
        ticket_system = AgiloTicketSystem(self.env)
        self.assert_contains(Key.REMAINING_TIME, ticket_system.get_ticket_fieldnames(Type.TASK))
        self.assert_not_contains(Key.BUSINESS_VALUE, ticket_system.get_ticket_fieldnames(Type.TASK))
    
    def test_can_determine_valid_ticket_statuses(self):
        valid_ticket_statuses = AgiloTicketSystem(self.env).valid_ticket_statuses()
        self.assert_contains('new', valid_ticket_statuses)
        self.assert_not_contains('fnord', valid_ticket_statuses)

    def test_finds_status_introduced_by_custom_workflow(self):
        self.teh.change_workflow_config([('fnordify', 'new -> fnord')])
        valid_ticket_statuses = AgiloTicketSystem(self.env).valid_ticket_statuses()
        self.assert_contains('fnord', valid_ticket_statuses)

    def test_restricting_owner_will_tranform_field_if_team_has_no_members(self):
        self.teh.create_sprint(self.sprint_name(), team="fnord")
        field = {"type": "fnord"}
        AgiloTicketSystem(self.env).eventually_restrict_owner(field, sprint_name=self.sprint_name())
        self.assert_equals("select", field["type"])
        self.assert_contains("options", field)
        self.assert_length(0, field["options"])
