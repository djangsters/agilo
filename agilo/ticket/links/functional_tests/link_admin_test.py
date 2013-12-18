# -*- encoding: utf-8 -*-
#   Copyright 2008 Agile42 GmbH, Berlin (Germany)
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

from trac.tests.functional import tc

from agilo.test import Usernames
from agilo.test.functional import AgiloFunctionalTestCase


class TestAdminLinks(AgiloFunctionalTestCase):

    def go_to_admin_links_page(self):
        page_url = self._tester.url + '/admin/agilo/links'
        tc.go(page_url)
        tc.url(page_url)
        tc.code(200)
        return page_url

    def create_link(self, source_type_alias, target_type_alias, source_type, target_type):
        # add new link
        # this form uses the aliased values
        tc.formvalue('addlink', 'source', source_type_alias)
        tc.formvalue('addlink', 'target', target_type_alias)
        tc.submit('add')
        tc.code(200)
        # save should redirect to edit page, see if it does
        tc.find('Modify %s-%s Link' % (source_type_alias, target_type_alias))
        # add new link
        tc.formvalue('modcomp', 'copy_fields', '+resolution')
        tc.submit('save')
        # redirects to list page, now new link should be found
        tc.find('%s-%s' % (source_type, target_type))

    def runTest(self):
        self._tester.login_as(Usernames.admin)

        page_url = self.go_to_admin_links_page()
        # see if one of the default links is there
        tc.find('story-task">Task</a>')
        
        # check if the alias module works correctly, reload the page
        tc.go(page_url)
        tc.find('story-task">Task</a>')

        self.create_link('Bug', 'Requirement', 'bug', 'requirement')


class TestAdminLinksWithDashesInTypeName(TestAdminLinks):

    def runTest(self):
        self.tester.login_as(Usernames.admin)
        custom_type = 'with-dashes'
        custom_type_alias = 'With-Dashes'
        self.tester.create_new_ticket_type(custom_type, alias=custom_type_alias)
        self.go_to_admin_links_page()
        self.create_link('Bug', custom_type_alias, 'bug', custom_type)
        self.go_to_admin_links_page()
        tc.find('bug-with-dashes">With-Dashes</a>')
        tc.find('bug-with-dashes">Bug</a>')



if __name__ == '__main__':
    from agilo.test.testfinder import run_all_tests
    run_all_tests(__file__)

