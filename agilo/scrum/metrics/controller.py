# -*- coding: utf-8 -*-
#   Copyright 2009 Agile42 GmbH
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
#     - Felix Schwarz <felix.schwarz__at__agile42.com>

from agilo.api import controller, validator
from agilo.charts import ChartGenerator
from agilo.scrum import SprintController
from agilo.scrum.metrics.model import TeamMetrics
from agilo.utils import Key


__all__ = ['MetricsController']


class MetricsController(controller.Controller):
    """Take care of processing any command related to metrics"""
    
    def __init__(self):
        self.sprint_controller = SprintController(self.env)
    
    class ListMetricsCommand(controller.ICommand):
        """Command to fetch a list of (all) metrics for a team"""
        parameters = {'team': validator.MandatoryStringValidator}
        
        def _execute(self, metrics_controller, date_converter=None,
                     as_key=None):
            sprint_controller = metrics_controller.sprint_controller
            
            cmd_class = SprintController.ListSprintsCommand
            cmd = cmd_class(metrics_controller.env, 
                            criteria={'team': self.team}, 
                            order_by=[Key.START])
            cmd.native = True
            sprints = sprint_controller.process_command(cmd)
            
            metrics_by_sprint = list()
            env = metrics_controller.env
            for sprint in sprints:
                metrics = TeamMetrics(env, sprint=sprint)
                metrics_by_sprint.append((sprint, metrics))
            
            return self.return_as_value_object(metrics_by_sprint)
    
    class StoreMetricsCommand(controller.ICommand):
        parameters = {'sprint': validator.MandatorySprintWithTeamValidator,
                      'name': validator.MandatoryStringValidator,
                      'value': validator.IntOrFloatValidator,}
        
        def _execute(self, metrics_controller, date_converter=None, as_key=None):
            metrics = self.sprint.get_team_metrics()
            metrics[self.name] = self.value
            metrics.save()
            # Need to invalidate the chart cache, or will not recalculate
            # the burndown with the new factor
            env = metrics_controller.env
            ChartGenerator(env).invalidate_cache(sprint_name=self.sprint.name)

