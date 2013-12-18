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

from agilo.core import Field, PersistentObject, PersistentObjectModelManager
from agilo.utils import AgiloConfig, Key
from agilo.utils.compat import json
from agilo.utils.days_time import now
from agilo.utils.geometry import Line, Point
from agilo.api.controller import ValuePerTime

__all__ = ['BurndownDataAggregator', 'BurndownDataChange',
           'BurndownDataConfirmCommitment', 'BurndownDataConstants',
           'BurndownTrendLineGenerator']


class BurndownDataConstants(object):
    REMAINING_TIME = Key.REMAINING_TIME
    REMAINING_POINTS = Key.REMAINING_POINTS
    COMPONENT = Key.COMPONENT
    SKIP_AGGREGATION = 'SKIP_AGGREGATION'
    DELTAS_BY_COMPONENT = 'DELTAS_BY_COMPONENT'


# REFACT: do we need to add field for backlog-name so we can identify sprints / milestones with the same name? (perhaps not if burndown can only happen in sprints)
class BurndownDataChange(PersistentObject):
    class Meta(object):
        id = Field(type='integer', primary_key=True, auto_increment=True)
        type = Field(db_name='burndown_type')
        scope = Field()
        when = Field(type='datetime', db_name='timestamp')
        # REFACT: Consider splitting metadata tuple (pair) into two fields:
        # numeric value and actual metadata dict (component, etc)
        value = Field()

    def __repr__(self):
        return '%s(id=%s, type=%s, scope=%s, when=%s, value=%s)' % (self.__class__.__name__, repr(self.id), repr(self.type), repr(self.scope), repr(self.when), repr(self.value))

    @classmethod
    def remaining_entry(cls, env, delta, scope, type, when=None, marker_key=None, marker_value=True):
        if when is None:
            when = now()

        instance = cls(env).update_values(
            scope=scope,
            type=type,
            when=when,
            delta=delta,
        )

        if marker_key is not None:
            instance.update_marker(marker_key, marker_value)

        return instance

    @classmethod
    def remaining_points_entry(cls, env, delta, scope, when=None, marker_key=None, marker_value=True):
        delta = int(delta)
        return BurndownDataChange.remaining_entry(env, delta, scope, BurndownDataConstants.REMAINING_POINTS, when, marker_key, marker_value)

    @classmethod
    def remaining_time_entry(cls, env, delta, scope, when=None, marker_key=None, marker_value=True):
        delta = float(delta)
        return BurndownDataChange.remaining_entry(env, delta, scope, BurndownDataConstants.REMAINING_TIME, when, marker_key, marker_value)

    @classmethod
    def create_aggregation_skip_marker(cls, env, scope, when=None):
        return cls.remaining_time_entry(env, 0, scope, when, BurndownDataConstants.SKIP_AGGREGATION)

    def update_values(self, scope=None, type=None, when=None, delta=None, markers=None):
        if scope: self.scope = scope
        if type: self.type = type
        if when: self.when = when
        if delta is not None: self.set_delta(delta)
        if markers: self.set_markers(markers)
        return self

    def parse_microformat(self):
        if self.value is None:
            return 0, dict()
        microformat = json.loads(self.value)
        if isinstance(microformat, int) or isinstance(microformat, float):
            return microformat, dict()
        elif isinstance(microformat, list):
            return microformat[0], microformat[1]
        else:
            raise ValueError('microformat <%s> not supported' % repr(self.value))

    def serialize_microformat(self, delta, markers=None):
        if markers is not None and len(markers.keys()) != 0:
            self.value = json.dumps([delta, markers])
        else:
            self.value = json.dumps(delta)

    def delta(self):
        return self.parse_microformat()[0]

    def markers(self):
        return self.parse_microformat()[1]

    def set_delta(self, a_delta):
        self.serialize_microformat(a_delta, self.markers())

    def set_markers(self, markers):
        self.serialize_microformat(self.delta(), markers)

    def update_marker(self, key, value):
        markers = self.markers()
        markers[key] = value
        self.set_markers(markers)

    def has_marker(self, marker):
        return marker in self.markers()

    def marker_value(self, marker):
        return self.markers().get(marker)

    def set_component_marker(self, component_name):
        message = 'need to enable both should_reload_burndown_on_filter_change_when_filtering_by_component and backlog_filter_attribute to save burndown data by component'
        assert AgiloConfig(self.env).is_filtered_burndown_enabled(), message

        self.update_marker(BurndownDataConstants.COMPONENT, component_name)

    def value_fields(self):
        "Return fields that are not the primary key"
        return filter(lambda field: field != 'id', self._fields)

    def save(self):
        for attribute_name in self.value_fields():
            value = getattr(self, attribute_name)
            if value is None:
                raise ValueError('Missing value for attribute <%s>' % attribute_name)
        return self.super()


