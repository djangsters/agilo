# -*- coding: utf-8 -*-
#   Copyright 2007-2008 Agile42 GmbH - Andrea Tomasini
#   Copyright 2011 Agilo Software GmbH All rights reserved 
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
# 
# Authors:
#     - Andrea Tomasini <andrea.tomasini__at__agile42.com>

from datetime import timedelta

from trac.util.datefmt import utc

from agilo.api import controller, validator
from agilo.scrum.team.model import TeamModelManager, TeamMemberModelManager
from agilo.utils import Key, Status, days_time
from agilo.utils.days_time import now

__all__ = ['TeamController']


class TeamController(controller.Controller):
    """Takes care of processing any command related to a Team"""
    
    def __init__(self):
        """
        Initialize the component, sets some references to needed
        Model Managers
        """
        self.tm_manager = TeamModelManager(self.env)
        self.tmm_manager = TeamMemberModelManager(self.env)
    
    class CalculateSummedCapacityCommand(controller.ICommand):
        """Returns the sum of the capacity of the team for the 
        whole sprint"""
        parameters = {'team': validator.TeamValidator, 
                      'sprint': validator.MandatorySprintValidator}
        
        def _execute(self, team_controller, date_converter=None, as_key=None):
            """Returns the team's capacity for every day of the given 
            sprint as list."""
            # If the team is still None try to get it from the sprint
            # or check that is the same as the sprint
            if not self.team:
                self.team = self.sprint.team
            elif self.sprint.team != self.team:
                raise self.CommandError("The given sprint (%s) is not assigned" \
                                        " to the given team (%s)!")
            
            if self.sprint.team is None:
                return []
            
            timed_capacities = self.sprint.team.capacity().hourly_capacities_in_sprint(self.sprint)
            return sum(map(lambda each: each.capacity, timed_capacities))
        
    
    class ListTeamsCommand(controller.ICommand):
        """Returns a list of teams matching the given criteria"""
        parameters = {'criteria': validator.DictValidator, 
                      'order_by': validator.IterableValidator, 
                      'limit': validator.IntValidator}
        
        def _execute(self, team_controller, date_converter=None,
                     as_key=None):
            """
            Execute the listing command, returns a list of sprints, if the
            set criteria is None, it returns all the sprints, otherwise only
            the sprints matching the criteria
            """
            criteria = getattr(self, 'criteria', None)
            order_by = getattr(self, 'order_by', None)
            limit = getattr(self, 'limit', None)
            teams = team_controller.tm_manager.select(criteria=criteria,
                                                      order_by=order_by,
                                                      limit=limit)
            return [self.return_as_value_object(t) for t in teams]
    
    
    class CalculateTeamVelocityCommand(controller.ICommand):
        """Calculates the team Velocity for a given sprint, can be
        estimated velocity or actual velocity."""
        parameters = {'sprint': validator.MandatorySprintValidator,
                      # Needed only if not in the Sprint
                      'team': validator.TeamValidator,
                      'estimated': validator.BoolValidator}
        
        def _execute(self, team_controller, date_converter=None,
                     as_key=None):
            """Runs the command, returns the result or raise a CommandError"""
            from agilo.ticket.model import AgiloTicketModelManager 
            ticket_manager = AgiloTicketModelManager(team_controller.env)
            # ask to agilo config which types have the story points
            # attribute
            from agilo.utils.config import AgiloConfig
            ac = AgiloConfig(team_controller.env)
            types = []
            for t_type, fields in ac.TYPES.items():
                if Key.STORY_POINTS in fields:
                    types.append(t_type)
            # choose the right operator
            types_condition = "in ('%s')" % "', '".join(types)
            if len(types) == 1:
                types_condition = types[0] # just equals that type

            stories = ticket_manager.select(criteria={'type': types_condition,
                                                      'sprint': self.sprint.name})
            if not self.estimated:
                stories = [s for s in stories if s[Key.STATUS] == Status.CLOSED]
            # Sum up the story points of all the stories
            return sum([float(s[Key.STORY_POINTS] or 0) for s in stories])
    
    @classmethod
    def store_team_velocity(cls, env, sprint, is_estimated):
        command = TeamController.\
            StoreTeamVelocityCommand(env, sprint=sprint.name,
                                     team=sprint.team.name,
                                     estimated=is_estimated)
        return TeamController(env).process_command(command)

    
    class StoreTeamVelocityCommand(CalculateTeamVelocityCommand):
        """
        Stores the estimated team velocity for the given sprint. The estimated
        velocity is calculated as the sum of the User Story Points committed by
        the Team for the given sprint
        """
        def _execute(self, team_controller, date_converter=None,
                     as_key=None):
            """Stores the velocity into the metrics"""
            # if None is stored because 'estimated' was not given, use False
            velocity = super(TeamController.StoreTeamVelocityCommand, 
                             self)._execute(team_controller)
            
            which_velocity = {True: Key.ESTIMATED_VELOCITY, 
                              False: Key.VELOCITY}
            
            velocity_name = which_velocity[bool(self.estimated)]
            
            cmd_store = TeamController.StoreTeamMetricCommand(team_controller.env,
                                                              sprint=self.sprint,
                                                              team=self.team,
                                                              metric=velocity_name,
                                                              value=velocity)
            return team_controller.process_command(cmd_store)
    
    
    class DeleteTeamMetricCommand(controller.ICommand):
        parameters = {'sprint': validator.MandatorySprintWithTeamValidator,
                      'metric': validator.MandatoryStringValidator}
        
        def _execute(self, team_controller, date_converter=None, as_key=None):
            from agilo.scrum.metrics.model import TeamMetrics
            env = team_controller.env
            metrics = TeamMetrics(env, sprint=self.sprint, team=self.sprint.team)
            if metrics is not None:
                del metrics[self.metric]
                metrics.save()
    
    class StoreTeamMetricCommand(controller.ICommand):
        """Stores in the Team Metrics for the given team and Sprint 
        the specified metric and value"""
        parameters = {'sprint': validator.MandatorySprintValidator,
                      'team': validator.TeamValidator,
                      'metric': validator.MandatoryStringValidator,
                      'value': validator.IntOrFloatValidator}
        
        def _execute(self, team_controller, date_converter=None, as_key=None):
            """Execute the command saving the data to the Team Metrics
            table, using the Team Metrics object"""
            if not self.sprint.team and not self.team:
                raise self.CommandError("No Team assigned to the given " \
                                        "Sprint %s!?" % self.sprint.name)
            
            from agilo.scrum.metrics.model import TeamMetrics
            team_metrics = TeamMetrics(team_controller.env, 
                                       sprint=self.sprint,
                                       team=self.team)
            if team_metrics is not None:
                team_metrics[self.metric] = self.value
                team_metrics.save()
                return team_metrics[self.metric]
    
    
    class GetTeamMetricCommand(controller.ICommand):
        """Stores in the Team Metrics for the given team and Sprint 
        the specified metric and value"""
        parameters = {'sprint': validator.MandatorySprintValidator,
                      'team': validator.TeamValidator,
                      'metric': validator.MandatoryStringValidator}
        
        def _execute(self, team_controller, date_converter=None, 
                     as_key=None):
            """Execute the command saving the data to the Team Metrics
            table, using the Team Metrics object"""
            if not self.sprint.team and not self.team:
                return None
            
            from agilo.scrum.metrics.model import TeamMetrics
            team_metrics = TeamMetrics(team_controller.env, 
                                       sprint=self.sprint,
                                       team=self.team)
            if team_metrics is not None:
                return team_metrics[self.metric]


    class GetStoredTeamVelocityCommand(StoreTeamVelocityCommand):
        """Retrieves the currently stored team velocity, by default actual, with
        the estimated options, the estimated velocity"""
        
        def _execute(self, team_controller, date_converter=None,
                     as_key=None):
            """Retrieves from the team metrics the current velocity"""
            which_velocity = {True: Key.ESTIMATED_VELOCITY, 
                              False: Key.VELOCITY}
            
            velocity_name = which_velocity[bool(self.estimated)]
            
            cmd_get_metric = TeamController.GetTeamMetricCommand(team_controller.env,
                                                                 sprint=self.sprint,
                                                                 team=self.team,
                                                                 metric=velocity_name)
            return team_controller.process_command(cmd_get_metric)
    
    
    class GetTeamCommand(controller.ICommand):
        """Command to get a team for a given name"""
        parameters = {'team': validator.MandatoryTeamValidator}
        
        def _execute(self, team_controller, date_converter=None, as_key=None):
            """Returns the team for the given name if existing or None"""
            return self.return_as_value_object(self.team)
    
    @classmethod
    def confirm_commitment_for_sprint(cls, env, sprint):
        cmd = TeamController.CalculateAndStoreTeamCommitmentCommand(env, sprint=sprint, team=sprint.team)
        return TeamController(env).process_command(cmd)
    
    class CalculateAndStoreTeamCommitmentCommand(controller.ICommand):
        """Stores the team commitment in the Team Metrics for the
        given team and sprint"""
        parameters = {'team': validator.TeamValidator,
                      'sprint': validator.MandatorySprintValidator,
                      'tickets': validator.IterableValidator}
        
        def _get_remaining_time_now(self, env, sprint):
            from agilo.scrum import SprintController
            cmd_class = SprintController.GetTotalRemainingTimeCommand
            cmd_tot_rem_time = cmd_class(env, sprint=sprint, day=now(tz=utc), 
                                         tickets=self.tickets)
            commitment = SprintController(env).process_command(cmd_tot_rem_time)
            return commitment
        
        def _store_commitment(self, team_controller, commitment):
            cmd_class = TeamController.StoreTeamMetricCommand
            env = team_controller.env
            cmd_store = cmd_class(env, team=self.team, sprint=self.sprint, 
                                  metric=Key.COMMITMENT, value=commitment)
            
            return team_controller.process_command(cmd_store)
        
        def _store_commitment_in_burndown_changes(self):
            from agilo.scrum.burndown import BurndownDataConfirmCommitment
            BurndownDataConfirmCommitment(self.sprint.env).confirm_commitment_for_sprint(self.sprint)
        
        def _execute(self, team_controller, date_converter=None, as_key=None):
            # we will make use of the sprint_controller to calculate
            # the remaining time on the first sprint day
            env = team_controller.env
            commitment = self._get_remaining_time_now(env, self.sprint)
            self._store_commitment(team_controller, commitment)
            self._store_commitment_in_burndown_changes()
            return commitment
    
    
    class GetTeamCommitmentCommand(controller.ICommand):
        """Returns the stored commitment in the Team Metrics for the
        given Team and Sprint"""
        parameters = {'sprint': validator.MandatorySprintValidator,
                      'team': validator.TeamValidator}
        
        def _execute(self, team_controller, date_converter=None,
                     as_key=None):
            cmd_get_commitment = TeamController.GetTeamMetricCommand(team_controller.env,
                                                                     team=self.team,
                                                                     sprint=self.sprint,
                                                                     metric=Key.COMMITMENT)
            commitment = team_controller.process_command(cmd_get_commitment)
            if commitment > 0:
                return commitment
