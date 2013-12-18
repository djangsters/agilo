# -*- encoding: utf-8 -*-
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
#   Authors: 
#       - Stefano Rago <stefano.rago__at__agilosoftware.com>

import string
import copy
from agilo.utils.compat import json
from operator import attrgetter
from StringIO import StringIO

from agilo.utils import Key
from agilo.scrum.backlog.json_ui import ConfiguredChildTypesView

class BacklogRenderer:
    
    def __init__(self, env, backlog):
        self.backlog = backlog
        self.env = env
        self.backlog_values = backlog.values()
        self.tickets_with_multiple_parents = []
        self.link_tree = ConfiguredChildTypesView(self.env).link_tree()
        self.backlog_values_as_dict = self.backlog_values_as_dict()
    
    def backlog_values_as_dict(self):
        values_as_dict = dict()
        for item in self.backlog_values:
            values_as_dict[item.ticket.id] = item
        return values_as_dict
            
    
    def ticket_has_parents(self, ticket):
        parents = []
        for incoming in ticket.get_incoming():
            if incoming in self.backlog_values:
                parents.append(incoming)
        return len(parents) > 0
    
    def configured_child_types_for_type(self, ticket_type):
        child_types = [];
        for possible_child in self.link_tree[ticket_type]:
            child_types.append(possible_child);

        return child_types

    def ticket_is_container(self, ticket):
        accessible_types = self.backlog.config.ticket_types
        container_types = [] 
        for ticket_type in accessible_types:
            if len(self.configured_child_types_for_type(ticket_type)) != 0:
                container_types.append(ticket_type)
        
        return ticket[Key.TYPE] in container_types
    
    def ticket_has_multiple_parents(self, ticket):
        return len(ticket.get_incoming()) > 1

    def get_top_level_containers(self):
        containers = []
        for item in self.backlog_values:
            if self.ticket_is_container(item.ticket) and not self.ticket_has_parents(item.ticket):
                containers.append(item)
        return containers
    
    def get_tickets_with_no_parents(self):
        tickets = []
        for item in self.backlog_values:
            if not self.ticket_is_container(item.ticket) and not self.ticket_has_parents(item.ticket):
                tickets.append(item)
        return tickets
    
    def _append_backlog_item_html_to_string(self, file_str, item, level=1, parent=None):
        item_id = item.ticket.id
        item_html_id = str(item_id)
        ticket_type = item.ticket.get_type()
        status = item.ticket.values['status']
        owner = item.ticket.values['owner']
        is_container = self.ticket_is_container(item.ticket)
        has_multiple_parents = self.ticket_has_multiple_parents(item.ticket)
        if has_multiple_parents:
            if item_id in self.tickets_with_multiple_parents:
                if parent is not None and self.backlog_values_as_dict.has_key(parent.ticket.id):
                    item_html_id += "-" + str(parent.ticket.id)
            else:
                self.tickets_with_multiple_parents.append(item_id)

        if is_container and level > 1:
            file_str.write('<dd class="childcontainer">')
        if is_container:
            file_str.write('<dl>')
            file_str.write('<dt class="container ')
        else:
            file_str.write('<dd class="leaf ')
        if has_multiple_parents:
            file_str.write('multi-linked-item ')

        html_text = 'handle level-$level ' +\
                       'tickettype-$type '+\
                       'ticketstatus-$status" '+\
                       'id="ticketID-$html_id" '+\
                       'data=\"$data\">'
                            
        html_template = string.Template(html_text)
        data_dict = item.ticket.as_dict()
        if data_dict.has_key('description'):
            del data_dict['description']
        from agilo.ticket import AgiloTicketSystem
        if AgiloTicketSystem.is_trac_1_0():
            from trac.util.datefmt import to_utimestamp
            data_dict.update({'view_time': str(to_utimestamp(item.ticket.time_changed))})

        data_dump = json.dumps(data_dict)

        import trac.util

        file_str.write(html_template.substitute({'level': level,
                                                  'type': ticket_type,
                                                  'status': status,
                                                  'id': item_id,
                                                  'html_id': item_html_id,
                                                  'owner': owner,
                                                  'ts': str(item.ticket.time_changed),
                                                  'data': trac.util.escape(data_dump)
                                                  }))
        
        for field in self.column_names:
            if field == 'id':
                ticket_url = ""
                if self.base_url != "" and self.base_url != "/":
                    ticket_url = self.base_url + ticket_url 
                ticket_url = ticket_url + "/ticket/%s" % item_id
                file_str.write('<span class="%s numeric" data="{field:\'%s\'}"><a href="%s">%s</a></span>' %(field, field, ticket_url, item_id))
            else:
                actual_field = field
                if isinstance(field, list):
                    actual_field = field[0]
                    for alternative in field:
                        if alternative in item.fields_for_type or alternative in item.ticket.get_calculated_fields_names():
                            actual_field = alternative
                data_field = actual_field
                if actual_field not in item.fields_for_type:
                    data_field = ''
                css_class = actual_field
                if actual_field in item.ticket.get_calculated_fields_names():
                    css_class += " numeric"
                
                value = item.get(actual_field)
                        
                if value is None:
                    value = ""
                try:
                    file_str.write('<span class="%s" data="{field:\'%s\'}">%g</span>' %(css_class, data_field, value))
                except TypeError:
                    file_str.write('<span class="%s" data="{field:\'%s\'}">%s</span>' %(css_class, data_field, value))
        if is_container:
            file_str.write('</dt>')
        else:
            file_str.write('</dd>')
        children = item.ticket.get_outgoing()
        
        def index_for_item(item):
            if self.backlog_values_as_dict.has_key(item.id):
                return self.backlog_values.index(item)
            else:
                return None
            
        sorted_children = sorted(children, key=lambda item: index_for_item(item))
        
        for child in sorted_children:
            if self.backlog_values_as_dict.has_key(child.id):
                self._append_backlog_item_html_to_string(file_str, self.backlog_values_as_dict[child.id], level = level+1, parent=item)
        if is_container:
            file_str.write('</dl>')
        if is_container and level > 1:
            file_str.write('</dt>')

                
    def _append_totals_row(self, file_str):
        file_str.write('<dl class="no_drag"><dt id="ticketID--2" class="total container" onload="alert(\'test\')">')
        file_str.write('<span class="id numeric"></span>')
        file_str.write('<span class="summary">Totals</span>')
        for field in self.column_names:
            if isinstance(field, list):
                field = field[0]
            if field not in ['summary', 'id']:
                file_str.write('<span class="numeric %s" data="{field:\'%s\'}"></span>' %(field, field))
        file_str.write('</dt></dl>')

    def _append_unreferenced_tickets(self, file_str, tickets):
        file_str.write('<dl class="no_drag"><dt id="ticketID--1" class="container unreferenced">')
        file_str.write('<span class="id numeric" data="{field:\'id\'}" style="visibility:hidden">-1</span>')
        file_str.write('<span class="summary" data="{field:\'summary\'}">Tasks without Stories</span>')
        for field in self.column_names:
            if isinstance(field, list):
                field = field[0]
            if field == 'id':
                continue
            file_str.write('<span class="%s" data="{field:\'%s\'}"></span>' %(field, field))
        file_str.write('</dt>')
        for item in tickets:
            self._append_backlog_item_html_to_string(file_str, item, level=2)
        file_str.write('</dl>')

    def flatten(self, a_list):
        result = []
        for item in a_list:
            if hasattr(item, '__iter__'):
                for sub_item in self.flatten(item):
                    result.append(sub_item)
            else:
                result.append(item)
        return result

    def get_backlog_table_html(self, base_url):
        file_str = StringIO()
        self.column_names = self.backlog.config.backlog_column_names()
        self.base_url = base_url
        for item in self.get_top_level_containers():
            self._append_backlog_item_html_to_string(file_str, item)
        tickets_with_no_parents = self.get_tickets_with_no_parents()
        if len(tickets_with_no_parents) > 0:
            self._append_unreferenced_tickets(file_str, tickets_with_no_parents)
        self._append_totals_row(file_str)
        return file_str.getvalue()
    
    
