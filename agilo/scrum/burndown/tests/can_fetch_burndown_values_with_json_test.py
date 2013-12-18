# -*- encoding: utf-8 -*-
#   Copyright 2009 Agile42 GmbH, Berlin (Germany)
#   Copyright 2011 Agilo Software GmbH All rights reserved
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicablelaw or ar in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import agilo.utils.filterwarnings

from trac.web import RequestDone

from agilo.test import AgiloTestCase
from agilo.utils import Action, Key
from agilo.scrum.burndown.json_ui import BurndownValuesView
from agilo.scrum.burndown.tests.burndownchart_test import BurndownChartTestCase
from agilo.utils.days_time import now


class CanFetchBurndownValuesWithJSONTest(AgiloTestCase):
    
    def setUp(self):
        self.super()
        self.sprint = self.teh.create_sprint('fnord')
        self.view = BurndownValuesView(self.env)
        self.req = self.teh.mock_request()
        self.teh.grant_permission(self.req.authname, Action.BACKLOG_VIEW)
    
    def call(self, sprint_name, **kwargs):
        return self.view.do_get(self.req, dict(sprint=sprint_name, **kwargs))
    
    def test_can_get_values_for_empty_sprint(self):
        data = self.call('fnord')
        keys = ["trend_data", "capacity_data", "ideal_data", "remaining_times",
                "ticks", "weekend_data", "today_data", "today_color"]
        for key in keys:
            self.assert_contains(key, data)
    
    def test_shows_error_message_when_sprint_does_not_exist(self):
        self.assert_raises(RequestDone, self.call, 'invalid')
        data = self.req.response.body_as_json()
        self.assert_contains('errors', data)
        self.assert_contains('No Sprint found with', data['errors'][0])
    
    def test_need_backlog_view_privileges(self):
        self.teh.revoke_permission(self.req.authname, Action.BACKLOG_VIEW)
        self.assert_raises(RequestDone, self.call, 'fnord')
        data = self.req.response.body_as_json()
        self.assert_contains('errors', data)
        self.assert_contains('No permission', data['errors'][0])
    
    def test_capacity_in_json_data_is_empty_when_filtered(self):
        self.sprint.team = self.teh.create_team('Team')
        member = self.teh.create_member('foo', self.sprint.team)
        
        data = self.call('fnord', filter_by='foo')
        self.assert_not_equals(0, len(data['capacity_data']))
        
        self.teh.enable_burndown_filter()
        data = self.call('fnord', filter_by='foo')
        self.assert_equals(0, len(data['capacity_data']))


class CanFetchFilteredBurndownValuesWithJSONTest(BurndownChartTestCase):
    
    def setUp(self):
        self.super()
        self.view = BurndownValuesView(self.env)
        self.req = self.teh.mock_request()
        self.teh.grant_permission(self.req.authname, Action.BACKLOG_VIEW)
        self.teh.enable_burndown_filter()

    def call(self, sprint_name, **kwargs):
        return self.view.do_get(self.req, dict(sprint=sprint_name, **kwargs))
    
    def _create_remaining_times(self):
        self._create_sprint_with_team()
        self._remaining_time(3, self.sprint.start, Key.COMPONENT, 'foo')
        self._remaining_time(6, self.sprint.start, Key.COMPONENT, 'bar')
        self._remaining_time(9, self.sprint.start)
        self._simulate_confirm_commitment(self.sprint.start)
        self._remaining_time(-2, now(), Key.COMPONENT, 'foo')
        self._remaining_time(-4, now(), Key.COMPONENT, 'bar')
        self._remaining_time(-6, now())
    
    def test_remaining_time_values_are_correct_when_filtered(self):
        self._create_remaining_times()
        data = self.call(self.sprint.name, filter_by='foo')
        remaining_times = data['remaining_times']
        # We will see three data points because of two changes that
        # are aggregated and one third which is the burndown at
        # the current time. This entry is generated because the second
        # change is at least a few milliseconds before
        self.assert_length(3, remaining_times)
        self.assert_equals(3, remaining_times[0][1])  # 1st change +3
        self.assert_equals(1, remaining_times[1][1])  # 2nd change -2
        self.assert_equals(1, remaining_times[2][1])  # right now, +0

    def test_remaining_time_values_are_correct_when_not_filtered(self):
        self._create_remaining_times()
        data = self.call(self.sprint.name, filter_by='')
        remaining_times = data['remaining_times']
        self.assert_length(3, remaining_times)
        self.assert_equals(3+6+9, remaining_times[0][1])
        # Wonder about the -2 ?
        # Check the comment in BurndownDataAggregator._compute_aggregation
        self.assert_equals(3+6+9-2, remaining_times[1][1])
        self.assert_equals(3+6+9-2-4-6, remaining_times[2][1])
    
