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

import agilo.utils.filterwarnings

from agilo.test import Usernames
from agilo.test.functional import AgiloFunctionalTestCase

# TODO: hand the current test to the tester in setUp and remove it in tearDown 
# so we can make create_new_team and these methods will choose a sensible default 
# name 
class DoNotUseAccountManagerIfItIsNotEnabledTest(AgiloFunctionalTestCase):
    
    def setUp(self):
        self.super()
        self.restore_trac_login_module()
    
    def runTest(self):
        self.tester.login_as(Usernames.admin)
        team_name = self.classname() + 'Team'
        member_name = self.classname() + 'Member'
        self.tester.create_new_team(team_name)
        self.tester.add_member_to_team(team_name, member_name)


class DoNotCreateUserIfAccountManagerCanNotWritePasswordStoreTest(AgiloFunctionalTestCase):
    
    def enable_account_manager_with_httpauth_store(self):
        # AccountManager can not create users if used with HTTPAuth. For now
        # we just use trac's default HTTP AUTH on /login (not activating the
        # LoginModule for AccountManager)
        env = self.testenv.get_trac_environment()
        env.config.set('account-manager', 'authentication_url', self.tester.url + '/login')
        env.config.set('account-manager', 'password_store', 'HttpAuthStore')
        env.config.set('components', 'acct_mgr.api', 'enabled')
        env.config.set('components', 'acct_mgr.*', 'enabled')
        env.config.set('components', 'acct_mgr.http.HttpAuthStore', 'enabled')
        env.config.save()
    
    def setUp(self):
        self.super()
        self.remove_all_account_manager_components_from_config()
        self.enable_account_manager_with_httpauth_store()

    def runTest(self):
        self.tester.login_as(Usernames.admin)
        team_name = self.classname() + 'Team'
        member_name = self.classname() + 'Member'
        self.tester.create_new_team(team_name)
        self.tester.add_member_to_team(team_name, member_name)


if __name__ == '__main__':
    from agilo.test.testfinder import run_all_tests
    run_all_tests(__file__)

