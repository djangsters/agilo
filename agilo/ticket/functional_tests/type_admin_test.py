# -*- encoding: utf-8 -*-
#   Copyright 2008-2009 Agile42 GmbH, Berlin (Germany)
#   Copyright 2007 Andrea Tomasini <andrea.tomasini_at_agile42.com>
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
#   Author: 
#       - Jonas von Poser <jonas.vonposer__at__agile42.com>
#       - Felix Schwarz <felix.schwarz__at__agile42.com>

import re

from trac.tests.functional import tc

from agilo.test import Usernames
from agilo.test.functional import AgiloFunctionalTestCase
from agilo.utils import Key
from agilo.utils.config import AgiloConfig


class TestAdminTypes(AgiloFunctionalTestCase):
    
    def runTest(self):
        self._tester.login_as(Usernames.admin)
        # get page for editing requirement ticket type
        page_url = self._tester.url + '/admin/agilo/types/requirement'
        tc.go(page_url)
        tc.url(page_url)
        tc.code(200)
        tc.find('requirement')
        tc.find('Alias:')
        
        # test default field
        tc.find('name="fields" value="businessvalue" checked="checked"')
        
        # change alias and fields and save
        tc.formvalue('modcomp', 'fields', '+priority')
        tc.formvalue('modcomp', 'fields', '-businessvalue')
        tc.formvalue('modcomp', 'fields', '-milestone')
        tc.formvalue('modcomp', 'fields', '-keywords')
        tc.submit('save')
        
        # redirects to list page, now only the priority should be selected
        tc.find('<td class="fields">[\n ]*Priority<br />[\n ]*</td>')
        
        tc.go(page_url)
        # We must ensure that these fields are available for later tests.
        tc.formvalue('modcomp', 'fields', '+businessvalue')
        tc.formvalue('modcomp', 'fields', '+milestone')
        tc.submit('save')


class TestAdminCustomTypes(AgiloFunctionalTestCase):
    """Adds a new ticket type through Trac and checks if it appears
        in the Agilo type admin page. Catches bug #264 as well."""
        
    def runTest(self):
        self.tester.login_as(Usernames.admin)
        # It's important that the ticket type is not all lower-cased so we can
        # see if the properties are really loaded again.
        
        # test with normal type
        self.tester.create_new_ticket_type('my_type', alias='MyTypeAlias')
        
        # test with camel cased type
        self.tester.create_new_ticket_type('MyType', alias='MyTypeCamelAlias')
    

# class TestRemoveAdminCustomTypeAliasDeactivatesType(AgiloFunctionalTestCase):
#     "Should fix #916, #918"
#     
#     def runTest(self):
#         self.tester.login_as(Usernames.admin)
#         type_name = 'fnord'
#         type_alias = 'Fnord'
#         self.tester.create_new_ticket_type(type_name, alias=type_alias)
#         self.tester.set_ticket_type_alias(type_name, '')
#         
#         self.assert_false(self.has_create_type_link_in_sidebar(type_name, ''))
#         self.assert_false(self.has_create_type_link_in_sidebar(type_name, type_alias))
#         
#         self.assert_none(self.saved_alias_name_for_type(type_name))
#     
#     def has_create_type_link_in_sidebar(self, type_name, type_alias):
#         action_regex = r'<a href="/newticket\?type=%s">\s*New\s*%s\s*</a>' % (type_name, type_alias)
#         return re.search(action_regex, tc.show()) is not None
#     
#     def saved_alias_name_for_type(self, type_name):
#         config = AgiloConfig(self.env)
#         return config.get('%s.%s' % (type_name, Key.ALIAS), section=AgiloConfig.AGILO_TYPES)
#    


if __name__ == '__main__':
    from agilo.test.testfinder import run_all_tests
    run_all_tests(__file__)

