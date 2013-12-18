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


from trac.core import TracError
from trac.resource import ResourceNotFound
from trac.util.text import to_unicode
from trac.util.translation import _
from trac.web.chrome import add_warning

from agilo.ticket.api import AgiloTicketSystem
from agilo.ticket.model import AgiloTicketModelManager
from agilo.utils import Action, Key, Type, Status
from agilo.utils.log import warning
from agilo.utils.compat import exception_to_unicode
from agilo.scrum.workflow.api import RuleValidationException


class CSVBasePerformer(object):
    """Base Performer class for CSV parsing"""
    def __init__(self, env, number_rows_for_preview=20):
        self.do_preview = False
        self.rows = []
        self.number_rows_for_preview = number_rows_for_preview
        self.env = env
        self.tm = AgiloTicketModelManager(self.env)
    
    def commit(self, req):
        '''Perform the operation for all processed rows. Return a list of new 
        or changed tickets'''
        raise NotImplementedError
    
    def check_header(self, header):
        """Check the headers for mandatory fields"""
        raise NotImplementedError
    
    def get_preview_rows(self):
        assert self.do_preview
        return self.rows
    
    def interesting_fieldnames(self):
        '''Return a list of field names which this performer will handle.'''
        raise NotImplementedError
    
    def name(self):
        'Return a human readable name of the performer.'
        return self.__class__.__name__
    
    def process(self, fields):
        '''Process the given row and save it for a later commit.'''
        if fields not in [None, {}]:
            if self.do_preview:
                if len(self.rows) < self.number_rows_for_preview:
                    self.rows.append(fields)
            else:
                self.rows.append(fields)
    
    def set_preview_mode(self):
        '''Tell the performer that it should only parse the lines for preview
        mode - therefore no data is changed.'''
        self.do_preview = True
    
    
    def _get_type_for_ticket(self, fields):
        type = Type.REQUIREMENT
        if Key.TYPE in fields:
            type = fields.pop(Key.TYPE).lower()
        return type
    
    def _may_create_ticket(self, perm, ticket_type):
        action_name = 'CREATE_%s' % ticket_type.upper()
        if hasattr(Action, action_name):
            permission = getattr(Action, action_name)
            return (permission in perm)
        return False # should be action_name in perm?
    
    def _get_ticket_from_id_in_csv(self, req, fields):
        ticket = None
        string_id = fields.get(Key.ID, fields.get('ticket'))
        try:
            ticket_id = int(string_id)
        except (ValueError, TypeError):
            add_warning(req, _("Non-numeric ticket ID '%s'") % string_id)
        else:
            try:
                ticket = self.tm.get(tkt_id=int(ticket_id))
            except ResourceNotFound:
                add_warning(req, _("Ticket %d does not exist") % ticket_id)
        return ticket


class ImportPerformer(CSVBasePerformer):
    """Performer that imports tickets from the CSV file"""
    def __init__(self, env, number_rows_for_preview=20):
        args = dict(number_rows_for_preview=number_rows_for_preview)
        super(ImportPerformer, self).__init__(env, **args)
    
    def check_header(self, header):
        if not (Key.SUMMARY in header):
            return _("Header must contain '%s'") % Key.SUMMARY
        return None
    
    def interesting_fieldnames(self):
        fieldnames = []
        for field in AgiloTicketSystem(self.env).get_ticket_fields():
            fieldname = field[Key.NAME]
            # AT: here key must be a string or will break the call
            # afterwards
            try:
                fieldname = str(fieldname)
            except ValueError, e:
                warning(self, "Fieldname: %s is not a string... %s" % \
                        (repr(fieldname), exception_to_unicode(e)))
                continue
            fieldnames.append(fieldname)
        return fieldnames
    
    def commit(self, req):
        tickets = []
        
        if not self.do_preview:
            for fields in self.rows:
                ticket_type = self._get_type_for_ticket(fields)
                if not self._may_create_ticket(req.perm, ticket_type):
                    add_warning(req, _("No permission to create a %s.") % ticket_type)
                    continue
                
                ticket_props = dict(t_type=ticket_type, status=Status.NEW,
                                    reporter=req.authname, owner='')
                for key in self.interesting_fieldnames():
                    if key in fields:
                        ticket_props[key] = fields[key]
                try:
                    ticket = self.tm.create(**ticket_props)
                    tickets.append(ticket)
                except RuleValidationException, e:
                    raise TracError(to_unicode(e))
        return tickets
        #post_process_special_fields(self.env, tkt, fields, self.messages)

