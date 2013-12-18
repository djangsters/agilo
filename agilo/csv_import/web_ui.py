# -*- coding: utf-8 -*-
#   Copyright 2008 Agile42 GmbH - Andrea Tomasini 
#   Copyright 2007 Andrea Tomasini <andrea.tomasini_at_agile42.com>
#                  Alexander Aptus <alexander.aptus_at_gmail.com>
#   Copyright 2011 Agilo Software GmbH All rights reserved
#
#   Licensed under the Apache License, Version 2.0 (the 'License');
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an 'AS IS' BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
# 
# Authors:
#     - Alexander Aptus
#     - Andrea Tomasini
#     - Felix Schwarz


import base64
import os
from StringIO import StringIO

from trac.core import Component, implements
from trac.util.compat import set
from trac.util.translation import _
from trac.web import IRequestHandler
from trac.web.chrome import add_notice, add_warning
from trac.wiki.formatter import wiki_to_html

from agilo_lib import chardet

from agilo.csv_import import IMPORT_URL, IMPORT_TEMPLATE
from agilo.csv_import.csv_file import CSVFile
from agilo.csv_import.import_performer import ImportPerformer
from agilo.csv_import.delete_performer import DeletePerformer
from agilo.csv_import.update_performer import UpdatePerformer
from agilo.utils import Key
from agilo.utils.log import error



class ImportParameter(object):
    DO_DELETE       = 'do_delete'
    DO_IMPORT       = 'do_import'
    DO_UPDATE       = 'do_update'
    
    ATTACHMENT      = 'attachment'
    FORCE           = 'force'
    FILE_ENCODING   = 'file_encoding'
    PERFORM_ACTION  = 'perform_action'


