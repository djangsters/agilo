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
#       - Martin Häcker <martin.haecker__at__agile42.com>

import agilo.utils.filterwarnings

from agilo.utils import Role
from agilo.test import Usernames
from agilo.test.functional import AgiloFunctionalTestCase

class NewTeamMembersGetTeamMemberRightsTest(AgiloFunctionalTestCase):
    
    def runTest(self):
        self._tester.login_as(Usernames.admin)
        team_name = self.team_name()
        member_name = self.first_team_member_name()
        self.tester.create_new_team(team_name)
        self.tester.add_member_to_team(team_name, member_name)
        member_permissions = self.tester.get_privileges_for_user(member_name)
        self.assertTrue(Role.TEAM_MEMBER in member_permissions)


if __name__ == '__main__':
    from agilo.test.testfinder import run_all_tests
    run_all_tests(__file__)

