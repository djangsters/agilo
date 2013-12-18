# -*- encoding: utf-8 -*-
#   Copyright 2008 Agile42 GmbH, Berlin (Germany)
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
#   Authors:
#       - Andrea Tomasini <andrea.tomasini__at__agile42.com>

from agilo.api import validator
from agilo.utils import Key, Type
from agilo.test import AgiloTestCase
from agilo.ticket.controller import TicketController


class TestTicketController(AgiloTestCase):
    """Tests the ticket controller commands"""
    def setUp(self):
        self.super()
        self.controller = TicketController(self.env)
    
    def test_get_ticket_command(self):
        """Tests the get ticket command"""
        t1 = self.teh.create_ticket(Type.TASK, 
                                    props={Key.REMAINING_TIME: '12'})
        cmd_get = TicketController.GetTicketCommand(self.env,
                                                    ticket=t1.id)
        t1_c = self.controller.process_command(cmd_get)
        self.assert_not_none(t1_c)
        self.assert_equals(t1[Key.SUMMARY], t1_c[Key.SUMMARY])
        # Try a non existing ticket
        try:
            cmd_get.ticket = 0
            self.fail("Could set 0 as a ticket id")
        except validator.ValidationError:
            pass
        
    def test_list_tickets_command(self):
        """Tests the get list of tickets command"""
        t1 = self.teh.create_ticket(Type.USER_STORY,
                                    props={Key.STORY_POINTS: '13'})
        t2 = self.teh.create_ticket(Type.TASK,
                                    props={Key.REMAINING_TIME: '16'})
        cmd_list = TicketController.ListTicketsCommand(self.env)
        l = self.controller.process_command(cmd_list)
        self.assert_equals(2, len(l))
        self.assert_true(t1 in l)
        self.assert_true(t2 in l)
        # now filter on those with attribute remaining time
        cmd_list = TicketController.ListTicketsCommand(self.env, with_attributes=[Key.REMAINING_TIME])
        l = self.controller.process_command(cmd_list)
        self.assert_not_contains(t1, l)
        self.assert_contains(t2, l)
        self.assert_equals(1, len(l))

    def test_create_ticket_command(self):
        """Tests the create ticket command"""
        cmd_create = TicketController.CreateTicketCommand(self.env,
                                                         summary='This is a ticket')
        t = self.controller.process_command(cmd_create)
        self.assert_true(t.exists)
        self.assert_equals('This is a ticket', t[Key.SUMMARY])
        
    def test_save_ticket_command(self):
        """Tests the save ticket command"""
        cmd_create = TicketController.CreateTicketCommand(self.env,
                                                          summary='This is a ticket')
        t = self.controller.process_command(cmd_create)
        self.assert_true(t.exists)
        self.assert_equals('This is a ticket', t[Key.SUMMARY])
        cmd_save = TicketController.SaveTicketCommand(self.env,
                                                      ticket=t.id,
                                                      properties={Key.DESCRIPTION: 'Hey!'})
        self.controller.process_command(cmd_save)
        # Now verify that the ticket has really been saved
        self.controller.manager.get_cache().invalidate()
        cmd_get = TicketController.GetTicketCommand(self.env,
                                                    ticket=t.id)
        t_reloaded = self.controller.process_command(cmd_get)
        self.assert_not_none(t_reloaded)
        self.assert_equals('Hey!', t_reloaded[Key.DESCRIPTION])
        

if __name__ == '__main__':
    from agilo.test import testfinder
    testfinder.run_unit_tests(__file__)

