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

from datetime import datetime, timedelta, date

import agilo.utils.filterwarnings

from trac.util.datefmt import get_timezone, localtz, utc

from agilo.api import ValueObject
from agilo.charts.chart_generator import ChartGenerator
from agilo.scrum.burndown.charts import BurndownChartGenerator, BurndownWidget, calculate_ideal_burndown
from agilo.scrum.burndown import BurndownDataChange, BurndownDataConfirmCommitment
from agilo.scrum.burndown.model import BurndownEntry
from agilo.scrum.charts import ChartType
from agilo.scrum.team import TeamController
from agilo.test import AgiloTestCase
from agilo.ticket import AgiloTicket
from agilo.utils import Key, Type
from agilo.utils.compat import json
from agilo.utils.days_time import midnight, now
from agilo.utils.config import AgiloConfig


class BurndownChartTestCase(AgiloTestCase):
    # Class to share the setup code for the burndown chart between the 
    # tests for the 'component burndown' and the generic burndown chart. I 
    # wanted to keep the 'component burndown' functionality as separated as 
    # possible.
    
    def setUp(self):
        self.super()
        self.teh.disable_sprint_date_normalization()
        self.env.compmgr.enabled[BurndownChartGenerator] = True
        self.now = now().replace(microsecond=0)
    
    def _remove_invalid_attributes_for_tasks(self, attributes):
        # For the filtered burndown we need the component attribute which is not
        # enabled for the usual case - therefore we'll just ignore that one.
        for field_name in attributes.keys():
            if not AgiloTicket(self.env, t_type=Type.TASK).is_writeable_field(field_name):
                attributes.pop(field_name)
        return attributes
    
    def _create_task(self, sprint, **kwargs):
        attributes = {Key.SUMMARY: 'Task', Key.SPRINT: sprint.name}
        attributes.update(kwargs)
        attributes = self._remove_invalid_attributes_for_tasks(attributes)
        
        ticket = self.teh.create_ticket(Type.TASK, props=attributes)
        return ticket
    
    def _create_sprint_with_team(self):
        member = self.teh.create_member('FooBarMember', team='MyTeam')
        self.team = member.team
        sprint_start = self.now - timedelta(days=4)
        self.sprint = self.teh.create_sprint("FilteredChartSprint", start=sprint_start, team=self.team)
    
    def _remaining_time(self, delta, when, marker_key=None, marker_value=True):
        BurndownDataChange.remaining_time_entry(self.env,
            delta=delta, when=when, scope=self.sprint.name,
            marker_key=marker_key, marker_value=marker_value,
        ).save()
    
    def _create_remaining_times(self, when_to_create_second_remaining_time=None):
        self._create_sprint_with_team()
        self._remaining_time(3+6+9, self.sprint.start) # 18
        if when_to_create_second_remaining_time is None:
            when_to_create_second_remaining_time = now() - timedelta(hours=3)
        self._remaining_time(-1+-2+-3, when_to_create_second_remaining_time) # -6
    
    def _store_commitment(self, commitment):
        cmd_class = TeamController.StoreTeamMetricCommand
        cmd = cmd_class(self.env, sprint=self.sprint, team=self.sprint.team,
                        metric=Key.COMMITMENT, value=commitment)
        TeamController(self.env).process_command(cmd)
    
    def _simulate_confirm_commitment(self, when):
        BurndownDataConfirmCommitment(self.env).confirm_commitment_for_sprint(self.sprint, when=when)
    
    def get_widget(self, sprint_name, use_cache=False, filter_by=None, tz=localtz):
        get_widget = ChartGenerator(self.env).get_chartwidget
        widget = get_widget(ChartType.BURNDOWN, sprint_name=sprint_name,
                            use_cache=use_cache, filter_by=filter_by)
        widget.prepare_rendering(self.teh.mock_request(tz=tz))
        return widget
    
    def get_chart_data(self, param_name, filter_by=None, use_cache=False, tz=localtz, storage='burndown_data'):
        return self.get_widget(self.sprint.name, use_cache, filter_by, tz).__getattribute__(storage)[param_name]
    
    # REFACT: should get rid of convert_timestamps, all callers should use the converted version
    def series_from_chart(self, series_name, filter_by=None, use_cache=False, tz=localtz):
        data = self.get_chart_data(series_name, filter_by=filter_by, use_cache=use_cache, tz=tz)
        return [(self.js_to_datetime(timestamp, tz=tz), value) for (timestamp, value) in data]
    
    def get_values_from_chart(self, param_name='remaining_times', 
                              filter_by=None, use_cache=False):
        data = self.get_chart_data(param_name, filter_by, use_cache)
        parameters = [value for (timestamp, value) in data]
        return parameters
    
    def get_times_from_chart(self, param_name='remaining_times', tz=localtz):
        series = self.series_from_chart(param_name, tz=tz)
        return [when for (when, value) in series]
    
    def js_to_datetime(self, timestamp_in_milliseconds, tz=utc):
        timestamp = timestamp_in_milliseconds / 1000
        return datetime.utcfromtimestamp(timestamp).replace(tzinfo=tz)
    


