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

from trac.tests.functional import tc

from agilo.test import Usernames
from agilo.test.functional import AgiloFunctionalTestCase


class TestCanDeleteMilestone(AgiloFunctionalTestCase):
    """Test that a TRAC_ADMIN can delete a milestone with some tickets 
    (see bug #872)"""
    
    def setUp(self):
        super(TestCanDeleteMilestone, self).setUp()
        self.tester.login_as(Usernames.admin)
        self.tester.create_milestone(self.milestone_name())
        self.tester.create_new_agilo_requirement('Some requirement', milestone=self.milestone_name())
    
    def runTest(self):
        tc.go(self.tester.url + '/admin/ticket/milestones')
        tc.formvalue('milestone_table', 'sel', self.milestone_name())
        tc.submit('remove')
        tc.code(200)


if __name__ == '__main__':
    from agilo.test.testfinder import run_all_tests
    run_all_tests(__file__)