class BurndownDataChangeModelManager(PersistentObjectModelManager):
    model = BurndownDataChange

class BurndownEntry(ValuePerTime):
    remaining_time = property(ValuePerTime._value, ValuePerTime._set_value)

# REFACT: Remove method, use class above
def burndown_entry(when, remaining_time):
    return BurndownEntry(remaining_time, when)


class BurndownDataAggregator(object):

    def __init__(self, env, remaining_field=BurndownDataConstants.REMAINING_TIME):
        self.env = env
        self.changes = None
        self.duration = None
        self.extend_until = None
        self.aggregated_changes = None
        self.filter_by_component = None
        self.remaining_field = remaining_field

    def burndown_data_for_sprint(self, sprint, extend_until=None, filter_by_component=None):
        changes = self.changes_for_sprint(sprint)
        return self.aggregate_changes_with_interval(
            changes, timedelta(hours=1),
            aggregate_until=sprint.start,
            discard_after=sprint.end,
            extend_until=extend_until,
            filter_by_component=filter_by_component)

    def changes_for_sprint(self, sprint):
        sprint_name = sprint.name
        conditions = dict(scope=sprint_name, type=self.remaining_field)
        return BurndownDataChangeModelManager(self.env).select(conditions, order_by=['when', 'id'])

    def aggregate_changes_with_interval(self, changes, duration, aggregate_until=None, discard_after=None, extend_until=None, filter_by_component=None):
        self.changes = changes
        self.duration = duration
        self.aggregate_until = aggregate_until
        self.discard_after = discard_after
        self.extend_until = extend_until
        self.aggregated_changes = []
        self.filter_by_component = filter_by_component

        self._compute_aggregation_for_all_changes()
        return self.aggregated_changes

    def _compute_aggregation_for_all_changes(self):
        self._discard_changes_that_do_not_match_the_filtered_component_if_neccessary()
        self._discard_all_changes_after_sprint_end()

        if self._has_no_entry():
            self.aggregated_changes = []
            return

        self._append_synthetic_burndown_data_if_neccessary()
        self._aggregate_changes_before_sprint_start()

        self.aggregated_changes = [self._first_aggregated_change()]
        if self._has_one_entry():
            return

        self._compute_aggregation()


    def _discard_changes_that_do_not_match_the_filtered_component_if_neccessary(self):
        if not self.filter_by_component:
            return

        if not AgiloConfig(self.env).is_filtered_burndown_enabled():
            raise ValueError("Trying to filter by component %s but burndown filtering is not enabled"
            % self.filter_by_component)

        def has_component(change):
            return change.marker_value(BurndownDataConstants.COMPONENT) == self.filter_by_component\
            or change.has_marker(BurndownDataConstants.DELTAS_BY_COMPONENT)

        self.changes = filter(has_component, self.changes)

    def _has_no_entry(self):
        return len(self.changes) == 0

    def _append_synthetic_burndown_data_if_neccessary(self):
        # REFACT: burndown could be nicer if appending a synthetic change would aggregate 
        # all changes in the hour before that
        # Without swallowing the first entry of course.
        if self.extend_until is None or self.changes[-1].when >= self.extend_until:
            return

        data = BurndownDataChange(self.env)
        data.when = self.extend_until
        data.set_delta(0)
        self.changes.append(data)

    def _discard_all_changes_after_sprint_end(self):
        if self.discard_after is None:
            return

        for index, change in enumerate(list(self.changes)):
            if change.when >= self.discard_after:
                # Kill everything after this point
                self.changes = self.changes[:index]
                break

    def _aggregate_changes_before_sprint_start(self):
        if self.aggregate_until is None:
            return

        changes_before_sprint = filter(lambda change: change.when < self.aggregate_until, self.changes)

        if len(changes_before_sprint) == 0:
            # no changes before aggregate_until
            return

        accumulated_delta = reduce(lambda sum, change: sum + change.delta(), changes_before_sprint, 0)
        synthetic_change = BurndownDataChange(self.env).update_values(when=self.aggregate_until, delta=accumulated_delta)
        self.changes = [synthetic_change] + self.changes[len(changes_before_sprint):]

    def _first_aggregated_change(self):
        delta = self.changes[0].delta()

        should_filter = AgiloConfig(self.env).is_filtered_burndown_enabled()
        is_filtering_by_component = self.filter_by_component
        is_not_component_itself = not self.changes[0].has_marker(BurndownDataConstants.COMPONENT)
        if should_filter and is_filtering_by_component and is_not_component_itself:
            by_component = self.changes[0].marker_value(BurndownDataConstants.DELTAS_BY_COMPONENT) or {}
            delta = by_component.get(self.filter_by_component, 0)

        return burndown_entry(self.changes[0].when, delta)

    def _has_one_entry(self):
        return len(self.changes) == 1

    def _compute_aggregation(self):
        current_remaining_time = self._first_aggregated_change().remaining_time
        for change in self.changes[1:-1]:
            # Whenever a change is found that is at least 1 hour from the last
            # aggregation, start a new aggregation and add the current change
            # as the last point of the closed aggregation window
            # This may disconnect changes that are (almost) at the same
            # time into two different aggregated changes
            current_remaining_time += change.delta()
            if self._should_start_next_aggregation(change):
                self.aggregated_changes.append(burndown_entry(change.when, current_remaining_time))

        final_remaining_time = current_remaining_time + self.changes[-1].delta()
        self.aggregated_changes.append(burndown_entry(self.changes[-1].when, final_remaining_time))

    def _should_start_next_aggregation(self, change):
        if change.has_marker(BurndownDataConstants.SKIP_AGGREGATION):
            return True

        return change.when > self.aggregated_changes[-1].when + self.duration


