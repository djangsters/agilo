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

from trac.tests.functional import tc

from agilo.utils import Key, Status

from agilo.test import Usernames
from agilo.ticket.functional_tests.json_functional_testcase import JSONFunctionalTestCase


class CanCreateNewTaskWithJSON(JSONFunctionalTestCase):
    
    def runTest(self):
        self.json_tester.login_as(Usernames.team_member)
        
        summary = 'My JSON Task'
        ticket = self.json_tester.create_task(summary=summary, remaining_time=12)
        
        self.assertEqual(summary, ticket.summary)
        self.assertEqual('', ticket.description)
        self.assertEqual('12', ticket.remaining_time)
        self.assertEqual(Usernames.team_member, ticket.reporter)
        self.assertEqual(Status.NEW, ticket.status)
        
        ticket_page = self.tester.navigate_to_ticket_page(ticket.id)
        self.assertEqual(summary, ticket_page.summary())
        self.assertEqual('12.0h', ticket_page.remaining_time())


class CanNotCreateNewTicketWithoutType(JSONFunctionalTestCase):
    
    def runTest(self):
        self.json_tester.login_as(Usernames.admin)
        
        parameters = {Key.SUMMARY: 'Foo', Key.REMAINING_TIME: 12}
        json = self.assert_json_error(self.json_tester.server.json.tickets.put, **parameters)
        self.assertEqual(['Must specify a type.'], json.errors)
        self.json_tester.server.json.tickets.put(type='task', **parameters)


if __name__ == '__main__':
    from agilo.test import run_all_tests
    run_all_tests(__file__)

