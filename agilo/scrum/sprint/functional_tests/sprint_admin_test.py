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

from datetime import timedelta
from urllib import quote

from trac.util.datefmt import format_datetime
from trac.tests.functional import tc

from agilo.utils.days_time import normalize_date, now

from agilo.test import Usernames
from agilo.test.functional import AgiloFunctionalTestCase


class TestAdminSprints(AgiloFunctionalTestCase):
    
    def runTest(self):
        self._tester.login_as(Usernames.admin)
        # Create the milestone first
        self._tester.create_milestone('milestone2')
        
        # get sprint listing, should be empty
        page_url = self._tester.url + '/admin/agilo/sprints'
        tc.go(page_url)
        tc.url(page_url)
        tc.code(200)
        
        # add new sprint
        sprint_start = normalize_date(now())
        sprint_name = 'Test sprint'
        tc.formvalue('addsprint', 'name', sprint_name)
        tc.formvalue('addsprint', 'start', format_datetime(sprint_start, format='iso8601'))
        tc.formvalue('addsprint', 'duration', '1')
        tc.formvalue('addsprint', 'milestone', 'milestone2')
        tc.submit('add')
        # add redirects to list view, new sprint should be in there
        tc.find(sprint_name)
        # go to detail page
        tc.go("%s/%s" % (page_url, quote(sprint_name)))
        # see if milestone is set correctly
        tc.find('<option selected="selected">\s*milestone2')
        
        # test setting end date, not duration
        tc.formvalue('modcomp', 'description', '[http://www.example.com]')
        tomorrow = sprint_start + timedelta(days=1)
        tc.formvalue('modcomp', 'end', format_datetime(tomorrow, format='iso8601'))
        tc.formvalue('modcomp', 'duration', '')
        tc.submit('save')
        tc.url(page_url)
        
        # duration of the new sprint should be 2
        tc.find('"duration">2</td>')
        
        # --- test invalid values when adding sprint ---
        # no values, should redirect to list view
        tc.formvalue('addsprint', 'name', '')
        tc.submit('add')
        tc.url(page_url)
        
        # invalid date, should throw an error
        tc.formvalue('addsprint', 'name', 'Testsprint 2')
        tc.formvalue('addsprint', 'start', '2008 May 13')
        tc.formvalue('addsprint', 'duration', '1')
        tc.submit('add')
        tc.find('Error: Invalid Date')
        
        # no end date or duration
        tc.go(page_url)
        tc.formvalue('addsprint', 'name', 'Testsprint 2')
        yesterday = now() - timedelta(days=3)
        tc.formvalue('addsprint', 'start', 
                     format_datetime(yesterday, format='iso8601'))
        tc.submit('add')
        tc.url(page_url)


if __name__ == '__main__':
    from agilo.test.testfinder import run_all_tests
    run_all_tests(__file__)

