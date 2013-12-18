# -*- coding: utf8 -*-
#   Copyright 2009 Agile42 GmbH, Berlin (Germany)
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
#   Authors:
#        - Felix Schwarz <felix.schwarz__at__agile42.com>
#        - Martin Häcker <martin.haecker__at__agile42.com>

from agilo.utils import Key

from agilo.test import Usernames
from agilo.ticket.functional_tests.json_functional_testcase import JSONFunctionalTestCase

from trac.tests.functional import tc


class ReturnCurrentDataAndErrorsInCaseOfFailure(JSONFunctionalTestCase):
    
    def runTest(self):
        self.tester.login_as(Usernames.admin)
        req_id = self.tester.create_new_agilo_requirement('My first req')
        
        new_summary = 'Super-duper Summary text'
        new_attributes = {Key.SUMMARY: new_summary}
        json = self.assert_json_error(self.json_tester.edit_ticket, req_id, **new_attributes)
        self.assertEqual(['No permission to change ticket fields.'], json.errors)
        self.assertTrue('current_data' in json)
        self.assertEqual('My first req', json.current_data['summary'])
        
        self.tester.go_to_view_ticket_page(req_id)
        tc.notfind(new_summary)


if __name__ == '__main__':
    from agilo.test import run_all_tests
    run_all_tests(__file__)

