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

from agilo.charts import FlotChartWidget
from agilo.charts.api import IAgiloWidgetGenerator
from agilo.scrum.charts import ChartType
from agilo.utils import Key
from agilo.utils.config import get_label


class MetricsChartGenerator(Component):
    
    implements(IAgiloWidgetGenerator)
    
    name = ChartType.TEAM_METRICS
    
    def can_generate_widget(self, name):
        return (name == self.name)
    
    def generate_widget(self, name, team_name=None, metric_names=None, **kwargs):
        metrics_widget = MetricsChartWidget(self.env)
        # not sure why we need this but for Andrea this fixed a problem where
        # the widget iterated over a plain string (getting tens of labels).
        if isinstance(metric_names, basestring):
            metric_names = (metric_names,)
        if team_name != None:
            metrics_widget.update_data(team_name=team_name)
            if metric_names != None:
                metrics_widget.fill(team_name, metric_names)
        return metrics_widget
    
    def get_cache_components(self, keys):
        components = ['name', 'sprint_name', 'team_name']
        if 'metric_names' in keys:
            components.extend(tuple(keys))
        return tuple(components)
    
    def get_backlog_information(self):
        return dict()


class MetricsChartWidget(FlotChartWidget):
    """This widget generates HTML and JS code so that Flot can generate a 
    chart for the team metrics (per sprint) combining some metrics."""
    
    default_width =  400
    default_height = 200
    
    def __init__(self, env, **kwargs):
        from agilo.scrum.sprint import SprintModelManager
        template_filename = 'scrum/metrics/templates/agilo_metrics_chart.html'
        self._define_chart_resources(env, template_filename, kwargs)
        super(MetricsChartWidget, self).__init__(env, template_filename, **kwargs)
        self.sp_manager = SprintModelManager(env)
    
    def _get_metrics_data(self, metric_names, sprint_names, metrics_by_sprint):
        metrics = []
        for label in metric_names:
            metric_values = []
            for i, sprint_name in enumerate(sprint_names):
                m = metrics_by_sprint[sprint_name]
                value = m[label]
                if value != None:
                    metric_values.append((i, value))
            metrics.append((get_label(label), metric_values))
        return metrics
    
    def _make_title(self, metric_names):
        titles = []
        for name in metric_names:
            titles.append(get_label(name))
        return ' / '.join(titles)
    
    def fill(self, team_name, metric_names):
        # Charts are not allowed to import the model classes globally
        from agilo.scrum.metrics import TeamMetrics
        sprints = self.sp_manager.select( 
                                criteria={'team': team_name}, 
                                order_by=['%s' % Key.START])
        sprint_names = [sprint.name for sprint in sprints]
        metrics_by_sprint = dict([(s.name, TeamMetrics(self.env, sprint=s)) \
                                  for s in sprints])
        metrics = self._get_metrics_data(metric_names, sprint_names, metrics_by_sprint)
        title = self._make_title(metric_names)
        self.data.update(
            dict(team_name=team_name, sprint_names=sprint_names,
                 metrics=metrics, title=title))

