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
#       - Andrea Tomasini <andrea.tomasini__at__agile42.com>

from trac.tests.functional import tc

from agilo.test import Usernames
from agilo.test.functional import AgiloFunctionalTestCase
from trac.util.text import unicode_quote


class TestRenameMilestoneAndSprint(AgiloFunctionalTestCase):
    """Test that when renaming a Milestone the related Sprints are updated
    (see bug #926)"""
    
    def setUp(self):
        self.super()
        self.tester.login_as(Usernames.admin)
        self.tester.create_milestone(self.milestone_name())
        self.tkt_id = self.tester.create_new_agilo_requirement('Some requirement', 
                                                               milestone=self.milestone_name())
        self.tester.create_sprint_for_milestone(self.milestone_name(), 
                                                "SprintFor" + self.milestone_name())
        
    def runTest(self):
        tc.go(self.tester.url + '/admin/ticket/milestones/' + unicode_quote(self.milestone_name()))
        new_name = self.milestone_name() + 'Renamed'
        tc.formvalue('modifymilestone', 'name', new_name)
        tc.submit('save')
        tc.code(200)
        # Now we expect that the ticket and the sprint have updated milestone
        ticket_page = self.tester.navigate_to_ticket_page(self.tkt_id)
        self.assert_equals(new_name, ticket_page.milestone())
        self.tester.go_to_sprint_edit_page("SprintFor" + self.milestone_name())
        tc.find('for milestone %s</h1>' % new_name)


if __name__ == '__main__':
    from agilo.test.testfinder import run_all_tests
    run_all_tests(__file__)