class BurndownTrendLineGenerator(object):
    """
    Takes an aggregated burndown and a date until the extrapolation should go 
    and computes an extrapolation of the last three days worth of work.
    """

    def __init__(self, reference_interval=None):
        self.reference_interval = reference_interval or timedelta(days=3)

    def calculate(self, actual_burndown, a_datetime):
        if len(actual_burndown) <= 1:
            return []

        reference_burndown = self.find_reference_burndown(actual_burndown)
        current_burndown = actual_burndown[-1]
        reference_point = Point(reference_burndown.when, reference_burndown.remaining_time)
        current_point = Point(current_burndown.when, current_burndown.remaining_time)
        trend_line = Line.from_two_points(reference_point, current_point)
        final_value = trend_line.y_from_x(a_datetime)
        return [current_burndown, burndown_entry(a_datetime, final_value)]

    def find_reference_burndown(self, actual_burndown):
        current_burndown = actual_burndown[-1]

        def is_old_enough(a_burndown):
            return a_burndown.when < current_burndown.when - self.reference_interval

        last_burndown = actual_burndown[-1]
        for burndown in reversed(actual_burndown[:-1]):
            if is_old_enough(burndown):
                return burndown
            last_burndown = burndown
        return last_burndown


class BurndownDataConfirmCommitment(object):
    def __init__(self, env):
        self.env = env
        self.remaining_field = BurndownDataConstants.REMAINING_TIME

    # TODO: if when is given, only take the burndown changes till that time
    def confirm_commitment_for_sprint(self, a_sprint, when=None):
        if AgiloConfig(self.env).is_filtered_burndown_enabled():
            self.aggregate_all_changes_with_deltas_by_components(a_sprint, when=when)
        else:
            self.aggregate_all_changes(a_sprint, when=when)

    def aggregate_all_changes(self, a_sprint, when=None):
        summed = self.sum_remaining_time_for_sprint(a_sprint)
        self.remove_old_changes_for_sprint(a_sprint)
        return self.add_initial_change_for_sprint_with_remaining_time(a_sprint, summed, when=when)

    def aggregate_all_changes_with_deltas_by_components(self, a_sprint, when=None):
        by_components = self.sum_remaining_time_for_sprint_by_component(a_sprint)
        change = self.aggregate_all_changes(a_sprint, when=when)
        change.update_marker(BurndownDataConstants.DELTAS_BY_COMPONENT, by_components)
        change.save()

    def sum_remaining_time_for_sprint(self, a_sprint):
        sum = 0
        for change in self._changes_for_sprint(a_sprint):
            sum += change.delta()
        return sum

    def sum_remaining_time_for_sprint_by_component(self, a_sprint):
        by_component = {}
        for change in self._changes_for_sprint(a_sprint):
            if change.has_marker(BurndownDataConstants.COMPONENT):
                component = change.marker_value(BurndownDataConstants.COMPONENT)
                by_component[component] = by_component.get(component, 0) + change.delta()
            elif change.has_marker(BurndownDataConstants.DELTAS_BY_COMPONENT):
                deltas_by_component = change.marker_value(BurndownDataConstants.DELTAS_BY_COMPONENT)
                for component, value in deltas_by_component.items():
                    by_component.setdefault(component, 0)
                    by_component[component] += value

        return by_component

    def remove_old_changes_for_sprint(self, a_sprint):
        changes = self._changes_for_sprint(a_sprint)
        for change in changes:
            change.delete()

    def add_initial_change_for_sprint_with_remaining_time(self, a_sprint, a_delta, when=None):
        change = BurndownDataChange(self.env)
        change.set_delta(a_delta)
        change.type = self.remaining_field
        change.scope = a_sprint.name
        change.when = when or now()
        change.save()
        return change

    def _changes_for_sprint(self, a_sprint):
        aggregator = BurndownDataAggregator(self.env)
        return aggregator.changes_for_sprint(a_sprint)




        # TODO switch to BurndownDataConstants.COMPONENT for everywhere?
        #  consider changing the marker to COMPONENT_MARKER so there is no confusion