class BurndownChartTest(BurndownChartTestCase):
    def setUp(self):
        self.super()
        self._create_remaining_times()
    
    def test_remaining_time_values_are_as_created(self):
        remaining_times = self.get_values_from_chart()
        self.assert_true(len(remaining_times) >= 2)
        self.assert_equals(18, remaining_times[0])
        self.assert_equals(12, remaining_times[1])
    
    def test_ideal_burndown_starts_from_commitment(self):
        self._simulate_confirm_commitment(self.sprint.start)
        ideal_data = self.get_values_from_chart(param_name='ideal_data')
        self.assert_not_equals(0, len(ideal_data))
        self.assert_almost_equals(12, ideal_data[0], max_delta=0.001)
        self.assert_equals(0, ideal_data[-1])
    
    def test_ideal_burndown_starts_from_time_of_first_burndown_change(self):
        today = now()
        self._simulate_confirm_commitment(today)
        first_ideal_burndown = self.get_times_from_chart('ideal_data')[0]
        self.assert_time_equals(today, first_ideal_burndown)
    
    def _ideal_burndown(self, commitment, commitment_when=None, capacities=None):
        commitment_when = commitment_when or now() - timedelta(days=3)
        if capacities is None:
            capacities = [
                (now() - timedelta(days=3), 6.0),
                (now() - timedelta(days=2), 4.0),
                (now() - timedelta(days=1), 2.0),
                (now(), 0)
            ]
        first_burndown = ValueObject(when=commitment_when, remaining_time=commitment)
        ideal_burndown = calculate_ideal_burndown(capacities, first_burndown, self.sprint)
        return [remaining for (when, remaining) in ideal_burndown]
    
    def test_ideal_burndown_is_same_as_capacity_if_commitment_is_equal_to_capacity(self):
        self.assert_equals([6,4,2,0], self._ideal_burndown(6))
    
    def test_ideal_burndown_is_proportional_to_capacity(self):
        self.assert_equals([3,2,1,0], self._ideal_burndown(3))

    def test_ideal_burndown_doesnt_raise_division_by_Zero_exception(self):
        commitment_when =  now() - timedelta(days=2)
        capacities = [
            (now() - timedelta(days=3), 1.0),
            (commitment_when, 0.0),
            (now() - timedelta(days=1), 0.0),
            (now(), 0.0)
        ]
        self.assert_equals([0,0,0], self._ideal_burndown(2, commitment_when=commitment_when,capacities=capacities))

    
    def test_ideal_burndown_visible_even_if_no_team_assigned_to_sprint(self):
        self.sprint.team = None
        self.sprint.save()
        ideal_data = self.get_values_from_chart(param_name='ideal_data')
        self.assert_not_equals(0, len(ideal_data))
        self.assert_equals(3+6+9, ideal_data[0])
    
    def test_ideal_burndown_visible_even_if_no_commitment(self):
        self.assert_not_none(self.sprint.team)
        self.assert_not_equals(0, len(self.sprint.team.members))
        ideal_data = self.get_values_from_chart(param_name='ideal_data')
        self.assert_not_equals(0, len(ideal_data))
        self.assert_almost_equals(3+6+9, ideal_data[0], max_delta=0.001)
    
    def _remove_member_from_team(self, member):
        member.team = None
        member.save()
    
    def test_display_linear_ideal_burndown_if_no_capacity_available(self):
        team_without_members = self.teh.create_team(name='test_display_linear_ideal_burndown_if_no_capacity_available')
        self.sprint.team = team_without_members
        self.assert_equals(0, len(self.sprint.team.members))
        initial_commitment = 3 + 6 + 9
        self._store_commitment(initial_commitment)
        
        ideal_data = self.get_values_from_chart(param_name='ideal_data')
        self.assert_not_equals(0, len(ideal_data))
        self.assert_equals(initial_commitment, ideal_data[0])
        
        last_value = ideal_data[0]
        last_difference = None
        for ideal_value in ideal_data[1:]:
            difference = ideal_value - last_value
            if last_difference is not None:
                self.assert_almost_equals(last_difference, difference, max_delta=0.001)
            last_difference = difference
            last_value = ideal_value
        
        self.assert_almost_equals(0, ideal_data[-1], max_delta=0.001)
    
    def test_last_item_in_ideal_burndown_is_end_of_sprint_time(self):
        self.sprint.end = self.sprint.end.replace(tzinfo=localtz)
        times = self.get_times_from_chart('ideal_data', tz=localtz)
        local_end = self.sprint.end.astimezone(localtz)
        self.assert_equals(local_end, times[-1])
    
    def test_can_deal_with_localtz_timezone_for_dates(self):
        times = self.get_times_from_chart(tz=localtz)
        self.assert_time_equals(self.sprint.start, times[0])
        self.assert_time_equals(self.now, times[-1])
    
    def test_can_deal_with_different_timezones_for_dates(self):
        # Actually Bangkok has no summer/winter time so that's ideal to test 
        # even with trac's own timezones which don't know anything about dst.
        bangkok_tz = get_timezone('GMT +7:00')
        times = self.get_times_from_chart(tz=bangkok_tz)
        start_in_bangkok = self.sprint.start.astimezone(bangkok_tz)
        self.assert_equals(start_in_bangkok, times[0])
        
        bankok_now = now().astimezone(bangkok_tz)
        self.assert_time_equals(bankok_now, times[-1])
    
    def test_weekends_are_relative_to_the_users_timezone(self):
        self.sprint.start = datetime(2009, 6, 23, 7, 0, tzinfo=utc)
        self.sprint.end = datetime(2009, 7, 6, 19, 0, tzinfo=utc)
        self.sprint.save()
        bangkok_tz = get_timezone('GMT +7:00')
        times = self.get_times_from_chart('weekend_data', tz=bangkok_tz)
        
        self.assert_equals(4, len(times))
        first_weekend = [datetime(2009, 6, 27, 0, 0, tzinfo=bangkok_tz),
                         datetime(2009, 6, 28, 0, 0, tzinfo=bangkok_tz),]
        self.assert_equals(first_weekend, times[0:2])
        
        second_weekend = [datetime(2009, 7, 4, 0, 0, tzinfo=bangkok_tz),
                          datetime(2009, 7, 5, 0, 0, tzinfo=bangkok_tz),]
        self.assert_equals(second_weekend, times[2:])
    
    def test_today_is_relative_to_the_users_timezone(self):
        self.assert_true(self.sprint.is_currently_running)
        bangkok_tz = get_timezone('GMT +7:00')
        times = self.get_chart_data('utc_today_data', tz=bangkok_tz, storage='data')[0]
        self.assert_equals(2, len(times))
        # Now we test that midnight in bangkok is normalized as UTC data with
        # offset
        now_in_bangkok = self.now.astimezone(bangkok_tz)
        today_start_in_bangkok = midnight(now_in_bangkok)
        self.assert_equals(today_start_in_bangkok, times[0])
        self.assert_equals(today_start_in_bangkok + timedelta(days=1), times[1])
    
    def test_guard_against_no_sprint(self):
        widget = self.get_widget('invalid_sprint')
        self.assert_true('error_message' in widget.data)
    
    def test_can_interpolate_ideal_time_to_given_time(self):
        widget = self.get_widget(self.sprint.name, use_cache=False)
        today = now()
        yesterday = today - timedelta(days=1)
        ideal_data = [(yesterday, 10), (today, 20)]
        self.assert_equals(15, widget._calculate_ideal_burndown_at_datetime(ideal_data, today - timedelta(hours=12)))
    
    def test_returns_zero_if_ideal_data_is_empty(self):
        widget = self.get_widget(self.sprint.name, use_cache=False)
        today = now()
        self.assert_equals(0, widget._calculate_ideal_burndown_at_datetime([], today))
    
    # -------------------------------------------------------------------------
    # These tests access BurndownWidget._today_color() directly - the old test
    # tried to set capacity/commitment and team members very carefully to get
    # the correct test setting through the public 'interface'.
    # However the old test was flaky at times and beyond fixing, better a 
    # stable, reliable test which accesses a private method.
    
    def test_today_color_is_green_if_actual_burndown_is_below_ideal_burndown(self):
        widget = BurndownWidget(self.env)
        actual_burndown = [BurndownEntry(15, datetime(2010, 5, 1, tzinfo=localtz)), 
                           BurndownEntry(10, datetime(2010, 5, 2, tzinfo=localtz))]
        ideal_burndown = [(datetime(2010, 5, 1, tzinfo=localtz), 30), 
                          (datetime(2010, 5, 2, tzinfo=localtz), 20)]
        actual_color = widget._today_color(self.sprint, actual_burndown, ideal_burndown)
        self.assert_equals(BurndownWidget.GOOD_COLOR, actual_color)
    
    def test_today_color_is_warning_if_actual_burndown_exceeds_ideal_by_10_percent(self):
        widget = BurndownWidget(self.env)
        actual_burndown = [BurndownEntry(10, datetime(2010, 5, 1, tzinfo=localtz)), 
                           BurndownEntry(11.1, datetime(2010, 5, 2, tzinfo=localtz))]
        ideal_burndown = [(datetime(2010, 5, 1, tzinfo=localtz), 10), 
                          (datetime(2010, 5, 2, tzinfo=localtz), 10)]
        actual_color = widget._today_color(self.sprint, actual_burndown, ideal_burndown)
        self.assert_equals(BurndownWidget.WARNING_COLOR, actual_color)
    
    def test_today_color_is_warning_if_actual_burndown_exceeds_ideal_by_30_percent(self):
        widget = BurndownWidget(self.env)
        actual_burndown = [BurndownEntry(10, datetime(2010, 5, 1, tzinfo=localtz)), 
                           BurndownEntry(13.1, datetime(2010, 5, 2, tzinfo=localtz))]
        ideal_burndown = [(datetime(2010, 5, 1, tzinfo=localtz), 10), 
                          (datetime(2010, 5, 2, tzinfo=localtz), 10)]
        actual_color = widget._today_color(self.sprint, actual_burndown, ideal_burndown)
        self.assert_equals(BurndownWidget.BAD_COLOR, actual_color)
    # --------------------------------------------------------------------------
    
    def test_only_one_point_for_today(self):
        # this is the crazy burndown chart regression test
        self.assert_true(self.sprint.is_currently_running)
        
        bangkok = get_timezone('GMT +7:00')
        times = self.get_times_from_chart(tz=bangkok)
        self.assert_smaller_than(times[-2], times[-1])
        self.assert_time_equals(now(), times[-1])
    
    def test_trend_lines_starts_from_last_burndown_change(self):
        one_day_ago = now() - timedelta(days=1)
        self._simulate_confirm_commitment(one_day_ago)
        self._remaining_time(35, now() - timedelta(hours=1))
        trend_data = self.get_times_from_chart('trend_data')
        self.assert_time_equals(now(), trend_data[0])
    
    def test_trend_line_until_end_of_sprint(self):
        self.assert_true(self.sprint.is_currently_running)
        
        berlin = get_timezone('GMT +2:00')
        trend_line = self.get_times_from_chart('trend_data', tz=berlin)
        self.assert_not_equals(0, len(trend_line))
        self.assert_time_equals(self.sprint.end, trend_line[-1])
    
    def test_can_serialize_json_data_as_real_json(self):
        widget = self.get_widget(self.sprint.name)
        # This raised an exception once as data conversion was problematic.
        json.dumps(widget.data_as_json())
    
    def test_ticks_are_present(self):
        ticks = self.get_chart_data('ticks')
        self.assert_not_equals(0, len(ticks))
    
    def test_first_tick_is_after_sprint_start(self):
        ticks = self.get_times_from_chart('ticks')
        self.assert_almost_equals(self.sprint.start, ticks[0], max_delta=timedelta(days=1))
        self.assert_true(ticks[0] >= self.sprint.start)
    
    def test_first_tick_is_before_sprint_end(self):
        ticks = self.get_times_from_chart('ticks')
        self.assert_almost_equals(self.sprint.end, ticks[-1], max_delta=timedelta(days=1))
        self.assert_true(ticks[-1] < self.sprint.end)
    

