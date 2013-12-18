# -*- coding: utf-8 -*-
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
#   Author: 
#       - Felix Schwarz <felix.schwarz__at__agile42.com>

import urllib2

from trac.perm import PermissionSystem
from trac.tests.functional import tc
from trac.util.datefmt import to_timestamp

from agilo.utils import Action, Key
from agilo.utils.compat import json
from agilo.test import Usernames
from agilo.test.functional import AgiloFunctionalTestCase


class NewTicketPageSavesCustomProperties(AgiloFunctionalTestCase):
    
    def runTest(self):
        self._tester.login_as(Usernames.product_owner)
        us_id = self._tester.create_new_agilo_userstory('This is a story', 
                                                        rd_points=5)
        page = self.tester.navigate_to_ticket_page(us_id)
        # now should find the points
        self.assertEqual(5, page.story_points())


class TicketPageInjectsCustomHeaderForTicketID(AgiloFunctionalTestCase):
    
    def setUp(self):
        super(TicketPageInjectsCustomHeaderForTicketID, self).setUp()
        self._grant_ticket_admin_to_anonymous()
    
    def tearDown(self):
        tracenv = self.testenv.get_trac_environment()
        PermissionSystem(tracenv).revoke_permission('anonymous', Action.TRAC_ADMIN)
        super(TicketPageInjectsCustomHeaderForTicketID, self).tearDown()
    
    def _grant_ticket_admin_to_anonymous(self):
        # twill does not allow us to access the response headers. Therefore we
        # need to utilize urllib2 directly which has the downside that we can
        # not access the ticket edit page by default.
        tracenv = self.testenv.get_trac_environment()
        PermissionSystem(tracenv).grant_permission('anonymous', Action.TRAC_ADMIN)
        # fs: Somehow we need to restart the tracd - otherwise tracd will not
        # 'see' the granted permissions even though I can verify with sqlite3
        # that they are really stored in the db...
        tracenv = self.testenv.get_trac_environment()
        tracenv.config.touch()
    
    def _response_headers_from_ticket_page(self, ticket_id, edit_page=False):
        url = self.tester.ticket_url(ticket_id, edit=edit_page)
        response = urllib2.urlopen(url)
        return response.headers
    
    def _ticket_id_from_header(self, task_id, edit_page=False):
        headers = self._response_headers_from_ticket_page(task_id, edit_page)
        return headers.getheader('X-Agilo-Ticket-ID')
    
    def _ticket_json_from_header(self, task_id):
        headers = self._response_headers_from_ticket_page(task_id)
        raw_json = headers.getheader('X-Agilo-Ticket-JSON')
        return json.loads(raw_json)
    
    def _verify_json_header(self, task_id):
        json_data = self._ticket_json_from_header(task_id)
        self.assertEqual(task_id, json_data[Key.ID])
        self.assertEqual('Foo', json_data[Key.SUMMARY])
    
    def runTest(self):
        self.tester.login_as(Usernames.team_member)
        task_id = self.tester.create_new_agilo_task('Foo')
        self.assertEqual(str(task_id), self._ticket_id_from_header(task_id))
        self.assertEqual(str(task_id), self._ticket_id_from_header(task_id, edit_page=True))
        self._verify_json_header(task_id)


class TicketModuleAcceptsAlsoTimestampsForLastChangedTimeTest(AgiloFunctionalTestCase):
    
    def runTest(self):
        self.tester.login_as(Usernames.team_member)
        task_id = self.tester.create_new_agilo_task('Foo')
        
        last_change = self.tester.get_time_of_last_change(task_id)
        from agilo.ticket import AgiloTicketSystem
        if AgiloTicketSystem.is_trac_1_0():
            self.tester.edit_ticket(task_id, summary='fnord', view_time='12')
        else:
            self.tester.edit_ticket(task_id, summary='fnord', ts='12')
        tc.find('This ticket has been modified by someone else since you started')
        
        if AgiloTicketSystem.is_trac_1_0():
            self.tester.edit_ticket(task_id, summary='fnord', view_time=str(last_change))
        else:
            self.tester.edit_ticket(task_id, summary='fnord', ts=str(last_change))
        tc.notfind('This ticket has been modified by someone else since you started')
        tc.find('fnord')



if __name__ == '__main__':
    from agilo.test.testfinder import run_all_tests
    run_all_tests(__file__)

