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
from agilo.scrum.charts import ChartType, ScrumFlotChartWidget
from agilo.scrum.sprint.controller import SprintController
from agilo.utils.config import AgiloConfig

__all__ = ['SprintTicketStatsChartGenerator']


class SprintTicketStatsChartGenerator(Component):
    
    implements(IAgiloWidgetGenerator)
    
    name = ChartType.SPRINT_TICKET_STATS
    
    def can_generate_widget(self, name):
        return (name == self.name)
    
    def _push_colors_if_available(self, widget, kwargs):
        if 'FORE_COLOR' in kwargs:
            widget.update_data(color_planned=kwargs['FORE_COLOR'])
        if 'BACK_COLOR' in kwargs:
            widget.update_data(color_closed=kwargs['BACK_COLOR'])
    
    def generate_widget(self, name, **kwargs):
        ticketstats_widget = SprintTicketStatsChartWidget(self.env)
        self._push_colors_if_available(ticketstats_widget, kwargs)
        if 'sprint_name' in kwargs:
            sprint_name = kwargs.get('sprint_name')
            ticketstats_widget.populate_with_sprint_data(sprint_name)
        return ticketstats_widget
    
    def get_backlog_information(self):
        from agilo.scrum.backlog import BacklogType
        return {self.name: (BacklogType.SPRINT,)}


class SprintTicketStatsChartWidget(ScrumFlotChartWidget):
    """This widget generates HTML and JS code so that Flot can generate a 
    grouped bar chart for the sprint displaying how many tickets are 
    planned vs. closed for every ticket type."""
    
    default_width =  400
    default_height = 400
    
    def __init__(self, env, **kwargs):
        template_filename = 'scrum/sprint/templates/agilo_sprint_ticket_stats_chart.html'
        self._define_chart_resources(env, template_filename, kwargs)
        self.super(env, template_filename, **kwargs)
    
    def populate_with_sprint_data(self, sprint_name):
        """Populate the chart with sprint statistics"""
        cmd_stats = SprintController.GetTicketsStatisticsCommand(self.env,
                                                                 sprint=sprint_name)
        tickets_stats = SprintController(self.env).process_command(cmd_stats)
        
        planned, closed, total, labels = [], [], [], []
        
        aliases = AgiloConfig(self.env).ALIASES
        for i, t_type in enumerate(tickets_stats):
            nr_planned, nr_in_progress, nr_closed = tickets_stats[t_type]
            planned.append((i, nr_planned))
            closed.append((i, nr_closed))
            nr_total = nr_planned + nr_in_progress + nr_closed
            total.append((i, nr_total))
            alias = aliases.get(t_type, t_type)
            labels.append((i, alias))
        
        self.data.update(
            dict(sprint_name=sprint_name, labels=labels, 
                 planned=planned, closed=closed, total=total)
        )
