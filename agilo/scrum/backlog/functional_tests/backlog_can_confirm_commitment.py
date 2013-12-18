# -*- encoding: utf-8 -*-
#   Copyright 2010 Agile42 GmbH, Berlin (Germany)
#   Copyright 2011 Agilo Software GmbH All rights reserved
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

import agilo.utils.filterwarnings
from datetime import timedelta

from agilo.test import Usernames
from agilo.test.functional import AgiloFunctionalTestCase
from agilo.test.functional.agilo_tester import TeamOverviewPageTester
from agilo.utils.constants import Key
from agilo.utils.days_time import now

class CanConfirmCommitment(AgiloFunctionalTestCase):
    testtype = 'windmill'
    
    def setUp(self):
        self.super()
        self.tester.login_as(Usernames.admin)
        self.tester.create_sprint_with_team('UncommitableSprint',
                                            start=now() - timedelta(days=3),
                                            team_name='UncommitableTeam')
        self.tester.create_sprint_with_team('CommitableSprint',
                                            team_name='CommitableTeam')
        self.tester.create_userstory_with_tasks(sprint_name='UncommitableSprint')
        self.tester.create_userstory_with_tasks(sprint_name='CommitableSprint')
    
    def runTest(self):
        self.windmill_tester.login_as(Usernames.scrum_master)
        self._test_cannot_commit_on_uncommitable_sprint()
        self._test_team_metrics_change_on_commit()
        self._test_burndown_reload_on_commit()
    
    def _test_cannot_commit_on_uncommitable_sprint(self):
        backlog = self.windmill_tester.go_to_new_sprint_backlog(sprint_name='UncommitableSprint')
        self.assert_false(backlog.can_click_confirm_commitment())
    
    def _test_team_metrics_change_on_commit(self):
        backlog = self.windmill_tester.go_to_new_sprint_backlog(sprint_name='CommitableSprint')
        self.assert_false(self._did_store_team_metrics(team_name='CommitableTeam', sprint_name='CommitableSprint'))
        self._click_confirm(backlog)
        self.assert_equals('', backlog.error_notice())
        self.assert_true(self._did_store_team_metrics(team_name='CommitableTeam', sprint_name='CommitableSprint'))
    
    def _did_store_team_metrics(self, team_name, sprint_name):
        team_page = TeamOverviewPageTester(self.tester, team_name).go()
        return  team_page.has_value_for_sprint(Key.COMMITMENT, sprint_name) \
            and team_page.has_value_for_sprint(Key.ESTIMATED_VELOCITY, sprint_name) \
            and team_page.has_value_for_sprint(Key.CAPACITY, sprint_name)
    
    def _test_burndown_reload_on_commit(self):
        backlog = self.windmill_tester.go_to_new_sprint_backlog(sprint_name='CommitableSprint')
        backlog.click_show_burndown_chart_toggle()
        self._click_confirm(backlog)
        self.windmill_tester.windmill.waits.forElement(xpath="//*[@id='chart-container']/*[@id='burndownchart']")
    
    def _click_confirm(self, backlog):
        backlog.click_confirm_commitment()
        self.windmill_tester.windmill.waits.forElement(xpath="//*[@id='message']")
