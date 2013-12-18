# -*- coding: utf-8 -*-
#   Copyright 2008 Agile42 GmbH
#   Copyright 2011 Agilo Software GmbH All rights reserved
#
#   Author: 2008 Felix Schwarz <felix.schwarz_at_agile42.com>
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


from trac.util.translation import _
from trac.web.chrome import add_warning

from agilo.csv_import.import_performer import CSVBasePerformer
from agilo.utils import Key


class DeletePerformer(CSVBasePerformer):
    def __init__(self, env, number_rows_for_preview=20, force=False, *args, **kw):
        super(DeletePerformer, self).__init__(env, number_rows_for_preview=number_rows_for_preview, *args, **kw)
        self.force = force
    
    
    def commit(self, req):
        '''Perform the operation for all processed rows. Return a list of new 
        or changed tickets'''
        tickets = []
        
        if not self.do_preview:
            for fields in self.rows:
                ticket = self._get_ticket_from_id_in_csv(req, fields)
                if ticket == None:
                    continue
                ticket_type = self._get_type_for_ticket(fields)
                if not self._may_create_ticket(req.perm, ticket_type):
                    add_warning(req, _("No permission to create a %s.") % ticket_type)
                    continue
                
                if not self.force:
                    csv_summary = fields[Key.SUMMARY]
                    db_summary = ticket[Key.SUMMARY]
                    if csv_summary != db_summary:
                        msg = _("Ticket %d has a different summary: '%s' (CSV) - '%s' (DB)" )
                        add_warning(req, msg % (ticket.id, repr(csv_summary), repr(db_summary)))
                        continue
                tickets.append(ticket)
                ticket.delete()
        return tickets
    
    
    def check_header(self, header):
        """Check the headers for mandatory fields"""
        if not ((Key.ID in header) or ('ticket' in header)):
            return _("Header must contain '%s' or '%s'") % (Key.ID, 'ticket')
        if not (Key.SUMMARY in header):
            return _("Header must contain '%s'") % Key.SUMMARY
        return None
    
    
    def interesting_fieldnames(self):
        '''Return a list of field names which this performer will handle.'''
        return [Key.ID, Key.SUMMARY, 'ticket']