class BurndownChartCanBeFilteredByAdditionalAttributeTest(BurndownChartTestCase):
    
    def setUp(self):
        self.super()
        self.teh.add_field_for_type(Key.COMPONENT, Type.TASK)
        self.teh.enable_burndown_filter()
        self._create_remaining_times()
    
    def _create_remaining_times(self):
        self._create_sprint_with_team()
        self._remaining_time(3, self.sprint.start, Key.COMPONENT, 'foo')
        self._remaining_time(6, self.sprint.start, Key.COMPONENT, 'bar')
        self._remaining_time(9, self.sprint.start)
        self._simulate_confirm_commitment(self.sprint.start)
        self._remaining_time(-2, now(), Key.COMPONENT, 'foo')
        self._remaining_time(-4, now(), Key.COMPONENT, 'bar')
        self._remaining_time(-6, now())
    
    def test_chart_can_show_all_items(self):
        remaining_times = self.get_values_from_chart()
        self.assert_length(3, remaining_times)
        self.assert_equals(3 + 6 + 9, remaining_times[0])
        self.assert_equals(1 + 2 + 3, remaining_times[-1])
    
    def test_chart_shows_only_filtered_tasks(self):
        remaining_times = self.get_values_from_chart(filter_by='foo')
        self.assert_length(3, remaining_times)
        self.assert_equals(3, remaining_times[0])
        self.assert_equals(1, remaining_times[-1])
    
    def test_no_capacity_line_if_filtered(self):
        capacity_data = self.get_values_from_chart(param_name='capacity_data')
        self.assertNotEqual(0, len(capacity_data))
        
        capacity_data = self.get_values_from_chart(param_name='capacity_data',
                                                   filter_by='foo')
        self.assert_equals(0, len(capacity_data))
    
    def get_commitment(self, team, sprint):
        cmd = TeamController.GetTeamCommitmentCommand(self.env, sprint=sprint, team=team)
        return TeamController(self.env).process_command(cmd)
    
    def test_cache_handles_filtered_chart_gracefully(self):
        capacity_data = self.get_values_from_chart(param_name='capacity_data', 
                                                   use_cache=True)
        self.assertNotEqual(0, len(capacity_data))
        
        capacity_data = self.get_values_from_chart(param_name='capacity_data',
                                                   filter_by='foo', use_cache=True)
        self.assert_equals(0, len(capacity_data))
    
    def test_capacity_in_json_data_is_empty_when_filtered(self):
        widget = self.get_widget(self.sprint.name, filter_by='foo')
        capacity_data = widget.data_as_json()['capacity_data']
        self.assert_equals(0, len(capacity_data))
    

