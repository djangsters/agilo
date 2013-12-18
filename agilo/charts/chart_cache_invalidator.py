# -*- encoding: utf-8 -*-
#   Copyright 2009 Agile42 GmbH, Berlin (Germany)
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
#        - Felix Schwarz <felix.schwarz__at__agile42.com>

from trac.core import Component, implements
from trac.ticket.api import ITicketChangeListener

from agilo.charts.chart_generator import ChartGenerator
from agilo.ticket import AgiloTicket
from agilo.utils import Key


__all__ = ['ChartsCacheInvalidator']


class ChartsCacheInvalidator(Component):
    implements(ITicketChangeListener)
    
    def _get_sprint_name(self, ticket):
        """Returns the sprint name for the given ticket."""
        sprint_name = ticket[Key.SPRINT]
        if not sprint_name:
            for parent in ticket.get_incoming():
                if parent.is_readable_field(Key.SPRINT):
                    sprint_name = parent[Key.SPRINT]
                    break
        return sprint_name
    
    def ticket_created(self, ticket):
        ticket = AgiloTicket.as_agilo_ticket(ticket)
        if ticket[Key.SPRINT] or ticket.is_writeable_field(Key.REMAINING_TIME):
            sprint = self._get_sprint_name(ticket)
            generator = ChartGenerator(self.env)
            generator.invalidate_cache(sprint_name=sprint)
    
    def ticket_changed(self, ticket, comment, author, old_values):
        ticket = AgiloTicket.as_agilo_ticket(ticket)
        generator = ChartGenerator(self.env)
        # AT: this will only work if the task has been explicitly planned for 
        # the sprint, otherwise it won't update. The sprint change is good for
        # task containers.
        #if ticket[Key.SPRINT]:
        if ticket[Key.SPRINT] or ticket.is_writeable_field(Key.REMAINING_TIME):
            sprint = self._get_sprint_name(ticket)
            generator.invalidate_cache(sprint_name=sprint)
        if old_values.get(Key.SPRINT) and old_values[Key.SPRINT] != ticket[Key.SPRINT]:
            generator.invalidate_cache(sprint_name=old_values[Key.SPRINT])
    
    def ticket_deleted(self, ticket):
        ticket = AgiloTicket.as_agilo_ticket(ticket)
        if ticket[Key.SPRINT] or ticket.is_writeable_field(Key.REMAINING_TIME):
            sprint = self._get_sprint_name(ticket)
            generator = ChartGenerator(self.env)
            generator.invalidate_cache(sprint_name=sprint)

