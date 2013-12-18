# -*- coding: utf-8 -*-
#   Copyright 2008 Agile42 GmbH - Andrea Tomasini
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
# Authors:
#     - Andrea Tomasini <andrea.tomasini__at__agile42.com>

from agilo.api import validator
from agilo.api import ICommand, Controller
from agilo.ticket.model import AgiloTicketModelManager
from agilo.utils import Key
from agilo.utils.config import AgiloConfig


class TicketController(Controller):
    """
    Ticket controller, handling all the commands for the tickets
    """
    class CreateTicketCommand(ICommand):
        """Creates a new ticket"""
        parameters = {'summary': validator.MandatoryStringValidator, 
                      't_type': validator.StringValidator,
                      'properties': validator.DictValidator}
        
        def _execute(self, controller, date_converter=None, 
                     as_key=None):
            """Execute the ticket creation"""
            # check if the type exists and is valid
            t_type = getattr(self, 't_type', None)
            props = getattr(self, 'properties', None) or {}
            if t_type and not t_type in \
                    AgiloConfig(controller.env).get_available_types():
                raise self.CommandError("The provided type is not existing")
            
            return controller.manager.create(summary=self.summary,
                                             t_type=t_type,
                                             **props)
        
        
    class GetTicketCommand(ICommand):
        """
        Retrieves a ticket given an id, that is the only primary key
        """
        parameters = {'ticket': validator.MandatoryTicketValidator, 
                      't_type': validator.StringValidator}
        
        def _execute(self, controller, date_converter=None, 
                     as_key=None):
            """Get the ticket from the Model Manager and return it"""
            return self.return_as_value_object(self.ticket)
    
    
    class SaveTicketCommand(GetTicketCommand):
        """Saves a ticket"""
        parameters = {'ticket': validator.MandatoryTicketValidator, 
                      't_type': validator.StringValidator, 
                      'properties': validator.DictValidator}
        
        def _execute(self, controller, date_converter=None, 
                     as_key=None):
            """Saves the ticket"""
            for name, value in self.properties.items():
                if hasattr(self.ticket, name) and not \
                        callable(getattr(self.ticket, name)):
                    setattr(self.ticket, name, value)
                #elif name in ticket.fields_for_type:
                # AT: it is too much restrictive, setting a key which
                # won't be used is not hurting anyone.
                else:
                    self.ticket[name] = value
            # now save it
            return controller.manager.save(self.ticket)
    
    
    class ListTicketsCommand(ICommand):
        """Returns a list of tickets matching the given parameters"""
        parameters = {'criteria': validator.DictValidator, 
                      'order_by': validator.IterableValidator, 
                      'limit': validator.IntValidator, 
                      'with_attributes': validator.IterableValidator}
        
        def _execute(self, controller, date_converter=None, 
                     as_key=None):
            """
            Performs a select on the model manager to fetch the
            tickets matching the query parameters
            """
            params = {'criteria': self.criteria,
                      'order_by': self.order_by,
                      'limit': self.limit}
            get_tickets = controller.manager.select
            if self.with_attributes:
                params['properties'] = self.with_attributes
                get_tickets = controller.manager.select_tickets_having_properties
            # Now perform the command
            return get_tickets(**params)
    
    
    class FilterTicketsWithAttribute(ICommand):
        parameters = {'tickets': validator.IterableValidator,
                      'attribute_name': validator.StringValidator}

        def _execute(self, controller, date_converter, as_key):
            # avoid circular imports
            from agilo.scrum.backlog import Backlog
            result_tickets = []
            for ticket_or_bi in self.tickets:
                if isinstance(ticket_or_bi, Backlog.BacklogItem):
                    ticket_or_bi = ticket_or_bi.ticket
                if ticket_or_bi.is_readable_field(self._attribute_name):
                    result_tickets.append(self.return_as_value_object(ticket_or_bi))
            return result_tickets

    
    class FindOrphanTasks(ICommand):
        """Returns a list of orphan tasks from a given list of all tickets."""
        
        parameters = {'tickets': validator.IterableValidator}
        
        def _execute(self, controller, date_converter, as_key):
            orphans = []
            
            cmd = TicketController.FilterTicketsWithAttribute(controller.env,
                                                              tickets=self.tickets, 
                                                              attribute_name=Key.REMAINING_TIME)
            cmd.native = True
            tasks = TicketController(controller.env).process_command(cmd)
            
            for ticket in tasks:
                if len(ticket.get_incoming()) == 0 or \
                        (not ticket.get_incoming()[0].is_readable_field(Key.STORY_POINTS)):
                    orphans.append(ticket)
            return orphans
    
    
    def __init__(self):
        """Initialize taking a reference to the ticket model manager"""
        self.manager = AgiloTicketModelManager(self.env)
        
