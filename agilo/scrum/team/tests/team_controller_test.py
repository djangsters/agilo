# -*- encoding: utf-8 -*-
#   Copyright 2008 Agile42 GmbH, Berlin (Germany)
#   Copyright 2007 Andrea Tomasini <andrea.tomasini__at__agile42.com>
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
#       - Felix Schwarz <felix.schwarz__at__agile42.com>

from datetime import datetime, timedelta

from trac.util.datefmt import utc

from agilo.api import ValueObject
from agilo.scrum.team import TeamController
from agilo.scrum.contingent import ContingentController
from agilo.test import AgiloTestCase
from agilo.utils import Type, Key
from agilo.utils.config import AgiloConfig
from agilo.utils.days_time import now


class TeamControllerTest(AgiloTestCase):
    """Tests the TeamController and all the Commands in it"""
    def setUp(self):
        """initalize and environment, and a controller instance"""
        self.super()
        self.controller = TeamController(self.teh.get_env())
        self.sprint = self.teh.create_sprint('TestSprint', team='A-Team')
        self.s1 = self.teh.create_ticket(Type.USER_STORY, 
                                         props={Key.STORY_POINTS: '13',
                                                Key.SPRINT: 'TestSprint'})
        self.s2 = self.teh.create_ticket(Type.USER_STORY, 
                                         props={Key.STORY_POINTS: '13',
                                                Key.SPRINT: 'TestSprint'})
        self.s3 = self.teh.create_ticket(Type.USER_STORY, 
                                         props={Key.STORY_POINTS: '13',
                                                Key.SPRINT: 'TestSprint',
                                                Key.STATUS: 'closed'})
        
    def testCalculateVelocityCommand(self):
        """Tests the calculate velocity command"""
        cmd_calc_velocity = TeamController.CalculateTeamVelocityCommand(self.env,
                                                                        sprint=self.sprint)
        velocity = self.controller.process_command(cmd_calc_velocity)
        # Now velocity is the actual, so should be 13 only the closed story
        self.assert_equals(13, velocity)
        # Now check the estimated velocity, setting estimated to true in the command
        cmd_calc_velocity.estimated = True
        est_velocity = self.controller.process_command(cmd_calc_velocity)
        self.assert_equals(39, est_velocity)
    
    def testStoreAndRetriveVelocityCommands(self):
        """Tests the store and retrive of the team velocity from the metrics"""
        self.assert_equals('A-Team', self.sprint.team.name)
        cmd_store_velocity = TeamController.StoreTeamVelocityCommand(self.env,
                                                                     sprint=self.sprint)
        velocity = self.controller.process_command(cmd_store_velocity)
        self.assert_equals(13, velocity)
        # now check if it has been stored
        cmd_get_velocity = TeamController.GetStoredTeamVelocityCommand(self.env,
                                                                       sprint=self.sprint)
        metrics_velocity = self.controller.process_command(cmd_get_velocity)
        self.assert_equals(velocity, metrics_velocity)
        # now the estimated
        cmd_store_velocity.estimated = True
        cmd_get_velocity.estimated = True
        est_velocity = self.controller.process_command(cmd_store_velocity)
        self.assert_equals(39, est_velocity)
        metrics_est_velocity = self.controller.process_command(cmd_get_velocity)
        self.assert_equals(est_velocity, metrics_est_velocity)
    
    def test_summed_capacity_for_team_command_returns_zero_array_if_no_capacity_is_there(self):
        """Tests the calculation of the Daily capacity of a team for a Sprint"""
        cmd_daily_capacity = TeamController.CalculateSummedCapacityCommand(self.env, sprint=self.sprint)
        capacity = self.controller.process_command(cmd_daily_capacity)
        self.assert_equals(0, capacity)
    
    def test_can_sum_capacity_for_team(self):
        self.sprints_can_start_and_end_anytime()
        self.sprint.start = datetime(2009, 8, 1, 00, 00, tzinfo=utc)
        self.sprint.end = datetime(2009, 8, 10, 23, 59, tzinfo=utc)
        self.sprint.save()
        self.teh.create_member('Foo', self.sprint.team)
        
        cmd_daily_capacity = TeamController.CalculateSummedCapacityCommand(self.env, sprint=self.sprint, team=self.sprint.team)
        capacity_per_day = self.controller.process_command(cmd_daily_capacity)
        self.assert_almost_equals(36, capacity_per_day, max_delta=.01)
    
    def test_can_subtract_contingents_from_team_capacity(self):
        self.sprints_can_start_and_end_anytime()
        self.sprint.start = datetime(2009, 8, 1, 00, 00, tzinfo=utc)
        self.sprint.end = datetime(2009, 8, 10, 23, 59, tzinfo=utc)
        self.sprint.save()
        self.teh.create_member('Foo', self.sprint.team)
        self.teh.add_contingent_to_sprint('Bar', 12, self.sprint)
        
        cmd_daily_capacity = TeamController.CalculateSummedCapacityCommand(self.env, sprint=self.sprint, team=self.sprint.team)
        capacity_per_day = self.controller.process_command(cmd_daily_capacity)
        self.assert_almost_equals(36 - 12, capacity_per_day, max_delta=.01)
    
    def sprints_can_start_and_end_anytime(self):
        config = AgiloConfig(self.env)
        config.change_option('sprints_can_start_or_end_on_weekends', True, section='agilo-general')
        config.save()
        
    def testGetTeamCommandReturnsMembersAsDict(self):
        team = self.teh.create_team('Testteam')
        self.teh.create_member('foo', team)
        cmd = TeamController.GetTeamCommand(self.env, team=team.name)
        value_team = TeamController(self.env).process_command(cmd)
        
        members = value_team.members
        self.assert_equals(1, len(members))
        self.assert_true(isinstance(members[0], ValueObject))
    
    def test_confirm_commitment_uses_current_remaining_time(self):
        self.sprint.start = now() - timedelta(hours=2)
        self.sprint.save()
        task_properties = {Key.REMAINING_TIME: '7', Key.SPRINT: self.sprint.name}
        self.teh.create_ticket(Type.TASK, props=task_properties)
        
        commitment = TeamController.confirm_commitment_for_sprint(self.env, self.sprint)
        self.assert_equals(7, commitment)
    
    def allowZeroDotFiveStoryPoints(self):
        AgiloConfig(self.env).change_option('rd_points.options', '|0|0.5|1|2|3|5|8|13|20|40|100', section='ticket-custom')
    
    def test_confirm_commitment_can_cope_with_float_story_points(self):
        self.allowZeroDotFiveStoryPoints()
        self.s1[Key.STORY_POINTS] = '0.5'
        self.s1.save_changes('', '')
        TeamController.confirm_commitment_for_sprint(self.env, self.sprint)
    
    def test_store_team_velocity_can_cope_with_float_story_points(self):
        self.allowZeroDotFiveStoryPoints()
        self.s1[Key.STORY_POINTS] = '0.5'
        self.s1.save_changes('', '')
        TeamController.store_team_velocity(self.env, self.sprint, True)
    


if __name__ == '__main__':
    from agilo.test.testfinder import run_unit_tests
    run_unit_tests(__file__)