class ImportCSVModule(Component):
    '''Import CSV'''
    
    implements(IRequestHandler)
    
    def _get_upload_file_size(self, upload_fp):
        if hasattr(upload_fp, 'fileno'):
            try:
                size = os.fstat(upload_fp.fileno())[6]
            except Exception, e:
                msg = _("Can't get size of uploaded file because of %s") % e
                error(self, msg)
                return None
        elif hasattr(upload_fp, 'len'):
            size = upload_fp.len
        else:
            old_fpos = upload_fp.tell()
            upload_fp.seek(0, 2)
            size = upload_fp.tell()
            upload_fp.seek(old_fpos, 0)
        return size
    
    
    def _get_uploaded_file(self, req):
        upload = req.args.get(ImportParameter.ATTACHMENT)
        if upload == None:
            # no warning if the user just enters the site
            return None
        elif hasattr(upload, 'file'):
            upload_fp = StringIO(upload.file.read())
        elif isinstance(upload, basestring):
            upload_fp = StringIO(base64.decodestring(upload))
        else:
            add_warning(req, _('No file uploaded.'))
            return None
        size = self._get_upload_file_size(upload_fp)
        if size in [None, 0]:
            add_warning(req, _('Uploaded file is empty.'))
            return None
        return upload_fp
    
    
    # IRequestHandler methods
    def match_request(self, req):
        return req.path_info.startswith(IMPORT_URL)
    
    
    def _guess_encoding(self, upload_file):
        encoding = None
        if hasattr(upload_file, 'read'):
            raw_contents = upload_file.read()
            upload_file.seek(0)
            
            guess = chardet.detect(raw_contents)
            if guess.get('confidence', 0) > 0.5:
                encoding = guess['encoding'].upper()
            else:
                msg = _('Was not able to detect file encoding, defaulting to UTF-8')
                add_notice(msg)
                encoding = "UTF-8"
        return encoding
    
    
    def _get_page_title_and_action_label(self, action, show_file_upload, show_preview):
        title, action_label = None, None
        if action == ImportParameter.DO_UPDATE:
            action_label = _("Update")
            if show_file_upload:
                title = _("Update Existing Tickets from CSV")
            elif show_preview:
                title = _("Update Preview")
            else:
                title = _('Updated Tickets')
        elif action == ImportParameter.DO_DELETE:
            action_label = _("Delete")
            if show_file_upload:
                title = _("Delete Existing Tickets from CSV")
            elif show_preview:
                title = _("Delete Preview")
            else:
                title = _('Deleted Tickets')
        else:
            action_label = _("Import")
            if show_file_upload:
                title = _("Import New Tickets from CSV")
            elif show_preview:
                title = _("Import Preview")
            else:
                title = _('Imported Tickets')
        return (title, action_label)
    
    
    def _get_column_names(self, preview_rows):
        """Return a list of all keys found in preview_rows which is assumed to 
        be a list of dictionaries."""
        preview_colums = set()
        for row in preview_rows:
            for key in row:
                preview_colums.add(key)
        preview_colums = list(preview_colums)
        return preview_colums
    
    
    def _get_possible_encodings(self, encoding, encoding_guess):
        possible_encodings = set(['UTF-8', 'CP1252', 'ISO-8859-15'])
        if encoding not in possible_encodings:
            possible_encodings.add(encoding)
        if encoding_guess not in possible_encodings:
            possible_encodings.add(encoding_guess)
        possible_encodings = list(possible_encodings)
        possible_encodings.sort()
        return possible_encodings
    
    
    def _get_action_and_performer_from_request(self, req):
        action = None
        performer = None
        if ImportParameter.DO_DELETE in req.args:
            action = ImportParameter.DO_DELETE
            force = (ImportParameter.FORCE in req.args)
            performer = DeletePerformer(self.env, force=force)
        elif ImportParameter.DO_UPDATE in req.args:
            action = ImportParameter.DO_UPDATE
            performer = UpdatePerformer(self.env)
        else:
            performer = ImportPerformer(self.env)
            action = ImportParameter.DO_IMPORT
        return (action, performer)
    
    
    def _build_show_flags(self, req, performer, upload_fp):
        show_file_upload = False
        show_preview = not (ImportParameter.PERFORM_ACTION in req.args)
        if upload_fp == None:
            show_preview = False
            show_file_upload = True
        if show_preview:
            performer.set_preview_mode()
            show_file_upload = False
        return show_file_upload, show_preview
    
    
    def _update_template_data_for_preview(self, performer, upload_fp, data):
        preview_rows = performer.get_preview_rows()
        column_names = self._get_column_names(preview_rows)
        upload_fp.seek(0)
        # we have to encode the data as Genshi needs unicode strings but we
        # don't know the encoding.
        csv_data = base64.b64encode(upload_fp.read())
        data.update({"preview_rows": preview_rows, 
                     "preview_columns": column_names, "csv_data": csv_data})
    
    
    def _build_html_changelog(self, req, changed_tickets):
        html_changes = None
        if len(changed_tickets) > 0:
            ticket_changes = u''
            for ticket in changed_tickets:
                ticket_changes += u' * #%d %s\n' % (ticket.id, ticket[Key.SUMMARY])
            html_changes = wiki_to_html(ticket_changes, self.env, req)
        return html_changes
    
    
    def process_request(self, req):
        (action, performer) = self._get_action_and_performer_from_request(req)
        upload_fp = self._get_uploaded_file(req)
        encoding = req.args.get(ImportParameter.FILE_ENCODING, None)
        encoding_guess = self._guess_encoding(upload_fp)
        if encoding in [None, '']:
            encoding = encoding_guess
        show_file_upload, show_preview = self._build_show_flags(req, performer, upload_fp)
        
        r = (False, [])
        if upload_fp != None:
            r = self.process_file(req, upload_fp, performer, encoding=encoding)
        (encoding_errors_present, changed_tickets) = r
        
        title, action_label = \
            self._get_page_title_and_action_label(action, show_file_upload, show_preview)
        possible_encodings = self._get_possible_encodings(encoding, encoding_guess)
        html_changes = self._build_html_changelog(req, changed_tickets)
        
        data = dict(action=action, title=title, action_label=action_label,
                    show_file_upload=show_file_upload, show_preview=show_preview,
                    file_encoding=encoding, encoding_guess=encoding_guess,
                    possible_encodings=possible_encodings,
                    encoding_errors_present=encoding_errors_present,
                    html_changes=html_changes)
        if show_preview:
            self._update_template_data_for_preview(performer, upload_fp, data)
        return IMPORT_TEMPLATE, data, None
    
    
    def process_file(self, req, upload_file, performer, encoding=None):
        errors_during_perform = True
        changed_tickets = []
        try:
            csv = CSVFile(upload_file, performer.name(), encoding)
            header = csv.get_headings()
            header_warning = performer.check_header(header)
            if (header == None) or header_warning:
                add_warning(req, header_warning)
            else:
                interesting_fieldnames = performer.interesting_fieldnames()
                csv.set_allowed_fields(interesting_fieldnames)
                (errors_during_perform, changed_tickets) = \
                    self.process_all_rows(req, csv, performer)
        except ValueError, e:
            msg = _(u"Error during import (please check that you did not upload a binary file):")
            add_warning(req, msg + (u" '%s'" % unicode(e)))
        return (errors_during_perform, changed_tickets)
    
    
    def process_all_rows(self, req, csvfile, performer):
        i = 2
        errors_during_perform = False
        msg_line_skipped = _('Line %d had errors, skipped')
        while True:
            try:
                row = csvfile.next()
            except StopIteration:
                break
            except Exception, e:
                errors_during_perform = True
                add_warning(req, msg_line_skipped % i)
                error(self, _("Error while processing CSV line %d: %s")  % (i, e))
            else:
                performer.process(row)
            i += 1
        changed_tickets = []
        if not errors_during_perform:
            changed_tickets = performer.commit(req)
        return (errors_during_perform, changed_tickets)
    
    
