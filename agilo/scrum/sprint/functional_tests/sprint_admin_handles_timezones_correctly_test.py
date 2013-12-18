# -*- encoding: utf-8 -*-
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

from datetime import datetime, timedelta
from urllib import quote

from trac.util.datefmt import format_datetime, get_timezone, to_datetime, utc
from trac.tests.functional import tc

from agilo.utils.days_time import normalize_date

from agilo.test import Usernames
from agilo.test.functional import AgiloFunctionalTestCase
from agilo.scrum import SPRINT_URL


class SprintAdminHandlesTimezonesCorrectlyTest(AgiloFunctionalTestCase):
    
    def testname(self):
        return 'SprintAdminHandlesTimezonesCorrectlyTest'
    
    def go_to_sprint_detail_page(self, sprint_name):
        tc.go('%s/%s' % (SPRINT_URL, sprint_name))
        tc.code(200)
    
    def runTest(self):
        self._tester.login_as(Usernames.admin)
        milestone_name = \
            self._tester.create_milestone(self.testname() + 'Milestone')
        
        admin_tz = get_timezone('GMT +2:00')
        self._tester.set_timezone_for_current_user('GMT +2:00')
        start = datetime(2009, 07, 06, 8, 00, tzinfo=utc)
        sprint_name = self.testname() + 'Sprint'
        self._tester.create_sprint_via_admin(sprint_name, start=start, duration=5, 
                                   milestone=milestone_name, tz=admin_tz)
        
        self._tester.login_as(Usernames.team_member)
        bangkok_tz = get_timezone('GMT +7:00')
        self._tester.set_timezone_for_current_user(bangkok_tz.zone)
        self.go_to_sprint_detail_page()
        expected_datestring = format_datetime(start, tzinfo=bangkok_tz)
        tc.find('started the %s' % expected_datestring, flags='i')


if __name__ == '__main__':
    from agilo.test.testfinder import run_all_tests
    run_all_tests(__file__)

