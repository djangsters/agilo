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
from agilo.test.test_env_helper import TestEnvHelper


class CanUpdateExistingTicketTest(JSONFunctionalTestCase):
    
    def runTest(self):
        self.tester.login_as(Usernames.team_member)
        task_id = self.tester.create_new_agilo_task('My first task')
        
        self.json_tester.login_as(Usernames.team_member)
        new_summary = 'Foo Sum'
        new_task_attributes = {Key.SUMMARY: new_summary, Key.REMAINING_TIME: 42}
        json = self.json_tester.edit_ticket(task_id, **new_task_attributes)
        
        self.assertEqual(new_summary, json.summary)
        self.assertEqual('42', getattr(json, Key.REMAINING_TIME))
        
        page = self.tester.navigate_to_ticket_page(task_id)
        self.assert_equals(new_summary, page.summary())
        self.assert_equals('42.0h', page.remaining_time())


class IgnoreSimpleStatusIfNoStatusChangeIsRequiredTest(JSONFunctionalTestCase):
    # Do not update the status if not required. This saves us some time (trac
    # can only update a ticket once per second) and prevents useless changes
    # (e.g. from assigned -> accepted).
    
    def runTest(self):
        self.tester.login_as(Usernames.team_member)
        task_id = self.tester.create_new_agilo_task('My first task')
        self.ensure_min_one_second_passed()
        self.tester.close_ticket(task_id)
        self.ensure_min_one_second_passed()
        self.tester.reopen_ticket(task_id)
        self.ensure_min_one_second_passed()
        
        self.json_tester.login_as(Usernames.team_member)
        new_task_attributes = {Key.REMAINING_TIME: 5, 'simple_status': 'in_progress'}
        json = self.json_tester.edit_ticket(task_id, **new_task_attributes)
        # AT: extra test on the ticket object to verify that has been
        # modified correctly
        teh = TestEnvHelper(env=self.tester.env, env_key=self.env_key)
        task = teh.load_ticket(t_id=task_id)
        self.assert_equals('5', task[Key.REMAINING_TIME])
        # now check the JSON
        self.assertEqual('5', getattr(json, Key.REMAINING_TIME))
        ticket_page = self.tester.navigate_to_ticket_page(task_id)
        self.assertEqual('5.0h', ticket_page.remaining_time())


class CanChangeStatusAndTicketPropertiesAtTheSameTimeTest(JSONFunctionalTestCase):
    
    def runTest(self):
        self.tester.login_as(Usernames.team_member)
        task_id = self.tester.create_new_agilo_task('My first task')
        self.ensure_min_one_second_passed()
        
        self.json_tester.login_as(Usernames.team_member)
        new_task_attributes = {Key.REMAINING_TIME: 5, 'simple_status': 'in_progress'}
        json = self.json_tester.edit_ticket(task_id, **new_task_attributes)
        
        self.assertEqual('5', json[Key.REMAINING_TIME])
        self.assertNotEqual('new', json[Key.STATUS])
        
        ticket_page = self.tester.navigate_to_ticket_page(task_id)
        self.assertEqual('5.0h', ticket_page.remaining_time())
        self.assertNotEqual('new', ticket_page.status())


class ServerAddsWaitingTimeIfTicketCanNotBeSavedImmediatelyTest(JSONFunctionalTestCase):
    
    def runTest(self):
        self.tester.login_as(Usernames.team_member)
        task_id = self.tester.create_new_agilo_task('My first task')
        
        self.json_tester.login_as(Usernames.team_member)
        json = self.json_tester.edit_ticket(task_id, summary='Foo')
        self.assertEqual('Foo', json[Key.SUMMARY])
        
        json = self.json_tester.edit_ticket(task_id, summary='Bar')
        self.assertEqual('Bar', json[Key.SUMMARY])


if __name__ == '__main__':
    from agilo.test import run_all_tests
    run_all_tests(__file__)

