# -*- encoding: utf-8 -*-
#   Copyright 2008 Agile42 GmbH, Berlin (Germany)
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
#       - Jonas von Poser jonas.vonposer_at_agile42.com>
#       - Sebastian Schulze <sebastian.schulze_at_agile42.com>

from trac.util.compat import set

from agilo.scrum.metrics.model import TeamMetrics
from agilo.test import AgiloTestCase
from agilo.utils.days_time import now


class TestTeamMetrics(AgiloTestCase):
    """Tests for the metrics model class TeamMetrics"""
    
    def setUp(self):
        self.super()
        self.team = self.teh.create_team(name="The A-Team")
        self.sprint = self.teh.create_sprint(name="Test Sprint", 
                         start=now(),  duration=7, team=self.team)
        
        self.metrics = TeamMetrics(self.env, self.sprint, self.team)
        self.metrics['quux'] = 42
        self.metrics.save()
    
    def test_keys_returns_all_metric_names(self):
        self.assert_equals(set(['quux']), set(self.metrics.keys()))
        self.metrics['foo'] = 21
        self.assert_equals(set(['foo', 'quux']), set(self.metrics.keys()))
    
    def test_metric_iterator_iterates_over_all_metric_names(self):
        self.assert_equals(['quux'], [i for i in self.metrics])
    
    def test_can_save_decimal_values_in_metrics(self):
        self.metrics['foo'] = 4.2
        self.metrics.save()
        
        metrics = TeamMetrics(self.env, self.sprint, self.team)
        self.assert_equals(4.2, metrics['foo'])
    
    def test_can_load_metric_with_specifying_team_explicitely(self):
        metrics = TeamMetrics(self.env, self.sprint)
        self.assert_equals(42, metrics['quux'])
    
    def test_delete_metric_is_automatically_persistant(self):
        del self.metrics['quux']
        self.assert_none(self.metrics['quux'])
        
        metrics = TeamMetrics(self.env, self.sprint, self.team)
        self.assert_none(metrics['quux'])
    
    def test_can_handle_multiple_metrics_with_the_same_key_in_different_sprints(self):
        second_sprint = self.teh.create_sprint(name="Second Sprint", 
                                               start=self.sprint.start, duration=5, 
                                               team=self.team)
        metrics_key = 'quux'
        second_metrics = TeamMetrics(self.env, second_sprint)
        second_metrics[metrics_key] = 21
        second_metrics.save()
        
        metrics = TeamMetrics(self.env, self.sprint)
        second_metrics = TeamMetrics(self.env, second_sprint)
        self.assert_equals(42, metrics[metrics_key])
        self.assert_equals(21, second_metrics[metrics_key])
    
    def test_as_dict_serializes_all_metrics_entries(self):
        self.sprint.team = self.team
        metrics = TeamMetrics(self.env, self.sprint)
        metrics['bar'] = 7
        metrics.save()
        
        self.assert_equals({'quux': 42, 'bar': 7}, metrics.as_dict())


if __name__ == '__main__':
    from agilo.test.testfinder import run_unit_tests
    run_unit_tests(__file__)

