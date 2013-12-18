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
#   Authors:
#        - Felix Schwarz <felix.schwarz__at__agile42.com>

from trac.core import Component, implements

from agilo.charts.api import IAgiloWidgetGenerator
from agilo.scrum.sprint.controller import SprintController
from agilo.scrum.charts import ChartType, ScrumFlotChartWidget

__all__ = ["ResourcesAssignmentPieChartGenerator"]

class ResourcesAssignmentPieChartGenerator(Component):
    
    implements(IAgiloWidgetGenerator)
    
    name = ChartType.SPRINT_RESOURCES_STATS
    
    def can_generate_widget(self, name):
        return (name == self.name)
    
    def generate_widget(self, name, **kwargs):
        resource_widget = ResourceAssignmentPieChartWidget(self.env)
        if 'sprint_name' in kwargs:
            if 'cached_data' in kwargs:
                resource_widget.update_data(cached_data=kwargs['cached_data'])
            sprint_name = kwargs.get('sprint_name')
            resource_widget.populate_with_sprint_data(sprint_name)
        return resource_widget
    
    def get_backlog_information(self):
        from agilo.scrum.backlog import BacklogType
        return {self.name: (BacklogType.SPRINT,)}


class ResourceAssignmentPieChartWidget(ScrumFlotChartWidget):
    """This widget generates HTML and JS code so that Flot can generate a pie
    chart for the sprint displaying the remaining time for every resource in
    a sprint."""
    
    default_width =  400
    default_height = 400
    
    def __init__(self, env, **kwargs):
        template_filename = 'scrum/sprint/templates/agilo_resource_assignment_piechart.html'
        self._define_chart_resources(env, template_filename, kwargs)
        self.super(env, template_filename, **kwargs)
    
    def populate_with_sprint_data(self, sprint_name):
        self.data['sprint_name'] = sprint_name
        tickets = self._get_prefetched_backlog()
        cmd_resources = SprintController.GetResourceStatsCommand(self.env,
                                                                 sprint=sprint_name,
                                                                 tickets=tickets)
        #resource_stats = sprint.get_resources_stats(tickets=tickets)
        self.data['resource_stats'] = SprintController(self.env).process_command(cmd_resources)

