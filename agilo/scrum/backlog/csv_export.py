# -*- encoding: utf-8 -*-
#   Copyright 2009-2010 Agile42 GmbH, Berlin (Germany)
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

import csv
from StringIO import StringIO

from trac.core import Component, implements
from trac.mimeview import Mimeview
from trac.mimeview.api import IContentConverter, Context
from trac.resource import Resource
from trac.util.translation import _
from trac.web.chrome import add_link, Chrome

from agilo.ticket import AgiloTicketSystem
from agilo.utils import Action, Key


__all__ = ['add_backlog_conversion_links', 'BacklogContentConverter', 'send_backlog_as']


BACKLOG_CONVERSION_KEY = 'agilo.scrum.backlog.Backlog'

def add_backlog_conversion_links(env, req, backlog, backlog_url):
    # TODO: Move tests to new backlog
    mime = Mimeview(env)
    for conversion in mime.get_supported_conversions(BACKLOG_CONVERSION_KEY):
        format = conversion[0]
        title = conversion[1]
        mimetype = conversion[4]
        backlog_href = req.href(backlog_url, backlog.name, backlog.scope, format=format)
        add_link(req, 'alternate', backlog_href, title, mimetype, format)


def send_backlog_as(env, req, backlog, format):
    "This method will handle the request completely, will not return"
    mime = Mimeview(env)
    mime.send_converted(req, BACKLOG_CONVERSION_KEY, backlog, format, filename=backlog.scope)


class BacklogContentConverter(Component):
    
    implements(IContentConverter)
    
    def get_supported_conversions(self):
        yield ('csv', _('Comma-delimited Text'), 'csv',
               BACKLOG_CONVERSION_KEY, 'text/csv', 9)
    
    def convert_content(self, req, mimetype, backlog, key):
        """Convert the given content from mimetype to the output MIME type
        represented by key. Returns a tuple in the form (content,
        output_mime_type) or None if conversion is not possible."""
        if key == 'csv':
            return self.export_csv(req, backlog, mimetype='text/csv')
    
    def _get_field_names(self, backlog):
        """Return an ordered collection of all field names which appear in one 
        of the tickets for this backlog."""
        ticket_types = set()
        for bi in backlog:
            ticket_types.add(bi[Key.TYPE])
        
        field_names = set()
        ats = AgiloTicketSystem(self.env)
        for ticket_type in ticket_types:
            for field in ats.get_ticket_fields(ticket_type):
                field_names.add(field[Key.NAME])
        return list(field_names)
    
    def _export_ticket(self, req, ticket, writer, field_names):
        
        cols = [unicode(ticket.id)]
        for name in field_names:
            value = ticket[name] or ''
            if name in ('cc', 'reporter'):
                context = Context.from_request(req, ticket.resource)
                value = Chrome(self.env).format_emails(context, value, ' ')
            cols.append(unicode(value).encode('utf-8'))
        writer.writerow(cols)
    
    def export_csv(self, req, backlog, sep=',', mimetype='text/plain'):
        field_names = self._get_field_names(backlog)
        content = StringIO()
        writer = csv.writer(content, delimiter=sep, quoting=csv.QUOTE_MINIMAL)
        writer.writerow(['id'] + [unicode(name) for name in field_names])
        
        for bi in backlog:
            ticket = bi.ticket
            ticket_resource = Resource('ticket', ticket.id)
            if Action.TICKET_VIEW in req.perm(ticket_resource):
                self._export_ticket(req, ticket, writer, field_names)
        return (content.getvalue(), '%s;charset=utf-8' % mimetype)