class CanTransformDataAsJSON(AgiloTestCase):
    def test_raise_if_rendering_was_not_prepared(self):
        widget = BurndownWidget(self.env)
        self.assert_raises(Exception, widget.data_as_json)
    

class BurndownChartCanShowWorkingDaysOnly(BurndownChartTestCase):
    now = now()
    today = midnight(now)
    yesterday = today - timedelta(days=1)
    tomorrow = today + timedelta(days=1)
    
    def setUp(self):
        self.super()
        self.env.config.set(AgiloConfig.AGILO_GENERAL, 'burndown_should_show_working_days_only', True)
        self.now = datetime(2010, 5, 7, 9, 0, 0, tzinfo=localtz)
        # creates sprint with 20 days, of which 15 are working days
        # This sprint starts at a specific day, which means that it will soon 
        # end before the real now. Other parts of the superclass test 
        # infrastructure don't expec this, which may lead to errors as stuff is 
        # created after the actual sprint has ended.
        self._create_remaining_times(self.now)
    
    def _dates_from_chart(self, param_name='remaining_times'):
        times = self.get_times_from_chart(param_name)
        all_dates = set()
        for time in times:
            all_dates.add(time.date())
        
        return sorted(list(all_dates))
    
    
    def test_weekends_are_hidden(self):
        all_dates = self._dates_from_chart('capacity_data')
        
        self.assert_length(15, all_dates)
        self.assert_contains(date(2010, 5, 7), all_dates)
        # this is actually the monday, shifted to the saturday by the compactor
        self.assert_contains(date(2010, 5, 8), all_dates)
        self.assert_contains((self.sprint.end - timedelta(days=5)).date(), all_dates)
        self.assert_not_contains((self.sprint.end - timedelta(days=4)).date(), all_dates)
    
    def test_sprint_without_team_does_not_hide_any_day(self):
        self.sprint.team = None
        self.sprint.save()
        self._remaining_time(5, self.sprint.end - timedelta(hours=5))
        
        all_dates = self._dates_from_chart('remaining_times')
        self.assert_contains(self.sprint.end.date(), all_dates)
    
    def test_weekend_marker_is_empty_when_hiding_weekends(self):
        all_dates = self._dates_from_chart('weekend_data')
        self.assert_length(0, all_dates)
    
    def test_today_marker_is_empty_when_hiding_today(self):
        member = self.sprint.team.members[0]
        member.capacity = [0] * 7
        member.save()
        
        self.sprint.start = self.yesterday
        self.sprint.end = self.tomorrow
        self.sprint.save()
        
        all_dates = self._dates_from_chart('today_data')
        self.assert_length(0, all_dates)
        
        self.env.config.set(AgiloConfig.AGILO_GENERAL, 'burndown_should_show_working_days_only', False)
        all_dates = self._dates_from_chart('today_data')
        self.assert_length(1, all_dates)
    
    def test_trendline_extends_to_shifted_sprint_end(self):
        all_times = self.get_times_from_chart('trend_data')
        self.assert_length(2, all_times)
        first, last = all_times
        virtual_end = self.sprint.end - timedelta(days=5)
        self.assert_equals(virtual_end, last)


# circle today marker should not be displayed before sprint start
# first tick should not be before sprint start
