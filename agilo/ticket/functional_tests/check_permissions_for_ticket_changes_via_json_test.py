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

from agilo.utils import Key, Type
import agilo.utils.filterwarnings

from agilo.test import Usernames
from agilo.ticket.functional_tests.json_functional_testcase import JSONFunctionalTestCase


class DontCreateTicketsIfNotEnoughPermissions(JSONFunctionalTestCase):
    
    def runTest(self):
        self.json_tester.login_as(Usernames.product_owner)
        
        new_summary = 'Super-duper Summary text'
        attributes = {Key.SUMMARY: new_summary, Key.TYPE: Type.USER_STORY}
        json = self.assert_json_error(self.json_tester.create_task, **attributes)
        self.assertEqual(['No permission to create or edit a task.'], json.errors)


class DontUpdateTicketFieldsIfNotEnoughPermissions(JSONFunctionalTestCase):
    
    def runTest(self):
        self.tester.login_as(Usernames.product_owner)
        req_id = self.tester.create_new_agilo_requirement('My Requirement')
        
        self.json_tester.login_as(Usernames.team_member)
        json = self.assert_json_error(self.json_tester.edit_ticket, req_id, 
                                      description='Spam!')
        self.assertEqual(1, len(json.errors))
        self.assertTrue(json.errors[0].startswith('No permission to '))
        self.assertEqual(req_id, json.current_data['id'], 'needs to include the ticket data')


class DontUpdateTicketStatusIfNotEnoughPermissions(JSONFunctionalTestCase):
    
    def runTest(self):
        self.tester.login_as(Usernames.team_member)
        task_id = self.tester.create_new_agilo_task('This is a requirement')
        
        self.json_tester.login_as(Usernames.product_owner)
        json = self.assert_json_error(self.json_tester.edit_ticket, task_id, 
                                      simple_status='in_progress')
        self.assertEqual(1, len(json.errors))
        self.assertTrue('privileges are required to perform this operation on' in json.errors[0])


if __name__ == '__main__':
    from agilo.test import run_all_tests
    run_all_tests(__file__)

