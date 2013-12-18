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

from trac.tests.functional import tc

from agilo.test import Usernames
from agilo.test.functional import AgiloFunctionalTestCase


class TestAdminBacklog(AgiloFunctionalTestCase):
    
    def _test_adding_a_backlog(self, page_url, backlog_name):
        tc.go(page_url)
        tc.url(page_url)
        tc.fv('addbacklog', 'name', backlog_name)
        tc.submit('add')
        # we're at the edit page
        backlog_url = page_url + '/' + backlog_name
        tc.url(backlog_url)
    
    def _test_ajax_update_fields(self):
        # test Ajax functionality by clicking "update fields" or 
        # passing the new values as a GET parameter
        tc.fv('modcomp', 'scope', 'milestone')
        tc.submit('preview')
        
        # see if the available and selected fields for this backlog 
        # type are display correctly
        tc.find('<option selected="selected" [^>]*>milestone</option>')
    
    def _test_backlog_deletion(self, backlog_name):
        # test deletion
        tc.formvalue('backlog_table', 'sel', '+' + backlog_name)
        tc.submit('remove')
        tc.notfind(backlog_name)
    
    def _test_create_new_type(self, page_url, backlog_name):
        # Creates a new type and check if it appears directly in the
        # backlog list of types
        tc.go(self._tester.url + '/admin/ticket/type')
        tc.formvalue('addenum', 'name', 'testtype')
        tc.submit('add')
        # Now go to Agilo Types and make it a type
        tc.go(self._tester.url + '/admin/agilo/types')
        tc.follow('testtype')
        tc.formvalue('modcomp', 'alias', 'Test Type')
        tc.formvalue('modcomp', 'fields', 'drp_resources')
        tc.submit('save')
        # Go to the Backlog and verify the newly created type is there
        tc.go(self._tester.url + '/admin/agilo/backlogs/' + \
              backlog_name)
        tc.find('<option value="testtype">')
        tc.go(self._tester.url + '/admin/agilo/backlogs/')

    def runTest(self):
        page_url = self._tester.url + '/admin/agilo/backlogs'
        backlog_name = "testbacklog"
        self._tester.login_as(Usernames.admin)
        self._test_adding_a_backlog(page_url, backlog_name)
        self._test_ajax_update_fields()
        self._test_create_new_type(page_url, backlog_name)
        self._test_backlog_deletion(backlog_name)


if __name__ == '__main__':
    from agilo.test.testfinder import run_all_tests
    run_all_tests(__file__)

