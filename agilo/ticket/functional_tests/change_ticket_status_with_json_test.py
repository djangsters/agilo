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

import agilo.utils.filterwarnings

from agilo.api import ValueObject
from agilo.utils import Status
from agilo.utils.compat import json, exception_to_unicode

from agilo.test import Usernames
from agilo.utils.json_client import GenericHTTPException
from agilo.ticket.functional_tests.json_functional_testcase import JSONFunctionalTestCase


# REFACT: try to rework these tests to unittests as they are much much faster to execute

class CanOverrideTicketWorkflow(JSONFunctionalTestCase):
    
    def runTest(self):
        self.tester.login_as(Usernames.team_member)
        task_id = self.tester.create_new_agilo_task('My first task')
        self.tester.accept_ticket(task_id)
        self.store_time()
        
        self.json_tester.login_as(Usernames.team_member)
        self.ensure_min_one_second_passed()
        json = self.json_tester.edit_ticket(task_id, simple_status='new')
        self.assertEqual(Status.NEW, json.status)
        self.assertEqual('', json.owner)
        task_owner = self.tester.get_owner_of_ticket(task_id)
        self.assertEqual('', task_owner)


class CatchRuleValidationExceptionOnStatusChangeByNonTeamMember(JSONFunctionalTestCase):
    
    def setUp(self, *args, **kwargs):
        super(CatchRuleValidationExceptionOnStatusChangeByNonTeamMember, self).setUp(*args, **kwargs)
        sprint_name = self.create_sprint_with_team()
        self.tester.login_as(Usernames.admin)
        self.task_id = self.tester.create_new_agilo_task('My first task', sprint=sprint_name)
        self.store_time()
    
    def runTest(self):
        # User "TeamMember" is not part of the team. This is why the test fails
        self.json_tester.login_as(Usernames.team_member)
        
        self.ensure_min_one_second_passed()
        exception = self.assert_raises(GenericHTTPException, \
                                       lambda: self.json_tester.edit_ticket(self.task_id, simple_status='in_progress'))
        self.assert_contains("doesn't belong to the team", exception_to_unicode(exception))
        response_json = json.loads(exception.detail)
        self.assertEqual(1, len(response_json['errors']))
        ticket = ValueObject(response_json['current_data'])
        self.assertEqual(Status.NEW, ticket.status)
        self.assertEqual('', ticket.owner)
        task_owner = self.tester.get_owner_of_ticket(self.task_id)
        self.assertEqual('', task_owner)


class CanSetOwnerExplicitlyIfCurrentlyLoggedInUserIsNotPartOfTheTeamTest(JSONFunctionalTestCase):
    
    def setUp(self, *args, **kwargs):
        super(CanSetOwnerExplicitlyIfCurrentlyLoggedInUserIsNotPartOfTheTeamTest, self).setUp(*args, **kwargs)
        sprint_name = self.create_sprint_with_team()
        self.tester.login_as(Usernames.admin)
        self.task_id = self.tester.create_new_agilo_task('My first task', sprint=sprint_name)
        self.store_time()
    
    def runTest(self):
        self.json_tester.login_as(Usernames.scrum_master)
        self.ensure_min_one_second_passed()
        json = self.json_tester.edit_ticket(self.task_id, simple_status='in_progress', 
                                            owner=self.current_team_member_name())
        self.assertEqual(self.current_team_member_name(), json.owner)
        current_owner = self.tester.get_owner_of_ticket(self.task_id)
        self.assertEqual(self.current_team_member_name(), current_owner)


class DoNotChangeOwnerIfTicketHasAnOwnerAndOnlyStatusChangeNeededTest(JSONFunctionalTestCase):
    
    def setUp(self, *args, **kwargs):
        super(DoNotChangeOwnerIfTicketHasAnOwnerAndOnlyStatusChangeNeededTest, self).setUp(*args, **kwargs)
        sprint_name = self.create_sprint_with_team()
        self.tester.login_as(Usernames.admin)
        self.task_id = self.tester.create_new_agilo_task('My first task', sprint=sprint_name, 
                                                         owner=self.current_team_member_name())
        self.assertEqual(self.current_team_member_name(),
                         self.tester.get_owner_of_ticket(self.task_id))
        self.store_time()
    
    def runTest(self):
        self.json_tester.login_as(Usernames.scrum_master)
        self.ensure_min_one_second_passed()
        
        team_member = self.current_team_member_name()
        json = self.json_tester.edit_ticket(self.task_id, simple_status='in_progress', 
                                            owner=self.current_team_member_name())
        self.assertEqual(team_member, json.owner)
        current_owner = self.tester.get_owner_of_ticket(self.task_id)
        self.assertEqual(team_member, current_owner)


if __name__ == '__main__':
    from agilo.test import run_all_tests
    run_all_tests(__file__)

