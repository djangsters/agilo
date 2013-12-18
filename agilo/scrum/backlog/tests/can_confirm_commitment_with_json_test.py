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

from datetime import datetime, timedelta

from agilo.scrum.sprint.model import SprintModelManager
from agilo.scrum.backlog.json_ui import ConfirmCommitmentJSONView
from agilo.scrum.team import TeamController
from agilo.scrum.burndown.model import BurndownDataAggregator
from agilo.scrum.backlog.model import BacklogModelManager
from agilo.test import JSONAgiloTestCase, Usernames
from agilo.utils import Key, Action, Role
from agilo.utils.days_time import now

from trac.perm import PermissionError


class CanConfirmCommitmentWithJSONTest(JSONAgiloTestCase):
    def setUp(self):
        self.super()
        self.teh.disable_sprint_date_normalization()
        self._create_sprint_with_team_and_small_backlog()
        self.teh.grant_permission(self.username(), Action.CONFIRM_COMMITMENT)
        self.smm = SprintModelManager(self.env)
    
    def _create_sprint_with_team_and_small_backlog(self, sprint_name=None, team=None):
        if team is None:
            self.team = self.teh.create_team(name=self.team_name())
            self.teh.create_member(Usernames.team_member, self.team_name())
        else:
            self.team = team
        self.sprint = self.teh.create_sprint(sprint_name or self.sprint_name(),
                                             team=self.team,
                                             duration=14,
                                             start=datetime.now() - timedelta(hours=2))
        self._create_tasks()
        
    def _create_tasks(self):
        self.teh.create_task(sprint=self.sprint.name, remaining_time=13)
        self.teh.create_story(sprint=self.sprint.name, rd_points=10)
    
    # --------------------------------------------------------------------------
    # helper methods
    
    def username(self):
        return 'Login User'
    
    def team_name(self):
        return 'Fnord Team'
    
    def _commitment(self, sprint, team):
        cmd = TeamController.GetTeamCommitmentCommand(self.env, sprint=sprint, team=team)
        commitment = TeamController(self.env).process_command(cmd)
        return commitment
    
    def _metric(self, sprint, team, metric):
        cmd = TeamController.GetTeamMetricCommand(self.env, sprint=sprint, team=team, metric=metric)
        result = TeamController(self.env).process_command(cmd)
        return result
    
    def _capacity(self, sprint, team):
        return self._metric(sprint, team, Key.CAPACITY)
    
    def _velocity(self, sprint, team):
        return self._metric(sprint, team, Key.ESTIMATED_VELOCITY)
    
    def _confirm_commitment(self, sprint=None, req=None):
        if req is None:
            req = self.teh.mock_request(self.username())
        sprint_name = sprint and sprint.name or self.sprint.name
        args = dict(sprint=sprint_name)
        return ConfirmCommitmentJSONView(self.env).do_post(req, args)
    
    # --------------------------------------------------------------------------
    # tests
    
    def test_stores_team_commitment_in_metrics(self):
        self.assert_none(self._commitment(self.sprint, self.team))
        self._confirm_commitment()
        self.assert_equals(13, self._commitment(self.sprint, self.team))
    
    def test_stores_team_velocity_in_metrics(self):
        self.assert_none(self._velocity(self.sprint, self.team))
        self._confirm_commitment()
        self.assert_equals(10, self._velocity(self.sprint, self.team))
    
    def test_stores_team_capacity_in_metrics(self):
        # Sprint must start at the same time (or before) the team members
        # start working or not all of his capacity will be in the sprint
        self.sprint.start = self.sprint.start.replace(hour=9, minute=0, second=0, microsecond=0,
                                                      tzinfo=self.team.members[0].timezone())
        self.sprint.save()
        SprintModelManager(self.env).get_cache().invalidate()
        self.assert_none(self._capacity(self.sprint, self.team))
        self._confirm_commitment()
        self.assert_almost_equals(10*6, self._capacity(self.sprint, self.team), max_delta=0.01)
    
    def test_stores_historic_data_change(self):
        self.teh.create_task(sprint=self.sprint.name, remaining_time=8)
        aggregator = BurndownDataAggregator(self.env)
        changes = aggregator.changes_for_sprint(self.sprint)
        self.assert_length(2, changes)
        self._confirm_commitment()
        changes = aggregator.changes_for_sprint(self.sprint)
        self.assert_length(1, changes)
    
    def test_cannot_confirm_without_permission(self):
        req = self.teh.mock_request(username=Usernames.product_owner)
        
        self.assert_raises(PermissionError, lambda: self._confirm_commitment(req=req))
    
    def test_scrum_master_can_commit(self):
        self.teh.grant_permission(Usernames.scrum_master, Role.SCRUM_MASTER)
        
        req = self.teh.mock_request(username=Usernames.scrum_master)
        self._confirm_commitment(req=req)
        self.assert_equals(13, self._commitment(self.sprint, self.team))
    
    def _invalidate_backlog_cache(self):
        BacklogModelManager(self.env).get_cache().invalidate()
    
    def test_second_commit_updates_the_first(self):
        self.assert_none(self._commitment(self.sprint, self.team))
        self._confirm_commitment()
        self.assert_equals(13, self._commitment(self.sprint, self.team))
        
        self.teh.create_task(sprint=self.sprint.name, remaining_time=8)
        self._invalidate_backlog_cache()
        self._confirm_commitment()
        self.assert_equals(21, self._commitment(self.sprint, self.team))
        
        aggregator = BurndownDataAggregator(self.env)
        changes = aggregator.changes_for_sprint(self.sprint)
        self.assert_length(1, changes)
    
    def test_can_only_commit_for_one_day(self):
        self.sprint.start = now() - timedelta(days=2)
        self.smm.save(self.sprint)
        self.assert_raises(PermissionError, self._confirm_commitment)
    
    def test_does_not_fail_with_team_without_members(self):
        team = self.teh.create_team(name='test_does_not_fail_with_team_without_membersTeam')
        self._create_sprint_with_team_and_small_backlog('test_does_not_fail_with_team_without_membersSprint', team)
        self.assert_length(0, self.team.members)
        
        self._confirm_commitment()
        self.assert_equals(0, self._capacity(self.sprint, self.team))
    
    def test_does_not_explode_with_no_team(self):
        sprint_without_team = self.teh.create_sprint('Fnord')
        
        self.assert_raises(PermissionError, lambda: self._confirm_commitment(sprint=sprint_without_team))
    
    def test_does_not_fail_with_unknown_sprint(self):
        req = self.teh.mock_request(username=self.username())
        json_view = ConfirmCommitmentJSONView(self.env)
        self.assert_method_returns_error_with_empty_data(json_view.do_post, req, dict(sprint='Missing Fnord'))
    

