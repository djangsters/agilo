# -*- encoding: utf-8 -*-
#   Copyright 2010 Agile42 GmbH, Berlin (Germany)
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

from datetime import timedelta

from agilo.scrum.burndown.model import (burndown_entry, BurndownDataAggregator, 
    BurndownDataChange, BurndownDataConstants)
from agilo.test import AgiloTestCase
from agilo.utils.days_time import now
from agilo.utils import Key


class TimeAggregationTest(AgiloTestCase):
    
    def setUp(self):
        self.super()
        self.sprint = self.teh.create_sprint(self.sprint_name())
        self.aggregator = BurndownDataAggregator(self.env)
    
    def change(self, time_delta, how_much, type=None, scope=None, marker_key=None, marker_value=True):
        instance = BurndownDataChange(self.env).update_values(
            type= type or BurndownDataConstants.REMAINING_TIME,
            scope=getattr(scope, 'name', self.sprint.name),
            when= now() + time_delta,
            delta=how_much,
        )
        if marker_key is not None:
            instance.update_marker(marker_key, marker_value)
        return instance
    
    def fixture(self):
        return [
            self.change(timedelta(hours=-3), -5),
            self.change(timedelta(hours=-1), -3),
            self.change(timedelta(hours=-5), 10),
        ]
    
    def aggregate(self, changes, interval=timedelta(hours=2), aggregate_until=None, discard_after=None, extend_until=None, filter_by_component=None):
        return self.aggregator.aggregate_changes_with_interval(changes, duration=interval, 
            aggregate_until=aggregate_until, discard_after=discard_after, extend_until=extend_until,
            filter_by_component=filter_by_component)
    
    
    
    def test_can_aggregate_zero_changes(self):
        self.assert_equals([], self.aggregate([]))
    
    def test_can_aggregate_one_change(self):
        first = self.change(timedelta(hours=0), 10)
        self.assert_equals([burndown_entry(first.when, first.delta())], self.aggregate([first]))
    
    def test_just_transforms_to_changes_if_no_aggregation_is_neccessary(self):
        first = self.change(timedelta(hours=0), 0)
        second = self.change(timedelta(hours=10), 6)
        aggregated = self.aggregate([first, second], interval=timedelta(hours=1))
        self.assert_length(2, aggregated)
        self.assert_equals(burndown_entry(first.when, first.delta()), aggregated[0])
        self.assert_equals(burndown_entry(second.when, first.delta() + second.delta()), aggregated[1])
    
    def test_can_add_up_durations(self):
        first = self.change(timedelta(hours=0), 10)
        second = self.change(timedelta(hours=10), 10)
        aggregated = self.aggregate([first, second], interval=timedelta(hours=1))
        self.assert_length(2, aggregated)
        self.assert_equals(burndown_entry(first.when, 10), aggregated[0])
        self.assert_equals(burndown_entry(second.when, 20), aggregated[1])
    
    def test_does_not_discard_start_or_end_value_even_if_interval_is_bigger_than_their_distance(self):
        first = self.change(timedelta(hours=0), 10)
        second = self.change(timedelta(hours=1), 10)
        aggregated = self.aggregate([first, second])
        self.assert_length(2, aggregated)
        self.assert_equals(burndown_entry(first.when, 10), aggregated[0])
        self.assert_equals(burndown_entry(second.when, 20), aggregated[1])
    
    def test_can_aggregate_multiple_changes_in_interval(self):
        first = self.change(timedelta(hours=0), 10)
        second = self.change(timedelta(hours=1), 10)
        third = self.change(timedelta(hours=2), 10)
        aggregated = self.aggregate([first, second, third])
        self.assert_length(2, aggregated)
        self.assert_equals(burndown_entry(first.when, 10), aggregated[0])
        self.assert_equals(burndown_entry(third.when, 30), aggregated[1])
    
    def test_can_extend_series_till_specified_time(self):
        first = self.change(timedelta(hours=-10), 10)
        end = now()
        aggregated = self.aggregate([first], extend_until=end)
        self.assert_equals([burndown_entry(first.when, first.delta()), burndown_entry(end, first.delta())], aggregated)
    
    def test_first_entry_is_always_at_start_of_sprint(self):
        change = self.change(timedelta(days=-100), 10)
        actual = self.aggregate([change], aggregate_until=self.sprint.start)
        self.assert_time_equals(self.sprint.start, actual[0].when)
    
    def test_will_aggregate_changes_before_sprint_start_to_sprint_start(self):
        first = self.change(timedelta(days=-100), 15)
        second = self.change(timedelta(days=-100), 23)
        actual = self.aggregate([first, second], aggregate_until=self.sprint.start)
        self.assert_equals(15+23, actual[0].remaining_time)
    
    def test_will_disregard_all_burndown_changes_after_sprint_end(self):
        change = self.change(timedelta(days=100), 200)
        self.assert_length(0, self.aggregate([change], discard_after=self.sprint.end))
    
    def test_changes_after_sprint_end_have_no_influence_on_burndown_chart_in_sprint(self):
        changes = [
            self.change(timedelta(), 10),
            self.change(timedelta(days=1), 10),
            self.change(timedelta(days=2), 10),
            self.change(timedelta(days=100), 1000)
        ]
        aggregated = self.aggregate(changes, discard_after=self.sprint.end, extend_until=self.sprint.end)
        self.assert_time_equals(changes[0].when, aggregated[0].when)
        self.assert_time_equals(self.sprint.end, aggregated[-1].when)
        self.assert_equals(30, aggregated[-1].remaining_time)
    
    def test_one_change_and_time_extension(self):
        self.change(timedelta(days=-20), 12).save()
        until = now() + timedelta(days=10)
        aggregated = self.aggregator.burndown_data_for_sprint(self.sprint, extend_until=until)
        self.assert_length(2, aggregated)
    
    def test_does_not_count_the_last_entry_twice(self):
        changes = [
            self.change(timedelta(), 0),
            self.change(timedelta(), 0),
            self.change(timedelta(), 0),
            self.change(timedelta(), 10),
        ]
        
        aggregated = self.aggregate(changes)
        self.assert_equals(0, aggregated[-2].remaining_time)
        self.assert_equals(10, aggregated[-1].remaining_time)
    
    
    # --------------------------------------------------------------------------------
    # Not aggregating over markers
    
    def test_can_have_normal_intersection_of_entries(self):
        changes = [
            self.change(timedelta(minutes=-1), 10),
            BurndownDataChange.create_aggregation_skip_marker(self.env, self.sprint_name()),
            self.change(timedelta(), 10),
            BurndownDataChange.create_aggregation_skip_marker(self.env, self.sprint_name()),
            self.change(timedelta(minutes=1), 10),
        ]
        aggregated = self.aggregate(changes)
        self.assert_length(4, aggregated)
        self.assert_equals(10, aggregated[0].remaining_time)
        self.assert_equals(10, aggregated[1].remaining_time)
        self.assert_equals(20, aggregated[2].remaining_time) # this is the jump
        self.assert_equals(30, aggregated[3].remaining_time)
    
    def test_only_changes_surrounded_with_markers_(self):
        changes = [
            BurndownDataChange.create_aggregation_skip_marker(self.env, self.sprint_name()),
            self.change(timedelta(), 10),
            self.change(timedelta(), 10),
            self.change(timedelta(), 10),
            BurndownDataChange.create_aggregation_skip_marker(self.env, self.sprint_name()),
        ]
        aggregated = self.aggregate(changes, interval=timedelta(hours=1))
        self.assert_length(2, aggregated)
        self.assert_equals(0, aggregated[0].remaining_time)
        self.assert_equals(30, aggregated[1].remaining_time)
    
    def test_can_add_additional_points_when_agregation_is_disabled_with_marker(self):
        changes = [
            self.change(timedelta(minutes=-30), 0),
            self.change(timedelta(minutes=-1), 10),
            BurndownDataChange.create_aggregation_skip_marker(self.env, self.sprint_name()),
            self.change(timedelta(minutes=1), 10),
            self.change(timedelta(minutes=30), 10),
        ]
        aggregated = self.aggregate(changes)
        self.assert_length(3, aggregated)
        self.assert_equals(0, aggregated[0].remaining_time)
        self.assert_equals(10, aggregated[1].remaining_time)
        self.assert_equals(30, aggregated[2].remaining_time)
    
    def test_can_have_skip_marker_as_first_entry(self):
        changes = [
            BurndownDataChange.create_aggregation_skip_marker(self.env, self.sprint_name()),
            self.change(timedelta(minutes=1), 10),
            self.change(timedelta(minutes=30), 10),
        ]
        aggregated = self.aggregate(changes)
        self.assert_length(2, aggregated)
        self.assert_equals(0, aggregated[0].remaining_time)
        self.assert_equals(20, aggregated[1].remaining_time)
    
    def test_can_have_two_markers(self):
        changes = [
            BurndownDataChange.create_aggregation_skip_marker(self.env, self.sprint_name()),
            BurndownDataChange.create_aggregation_skip_marker(self.env, self.sprint_name()),
        ]
        aggregated = self.aggregate(changes, interval=timedelta(hours=1))
        self.assert_length(2, aggregated)
        self.assert_equals(0, aggregated[0].remaining_time)
        self.assert_equals(0, aggregated[1].remaining_time)
    
    # --------------------------------------------------------------------------
    # filter by component
    
    def _generate_changes_with_components(self):
        self.teh.enable_burndown_filter()
        changes = [
            self.change(timedelta(hours=-10), 10),
            self.change(timedelta(hours=-5), 10),
            self.change(timedelta(), 5, marker_key=Key.COMPONENT, marker_value='fnord'),
            self.change(timedelta(), 8, marker_key=Key.COMPONENT, marker_value='foobardibub'),
        ]
        return changes
    
    def test_can_filter_by_component(self):
        changes = self._generate_changes_with_components()
        aggregated = self.aggregate(changes, filter_by_component='fnord')
        self.assert_length(1, aggregated)
        self.assert_equals(5, aggregated[0].remaining_time)
    
    def test_can_see_all_changes_if_filtering_is_enabled_but_not_selected(self):
        changes = self._generate_changes_with_components()
        aggregated = self.aggregate(changes)
        self.assert_length(4, aggregated)
    
    def test_can_see_all_changes_if_filtering_and_filter_is_empty(self):
        changes = self._generate_changes_with_components()
        aggregated = self.aggregate(changes, filter_by_component='')
        self.assert_length(4, aggregated)
    
    def test_throws_if_filtering_is_enabled_but_preferences_are_disabled(self):
        self.assert_raises(ValueError, lambda: self.aggregate([], filter_by_component='fnord'))
    
    
    # --------------------------------------------------------------------------
    # selecting db objects
    
    def test_can_select_changes(self):
        map(lambda change: change.save(), self.fixture())
        changes = self.aggregator.changes_for_sprint(self.sprint)
        self.assert_length(3, changes)
    
    def test_will_only_return_changes_for_sprint(self):
        other_sprint = self.teh.create_sprint('Fnord')
        map(lambda change: change.save(), self.fixture())
        self.change(timedelta(hours=2), 3000, scope=other_sprint).save()
        changes = self.aggregator.changes_for_sprint(self.sprint)
        self.assert_length(3, changes)
    
    def test_will_only_return_changes_for_specific_key(self):
        map(lambda change: change.save(), self.fixture())
        self.change(timedelta(hours=2), 3000, type='foo').save()
        changes = self.aggregator.changes_for_sprint(self.sprint)
        self.assert_length(3, changes)
    
    def test_return_changes_ordered_by_time(self):
        map(lambda change: change.save(), self.fixture())
        changes = self.aggregator.changes_for_sprint(self.sprint)
        self.assert_larger_than(changes[1].when, changes[0].when)
        self.assert_larger_than(changes[2].when, changes[1].when)
    
    # TODO: Check sprint start - confirm commitment
