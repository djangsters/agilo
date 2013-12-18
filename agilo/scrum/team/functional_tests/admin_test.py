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

from urllib import quote

import agilo.utils.filterwarnings

from trac.util.text import unicode_quote
from trac.tests.functional import tc
from twill.errors import TwillAssertionError

from agilo.test import Usernames
from agilo.test.functional import AgiloFunctionalTestCase


class TestAdminTeam(AgiloFunctionalTestCase):
    
    def runTest(self):
        self._tester.login_as(Usernames.admin)
        page_url = self._tester.url + '/admin/agilo/teams'
        #TODO: find a way to test with umlaut without compromising the encoding
        team_name = self.classname() + 'Team'
        utf8_team_name = team_name.encode('UTF-8')
        team_desc = "'''Testdescription'''"
        self._tester.create_new_team(team_name)

        # set description
        tc.fv('modcomp', 'description', team_desc)
        tc.submit('save')
        
        # back at list view
        tc.url(page_url)
        tc.code(200)
        
        # add a new team and team member
        #TODO: find a way to test team names with umlaut without assuming the
        # locale of the testing system is UTF-8.de_DE
        member_name = self.classname() + 'Member'
        utf8_member_name = member_name.encode('UTF-8')
        member_desc = "Goldmember"

        team_name2 = "T-team"
        tc.fv('addteam', 'name', team_name2)
        tc.submit('add')
        tc.code(200)
        
        tc.fv('modcomp', 'team_member', utf8_member_name)
        tc.fv('modcomp', 'member_description', member_desc)
        tc.submit('add')
        tc.code(200)
        
        try:
            # IF the accountmanagerplugin is enabled has to appear 
            #       the Confirm user creation frame
            tc.find('Create new user')
        except TwillAssertionError:
            account_manager_plugin_enabled = False
        else:
            account_manager_plugin_enabled = True
            tc.fv('modcomp', 'createUser_ok', 'click')
            tc.submit('createUser_ok')
            tc.code(200)

        # correct team selected?
        tc.find('<option selected="selected">%s</option>' % team_name2)
        tc.find(utf8_member_name)
        tc.find(member_desc)
        
        # set new value for mondays and tuesdays
        tc.fv('modcomp', 'ts_0', '0')
        tc.fv('modcomp', 'ts_1', '')
        tc.submit('save')
        
        # back at team page
        tc.url("%s/%s" % (page_url, quote(team_name2)))
        tc.find(utf8_member_name)
        # three days x 6h
        tc.find('18.0h')
        
        user_not_confirmed = None
        if account_manager_plugin_enabled:
            # start to add a new user as team member but cancel at last
            user_not_confirmed = 'user-not-confirmed'
            tc.fv('modcomp', 'team_member', user_not_confirmed)
            tc.submit('add')
            # abort user creation
            tc.find('Create new user')
            tc.fv('modcomp', 'createUser_cancel', 'click')
            tc.submit('createUser_cancel')
        
        # back at team page
        tc.url("%s/%s" % (page_url, quote(team_name2)))
        tc.find(utf8_member_name)
        if user_not_confirmed is not None:
            tc.notfind(user_not_confirmed)
        
        # change team
        tc.follow(utf8_member_name)
        tc.fv('modcomp', 'team', utf8_team_name)
        tc.submit('save')
        tc.notfind(utf8_member_name)
        tc.go("%s/%s" % (page_url, unicode_quote(team_name)))
        tc.find(utf8_member_name)
        
        # --------- unassigned team members functionality --------
        # add another team member to team 1
        member_name2 = 'member #2'
        tc.fv('modcomp', 'team_member', member_name2)
        tc.submit('add')

        if account_manager_plugin_enabled:
            tc.find('Create new user')
            tc.find(member_name2)
            tc.fv('modcomp', 'createUser_ok', 'click')
            tc.submit('createUser_ok')

        tc.fv('modcomp', 'member_description', '')
        tc.submit('save')
        
        # back at team list, delete first team member
        tc.url("%s/%s" % (page_url, unicode_quote(team_name)))
        tc.fv('modcomp', 'delete', utf8_member_name)
        tc.submit('save')
        # same url, should not list this member anymore
        tc.url("%s/%s" % (page_url, unicode_quote(team_name)))
        tc.notfind(utf8_member_name)
        
        # select the other one but cancel back to team list. Formvalue
        # must use True here because Twill treats checkboxes differently
        # when there are several with the same name or only one
        tc.fv('modcomp', 'delete', True)
        tc.submit('cancel')
        tc.go(page_url)
        tc.follow('Unassigned team members')
        
        # shows the member we deleted, not the one we canceled on
        tc.url(page_url + "/unassigned")
        tc.find(utf8_member_name)
        tc.notfind(member_name2)
        
        # completely delete the team member
        tc.fv('modcomp', 'delete', True)
        tc.submit('remove')
        
        # no team members without teams anymore
        tc.url(page_url)
        tc.notfind('unassigned')
        
        # now delete the teams
        tc.fv('team_table', 'delete', utf8_team_name)
        tc.fv('team_table', 'delete', team_name2)
        tc.submit()
        
        tc.notfind(utf8_team_name)
        tc.notfind(team_name2)
        tc.find('unassigned')


if __name__ == '__main__':
    from agilo.test.testfinder import run_all_tests
    run_all_tests(__file__)

