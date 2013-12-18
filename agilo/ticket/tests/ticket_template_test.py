# -*- encoding: utf-8 -*-
#   Copyright 2010 Agile42 GmbH, Berlin (Germany)
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

import trac

from agilo.test import AgiloTestCase
from agilo.ticket.web_ui import AgiloTicketModule
from agilo.utils import Key, Type


class DisplayRenderedValuesFromTracIfAvailableTest(AgiloTestCase):
    
    def setUp(self):
        self.super()
        self.teh.create_field('wiki_field', 'text', format='wiki')
        self.teh.add_field_for_type('wiki_field', Type.TASK)
        self.task = self.teh.create_task(wiki_field='[/ Some weird link text]')
        self.assert_equals('[/ Some weird link text]', self.task['wiki_field'])
        self.req = self.teh.mock_request(username='foo', args={'id': self.task.id}, method='GET')
    
    def field_with_name(self, fields, name):
        for field in fields:
            if field[Key.NAME] == name:
                return field
        self.fail('No field with name %s' % repr(name))
    
    def field_for_template(self, field_name):
        template, data, content_type = AgiloTicketModule(self.env).process_request(self.req)
        fields = data['fields']
        return self.field_with_name(fields, field_name)
    
    def test_can_use_wiki_formatting_in_ticket_fields(self):
        trac_version = trac.__version__
        is_011 = (trac_version[:4] == '0.11')
        trac_minor_version = (len(trac_version) > 4) and int(trac.__version__[5]) or 0
        if is_011 and trac_minor_version < 3:
            # Support for wiki formatting was introduced in 0.11.3 (#1791)
            # we can't properly skip this test as we can't assume that the test
            # suite will run with nose exclusively
            return
        wiki_field = self.field_for_template('wiki_field')
        self.assert_contains('<a ', unicode(wiki_field[Key.RENDERED]))
    
    def test_still_displays_na_if_no_content_in_wiki_field(self):
        self.task['wiki_field'] = ''
        self.task.save_changes(None, None)
        
        wiki_field = self.field_for_template('wiki_field')
        self.assert_equals('n.a.', unicode(wiki_field[Key.RENDERED]))
    
    def test_still_displays_na_if_no_content_in_sprint_field(self):
        self.assert_contains(self.task[Key.SPRINT], (None, ''))
        
        sprint_field = self.field_for_template('sprint')
        self.assert_equals('n.a.', unicode(sprint_field[Key.RENDERED]))
    
    def test_displays_shortened_email_addresses_if_insufficient_permissions(self):
        self.teh.add_field_for_type('cc', Type.TASK)
        self.task['cc'] = 'foo.bar@example.com'
        self.task.save_changes(None, None)
        self.assert_not_contains('EMAIL_VIEW', self.req.perm)
        
        cc_field = self.field_for_template('cc')
        self.assert_equals(u'foo.bar@…', unicode(cc_field[Key.RENDERED]))

