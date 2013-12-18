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

from datetime import timedelta

import agilo.utils.filterwarnings

from trac.tests.functional import tc
from trac.util.datefmt import parse_date

from agilo.scrum import TEAM_URL
from agilo.scrum.team import TeamModelManager, TeamMemberModelManager
from agilo.scrum.sprint import SprintModelManager
from agilo.test import Usernames
from agilo.test.functional import AgiloFunctionalTestCase
from agilo.utils.days_time import now


class TestTeamPages(AgiloFunctionalTestCase):
    
    def setUp(self):
        self.super()
        self.env = self._testenv.get_trac_environment()
        self.team = TeamModelManager(self.env).create(name="Team#1")
        tmm = TeamMemberModelManager(self.env)
        self.members = (tmm.create(name="Member#1", team=self.team),
                        tmm.create(name="Member#2", team=self.team,
                                         default_capacity=[4,4,4,0,0,0,0]),
                        tmm.create(name="Member#3", team=self.team,
                                         default_capacity=[0,0,0,2,2,0,0]))
        for m in self.members:
            m.save()



    def runTest(self):
        self._tester.login_as(Usernames.team_member)
        page_url = self._tester.url + TEAM_URL
        tc.go(page_url)
        tc.url(page_url)
        tc.code(200)
        tc.follow('Team#1')
        tc.code(200)
        tc.find('Member#1')


class TestViewingTheTeamPageRequiresPrivilege(AgiloFunctionalTestCase):
    """Test that the team page is not shown if the user does not have the
    TEAM_VIEW privilege."""
    
    def runTest(self):
        self._tester.login_as(Usernames.admin)
        self._tester.create_new_team('privilege_team')
        
        self._tester.login_as(Usernames.product_owner)
        teampage_url = self._tester.url + TEAM_URL
        tc.go(teampage_url)
        tc.code(200)
        
        self._tester.logout()
        tc.go(teampage_url)
        tc.code(403)
        
        self._tester.go_to_front()
        tc.notfind('href="%s"' % TEAM_URL)


class TestStoreCapacityPerDayForTeamMember(AgiloFunctionalTestCase):
    
    def runTest(self):
        team_name = 'team_for_capacity_saving'
        member_name = 'Team member_name'
        sprint_name = 'capacity_saving_sprint'
        
        self._tester.login_as(Usernames.admin)
        self._tester.create_new_team(team_name)
        self._tester.add_member_to_team(team_name, member_name)
        sprint_start = now()
        self._tester.create_sprint_via_admin(sprint_name, start=sprint_start, team=team_name)
        
        # having tasks with remaining time which were not assigned to a specific
        # user triggered another bug on the team page.
        attributes = dict(sprint=sprint_name, remaining_time='12')
        self._tester.create_new_agilo_task('Not assigned Task', **attributes)
        
        self._tester.login_as(Usernames.scrum_master)
        self._tester.go_to_team_page(team_name, sprint_name)
        team_page_url = tc.get_browser().get_url()
        
        day_ordinal = (sprint_start + timedelta(days=3)).toordinal()
        input_name = 'ts_%s_%d' % (member_name, day_ordinal)
        tc.formvalue('team_capacity_form', input_name, '2')
        tc.submit('save')
        tc.code(200)
        tc.url(team_page_url)


class TestStoreNoneCapacityPerDayForTeamMember(AgiloFunctionalTestCase):

    def runTest(self):
        team_name = 'team_for_capacity_saving'
        member_name = 'Team member_name'
        sprint_name = 'capacity_saving_sprint'

        self._tester.login_as(Usernames.admin)
        self._tester.create_new_team(team_name)
        self._tester.add_member_to_team(team_name, member_name)
        sprint_start = now()
        self._tester.create_sprint_via_admin(sprint_name, start=sprint_start, team=team_name)

        # having tasks with remaining time which were not assigned to a specific
        # user triggered another bug on the team page.
        attributes = dict(sprint=sprint_name, remaining_time='12')
        self._tester.create_new_agilo_task('Not assigned Task', **attributes)

        self._tester.login_as(Usernames.scrum_master)
        self._tester.go_to_team_page(team_name, sprint_name)
        team_page_url = tc.get_browser().get_url()

        day_ordinal = (sprint_start + timedelta(days=3)).toordinal()
        input_name = 'ts_%s_%d' % (member_name, day_ordinal)
        tc.formvalue('team_capacity_form', input_name, '\'\'')
        tc.submit('save')
        tc.code(200)
        tc.url(team_page_url)


if __name__ == '__main__':
    from agilo.test.testfinder import run_all_tests
    run_all_tests(__file__)

