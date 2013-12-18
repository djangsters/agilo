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

from trac.perm import PermissionSystem
from trac.test import Mock, MockPerm

from agilo.api import ValueObject
from agilo.utils import Role
from agilo.test import AgiloTestCase
from agilo.scrum.team.admin import TeamAdminPanel

class TeamAdminTest(AgiloTestCase):
    
    def test_new_team_members_get_teammember_permissions(self):
        req = Mock(authname='admin', perm=MockPerm())
        new_member_name = 'fnord'
        
        admin_panel = TeamAdminPanel(self.env)
        team_member = ValueObject(dict(name=new_member_name))
        admin_panel.create_user_and_grant_permissions(req, team_member)
        
        permission_system = PermissionSystem(self.env)
        permissions = permission_system.get_user_permissions(new_member_name)
        self.assert_true(Role.TEAM_MEMBER in permissions)
        self.assert_true(permissions[Role.TEAM_MEMBER])

