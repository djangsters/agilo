# -*- coding: utf-8 -*-
#   Copyright 2008 Agile42 GmbH
#   Copyright 2011 Agilo Software GmbH All rights reserved
#
#   Author: 2008 Felix Schwarz <felix.schwarz__at__agile42.com>
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
#    Authors:
#            - Felix Schwarz <felix.schwarz__at__agile42.com>
#            - Andrea Tomasini <andrea.tomasini__at__agile42.com>

from trac.core import TracError
from trac.util.text import to_unicode
from trac.util.translation import _
from trac.web.chrome import add_warning

from agilo.csv_import.import_performer import CSVBasePerformer
from agilo.utils import Action, Key
from agilo.scrum.workflow.api import RuleValidationException
from agilo.ticket.api import AgiloTicketSystem


class UpdatePerformer(CSVBasePerformer):
    
    def check_header(self, header):
        """Check the headers for mandatory fields"""
        if not ((Key.ID in header) or ('ticket' in header)):
            return _("Header must contain '%s' or '%s'") % (Key.ID, 'ticket')
        if not (Key.SUMMARY in header):
            return _("Header must contain '%s'") % Key.SUMMARY
        return None
    
    
    def interesting_fieldnames(self):
        fieldnames = [Key.ID, 'ticket']
        for field in AgiloTicketSystem(self.env).get_ticket_fields():
            fieldname = field[Key.NAME]
            fieldnames.append(fieldname)
        return fieldnames
    
    
    def commit(self, req):
        tickets = []
        
        if not self.do_preview:
            interesting_fieldnames = self.interesting_fieldnames()
            for fields in self.rows:
                ticket = self._get_ticket_from_id_in_csv(req, fields)
                if ticket == None:
                    continue
                
                if not req.perm.has_permission(Action.TICKET_EDIT):
                    add_warning(req, _("No permission to edit ticket %d.") % ticket.id)
                    continue
                
                changed_something = False
                for key in fields:
                    if (key in interesting_fieldnames) and key not in [Key.ID, 'ticket']:
                    # Probably we should check more things here.
                    #if key in ticket.values:
                        if ticket[key] != fields[key]:
                            ticket[key] = fields[key]
                            changed_something = True
                
                if changed_something:
                    author = req.authname
                    comment = _("Update from CSV")
                    try:
                        ticket.save_changes(author, comment)
                    except RuleValidationException, e:
                        raise TracError(to_unicode(e))
                    tickets.append(ticket)
        return tickets

