# -*- encoding: utf-8 -*-
#   Copyright 2008-2009 Agile42 GmbH, Berlin (Germany)
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
#   Authors: 
#       - Felix Schwarz <felix.schwarz__at__agile42.com>

from datetime import timedelta

from agilo.charts.chart_generator import ChartGenerator
from agilo.scrum.charts import ChartType
from agilo.scrum.metrics import MetricsChartGenerator, TeamMetrics
from agilo.test import AgiloTestCase
from agilo.utils import Key
from agilo.utils.config import get_label
from agilo.utils.days_time import now



class TestCharts(AgiloTestCase):
    def setUp(self):
        self.super()
        team = self.teh.create_team(name="A-Team")
        sprint_name = 'Test sprint'
        self.sprint = self.teh.create_sprint(name=sprint_name, duration=14,
                                             team=team)
    
    def _add_metrics(self, sprint, **data):
        metrics = TeamMetrics(self.env, sprint, sprint.team)
        for key in data:
            metrics[key] = data[key]
        metrics.save()
    
    def testTeamMetricsChartContainsAllMetricsDataForMultipleSeries(self):
        self.env.compmgr.enabled[MetricsChartGenerator] = True
        today = now()
        self._add_metrics(self.sprint, **{Key.VELOCITY: 10})
        start_sprint2 = today - timedelta(days=30)
        sprint2 = self.teh.create_sprint(name='Sprint 2', start=start_sprint2, 
                                         duration=20, team=self.sprint.team)
        self._add_metrics(sprint2, **{Key.ESTIMATED_VELOCITY: 7})
        start_sprint3 = today - 2 * timedelta(days=30)
        sprint3 = self.teh.create_sprint(name='Sprint 3', start=start_sprint3,
                                         duration=20, team=self.sprint.team)
        self._add_metrics(sprint3, **{Key.VELOCITY: 5})
        self._add_metrics(sprint3, **{Key.ESTIMATED_VELOCITY: 9})
        
        widget = ChartGenerator(self.env).get_chartwidget(ChartType.TEAM_METRICS, 
                      team_name=self.sprint.team.name, metric_names=[Key.ESTIMATED_VELOCITY, Key.VELOCITY])
        self.assert_equals(['Sprint 3', 'Sprint 2', self.sprint.name], widget.data['sprint_names'])
        metrics = widget.data['metrics']
        self.assert_equals(2, len(metrics))
        
        velocity_label, velocity_data = metrics[0]
        self.assert_equals(get_label(Key.ESTIMATED_VELOCITY), velocity_label)
        self.assert_equals([(0, 9), (1, 7)], velocity_data)
        
        velocity_label, velocity_data = metrics[1]
        self.assert_equals(get_label(Key.VELOCITY), velocity_label)
        self.assert_equals([(0, 5), (2, 10)], velocity_data)


