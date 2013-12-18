# -*- encoding: utf-8 -*-
#   Copyright 2008-2009 Agile42 GmbH, Berlin (Germany)
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

from agilo.api import controller, validator
from agilo.scrum.backlog.model import BacklogModelManager


__all__ = ['BacklogController']


class BacklogController(controller.Controller):
    """Controller to perform operations on the Backlog Object"""
    
    def __init__(self):
        """Create a reference to the Model Manager"""
        self.manager = BacklogModelManager(self.env)
    
    @classmethod
    def backlog(cls, env, name, scope):
        cmd_get = BacklogController.GetBacklogCommand(env, name=name, scope=scope)
        backlog = BacklogController(env).process_command(cmd_get)
        return backlog
    
    class GetBacklogCommand(controller.ICommand):
        """Retrieves a Backlog given its name. The reload parameter,
        set to True force a reload of the backlog tickets."""
        # AT: Due to the implemented Object Identity though, there should 
        # not be any need of reloading a backlog, the parameters is 
        # offered to be used in those cases when a server with 
        # multiple processors uses a Python VM which is not supporting 
        # that configuration de facto duplicating the items in every 
        # VM space.
        parameters = {'name': validator.MandatoryStringValidator,
                      'scope': validator.StringValidator,
                      'reload': validator.BoolValidator,
                      'filter_by': validator.StringValidator,
                      'load': validator.BoolValidator}
        
        def _execute(self, backlog_controller, date_converter, as_key):
            return backlog_controller.manager.get(name=self.name,
                                                  scope=self.scope)
    
    
    class ListBacklogsCommand(controller.ICommand):
        """Returns the list of Backlogs available"""
        parameters = {}
        
        def _execute(self, backlog_controller, date_converter, as_key):
            backlog_list = backlog_controller.manager.select(order_by=['type', 'name'])
            return [controller.ValueObject(b.as_dict()) \
                    for b in backlog_list]
    
    
    class CreateBacklogCommand(controller.ICommand):
        """Creates a Backlog object with the given properties"""
        parameters = {'name': validator.MandatoryStringValidator,
                      'ticket_types': validator.IterableValidator, 
                      'scope': validator.StringValidator,
                      'type': validator.IntValidator,
                      'description': validator.StringValidator}
        
        def _execute(self, backlog_controller, date_converter, as_key):
            """Create the backlog and returns it after saving it"""
            return backlog_controller.manager.create(name=self.name,
                                                     ticket_types=self.ticket_types,
                                                     scope=self.scope,
                                                     type=self.type,
                                                     description=self.description)
    
    
    def move(self, name, scope, ticket, to_pos, from_pos=None):
        cmd_get = BacklogController.MoveBacklogItemCommand(self.env, name=name, scope=scope,
                                                           ticket=ticket, to_pos=to_pos)
        self.process_command(cmd_get)
    
    class MoveBacklogItemCommand(GetBacklogCommand):
        """Allows to move a Backlog Item from a position to another of
        a backlog identified by name and scope."""
        
        parameters = {'name': validator.MandatoryStringValidator,
                      'scope': validator.StringValidator,
                      'ticket': validator.MandatoryTicketValidator,
                      'to_pos': validator.MandatoryIntValidator}
        
        def _execute(self, backlog_controller, date_converter, as_key):
            """Execute the item move"""
            # We always have to load the tickets or we can't move anything
            self.reload = True
            
            s_cmd = super(BacklogController.MoveBacklogItemCommand, self)
            backlog = s_cmd._execute(backlog_controller, date_converter, as_key)
            return backlog.insert(self.to_pos, self.ticket)
    
    @classmethod
    def set_ticket_positions(cls, env, name, scope, positions):
        command = cls.SetBacklogTicketPositionsCommand(env, name=name, scope=scope, positions=positions)
        return cls(env).process_command(command)
    
    class SetBacklogTicketPositionsCommand(GetBacklogCommand):
        """Allows to set all positions for multiple backlog items at once.
        Will remove all positions of items that don't get a new position"""
        
        parameters = {'name': validator.MandatoryStringValidator,
                      'scope': validator.StringValidator,
                      'positions': validator.MandatoryIterableIntValidator}
        
        def _execute(self, backlog_controller, date_converter, as_key):
            self.load = False
            cmd_get = super(BacklogController.SetBacklogTicketPositionsCommand, self)
            backlog = cmd_get._execute(backlog_controller, date_converter=date_converter, as_key=as_key)
            backlog.set_ticket_positions(self.positions)

    class SaveBacklogCommand(GetBacklogCommand):
        """Saves the Backlog with the given parameters"""
        
        parameters = {'name': validator.MandatoryStringValidator,
                      'ticket_types': validator.IterableValidator, 
                      'scope': validator.StringValidator,
                      'b_type': validator.IntValidator, 
                      'description': validator.StringValidator}
        
        def _execute(self, backlog_controller, date_converter, as_key):
            # Retrieves and save the backlog
            s_cmd = super(BacklogController.SaveBacklogCommand, self)
            backlog = s_cmd._execute(backlog_controller, date_converter, as_key)
            
            for param in self.parameters:
                value = getattr(self, param, None)
                if value is not None:
                    setattr(backlog, param, value)
            # Now use the manager to save the backlog
            return backlog_controller.manager.save(backlog)
    
