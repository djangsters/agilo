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

from datetime import datetime, timedelta
from math import ceil

from trac.core import Component, implements
from trac.util.datefmt import to_timestamp, utc

from agilo.api import ValueObject
from agilo.charts.api import IAgiloWidgetGenerator
from agilo.scrum.backlog.controller import BacklogController
from agilo.scrum.burndown.model import BurndownTrendLineGenerator, BurndownDataConstants
from agilo.scrum.charts import ChartType, ScrumFlotChartWidget
from agilo.scrum.team.controller import TeamController
from agilo.utils import BacklogType
from agilo.utils.days_time import now, midnight_with_utc_shift, unicode_strftime,\
    date_to_datetime, midnight
from agilo.utils.geometry import Line
from agilo.scrum.sprint.controller import SprintController
from agilo.api.controller import ValuePerTime
from agilo.utils.config import AgiloConfig

__all__ = ["PointBurndownChartGenerator", "BurndownChartGenerator"]


class PointBurndownChartGenerator(Component):

    implements(IAgiloWidgetGenerator)

    name = ChartType.POINT_BURNDOWN

    def can_generate_widget(self, name):
        return (name == self.name)

    def get_cache_components(self, keys):
        return ('name', 'sprint_name', 'filter_by')

    def generate_widget(self, name, **kwargs):
        burndown_widget = BurndownWidget(self.env, template_filename='scrum/backlog/templates/agilo_point_burndown_chart.html')
        burndown_widget.update_data(remaining_field=BurndownDataConstants.REMAINING_POINTS)
        if 'filter_by' in kwargs:
            burndown_widget.update_data(filter_by=kwargs['filter_by'])
        if 'sprint_name' in kwargs:
            if 'cached_data' in kwargs:
                burndown_widget.update_data(cached_data=kwargs['cached_data'])
            sprint_name = kwargs.get('sprint_name')
            burndown_widget.populate_with_sprint_data(sprint_name)
        return burndown_widget

    def get_backlog_information(self):
        # Charts are a layer above the burndown so this module must not import
        # agilo.scrum.backlog globally
        return {self.name: (BacklogType.SPRINT,)}

class BurndownChartGenerator(Component):
    
    implements(IAgiloWidgetGenerator)
    
    name = ChartType.BURNDOWN
    
    def can_generate_widget(self, name):
        return (name == self.name)
    
    def get_cache_components(self, keys):
        return ('name', 'sprint_name', 'filter_by')
    
    def generate_widget(self, name, **kwargs):
        burndown_widget = BurndownWidget(self.env)
        burndown_widget.update_data(remaining_field=BurndownDataConstants.REMAINING_TIME)
        if 'filter_by' in kwargs:
            burndown_widget.update_data(filter_by=kwargs['filter_by'])
        if 'sprint_name' in kwargs:
            if 'cached_data' in kwargs:
                burndown_widget.update_data(cached_data=kwargs['cached_data'])
            sprint_name = kwargs.get('sprint_name')
            burndown_widget.populate_with_sprint_data(sprint_name)
        return burndown_widget
    
    def get_backlog_information(self):
        # Charts are a layer above the burndown so this module must not import
        # agilo.scrum.backlog globally
        return {self.name: (BacklogType.SPRINT,)}


# ----------------------------------------------------------------------------
# Calculation for 

def _entries_from_timeseries_nearest_to(timeseries, a_datetime):
    before = after = None
    for data in timeseries:
        if data[0] <= a_datetime:
            before = data
        if data[0] >= a_datetime:
            after = data
            break
    return (before, after)


def _shorten_series_to_start_from_day(daily_timeseries, a_datetime):
    for i, capacity in enumerate(daily_timeseries):
        # half a day + buffer for summer-/ winter-time changes
        if abs(capacity[0] - a_datetime) < timedelta(hours=14):
            return daily_timeseries[i:]
    return daily_timeseries

def _shorten_capacities_to_start_from_remaining_time_entry(capacities_series, first_remaining_time):
    shortened_capacities = _shorten_series_to_start_from_day(capacities_series, first_remaining_time.when)
    # synthesize first ideal burndown entry at the time of the first remaining_time
    before, after = _entries_from_timeseries_nearest_to(capacities_series, first_remaining_time.when)
    if before is not None and after is not None:
        interpolated_start_capacity = Line.from_two_tupples(before, after).y_from_x(first_remaining_time.when)
        shortened_capacities = [(first_remaining_time.when, interpolated_start_capacity)] + shortened_capacities[1:]
    return shortened_capacities
    

# REFACT: consider to inline into charts.py, having it outside doesn't make reading the code easier...
def calculate_ideal_burndown(utc_capacity_data, first_remaining_time, sprint):
    """Calculates the data for the ideal burndown, based on the actual
    capacity for the sprint, given the initial team commitment."""
    assert len(utc_capacity_data) > 0 and utc_capacity_data[0][1] != 0, \
        "Please provide a non empty list for capacity_data"
    shortened_capacities = _shorten_capacities_to_start_from_remaining_time_entry(utc_capacity_data, first_remaining_time)
    first_capacity = shortened_capacities[0][1]
    ideal_burndown_proportion = 0;
    if first_capacity != 0:
        ideal_burndown_proportion = 1 + (first_remaining_time.remaining_time - first_capacity) / first_capacity

    def ideal_burndown_from_capacity(capacity_entry):
        when, capacity = capacity_entry
        return (when, ideal_burndown_proportion * capacity)
    return map(ideal_burndown_from_capacity, shortened_capacities)

# ------------------------------------------------------------------------------


# Usage:
# from agilo.utils.widgets import BurndownWidget
# burndown = BurndownWidget(self.env)
# ${burndown.prepare_renderung(req)}
# ${burndown.display()}

class BurndownWidget(ScrumFlotChartWidget):
    """Burndown chart widget which generates HTML and JS code so that Flot
    can generate a burndown chart for the sprint including actual data, ideal 
    burndown and moving average."""
    
    default_width =  750
    default_height = 350
    
    GOOD_COLOR = '#94d31a'
    WARNING_COLOR = '#e0e63d'
    BAD_COLOR = '#f35e5e'
    
    def __init__(self, env, **kwargs):
        template_filename = kwargs.get('template_filename') or 'scrum/backlog/templates/agilo_burndown_chart.html'
        self._define_chart_resources(env, template_filename, kwargs)
        kwargs['scripts'] = ('agilo/js/burndown.js',)
        self.super(env, template_filename, **kwargs)
        self.t_controller = TeamController(self.env)
        self.sp_controller = SprintController(self.env)
        self.b_controller = BacklogController(self.env)
        self.burndown_data = dict()
    
    def json_data(self):
        return self.burndown_data
    
    def populate_with_sprint_data(self, sprint_name):
        # REFACT: migrate to member variable?
        sprint = self._load_sprint(sprint_name)
        if sprint is None:
            return
        
        self.data.update(dict(
            # REFACT: consider to remove these, we don't really need them cached
            sprint_start=sprint.start,
            sprint_end=sprint.end,
        ))
    
    # REFACT: We should remove the utc_ variants from the data dict so that 
    # there is no confusion which item to use. However we need to check that his
    # does not breaks caching... (or remove the caching altogether)
    def prepare_rendering(self, req):
        self.super()
        self._populate_with_sprint_and_viewer_timezone(self.data['sprint_name'], req.tz)
        self._convert_utc_times_to_local_timezone(req.tz)
        self._add_jsonized_plot_data()
    
    def _populate_with_sprint_and_viewer_timezone(self, sprint_name, viewer_timezone):
        sprint = self._load_sprint(sprint_name, native=True)
        if sprint is None:
            return
        
        days_to_remove = self._days_to_remove_from_burndown(sprint, viewer_timezone)
        container = ValueObject(
            remaining_times = self._get_remaining_time_series(sprint_name),
            capacity_data = self._get_capacity(sprint, viewer_timezone, self._is_filtered_backlog(), self._is_point_burndown()),
            ticks = self._calculate_ticks(sprint, viewer_timezone, days_to_remove),
            weekend_data = self._get_weekend_starts(sprint.start, sprint.end, viewer_timezone),
            today_data = self._get_today_data(sprint.start, sprint.end, viewer_timezone),
        )
        self._compact_values_by_removing_days(container, days_to_remove)

        days_without_capacity_to_hide = ValuesPerTimeCompactor.final_shift(days_to_remove)
        container.trend_data = self._trend_line(container.remaining_times, sprint.end - days_without_capacity_to_hide)

        # REFACT: put container directly into data and then unsmart the values in the utc shifting method
        utc_remaining_times = self._smart_to_tuple_series(container.remaining_times)
        utc_capacity_data = self._smart_to_tuple_series(container.capacity_data)
        # need that in non utc form too to compact
        first_remaining_time = self._first_remaining_time(container.remaining_times)
        utc_ideal_data = self._calculate_ideal_burndown(utc_capacity_data, first_remaining_time, sprint)
        utc_trend_data = self._smart_to_tuple_series(container.trend_data)
        utc_ticks = self._smart_to_tuple_series(container.ticks)
        utc_weekend_data = self._smart_to_tuple_series(container.weekend_data)
        utc_today_data = self._smart_to_tuple_series(container.today_data)
        
        self.data.update(dict(
            utc_remaining_times=utc_remaining_times,
            utc_ideal_data=utc_ideal_data,
            utc_capacity_data=utc_capacity_data,
            utc_trend_data=utc_trend_data,
            utc_ticks=utc_ticks,
            utc_weekend_data=utc_weekend_data,
            utc_today_data=utc_today_data,
        ))
        self.burndown_data.update(dict(
            today_color=self._today_color(sprint, container.remaining_times, utc_ideal_data),
        ))
    
    def _days_to_remove_from_burndown(self, sprint, viewer_timezone):
        if not AgiloConfig(self.env).burndown_should_show_working_days_only:
            return []
        if sprint.team is None:
            return []
        days_to_remove = sprint.team.capacity(viewer_timezone).days_without_capacity_in_interval(sprint.start, sprint.end)
        
        return days_to_remove
    
    def _add_jsonized_plot_data(self):
        from agilo.utils.compat import json
        self.data['jsonized_burndown_values'] = json.dumps(self.data_as_json())
    
    def _datetime_to_js_milliseconds(self, datetime_date, tz):
        """Convert a datetime into milliseconds which are directly usable by 
        flot"""
        # Flot always uses UTC. In order to display the data with the correct 
        # days, we have to move the data to UTC
        # FIXME: we no longer use flott in date mode, so this is not neccessary anymore
        # Perhaps better do the serialization in the json interface
        # Probably we still need this, since js cannot read times with timezones
        
        # "Normally you want the timestamps to be displayed according to a
        # certain time zone, usually the time zone in which the data has been
        # produced. However, Flot always displays timestamps according to UTC.
        # It has to as the only alternative with core Javascript is to interpret
        # the timestamps according to the time zone that the visitor is in,
        # which means that the ticks will shift unpredictably with the time zone
        # and daylight savings of each visitor.
        fake_utc_datetime = datetime_date.astimezone(tz).replace(tzinfo=utc)
        seconds_since_epoch = to_timestamp(fake_utc_datetime)
        milliseconds_since_epoch = seconds_since_epoch * 1000
        return milliseconds_since_epoch
    
    def _convert_to_utc_timeseries(self, start, end, input_data, now=None):
        """Takes a list of input_data and converts it into a list of tuples 
        (datetime in UTC, data). It returns a tuple every 24h from the sprint
        start datetime."""
        utc_data = []
        stop = False
        current_date = start
        for data in input_data:
            if now is not None and current_date > now:
                current_date = now
                # FIXME: (AT) This is an hack to make sure the last value is 
                # always the last one, we need to send the request timezone 
                # through to get the sprint days shifted to the current timezone.
                data = input_data[-1]
                # AT: We need to break after the append, we are already at now
                # the last data, if available would be the same exact value as
                # now. This happens in tests because the sprint is created in
                # the same microsecond as the now will be calculated adding two
                # values at last
                stop = True
            elif current_date > end:
                current_date = end
            # AT: the dates should be already UTC, but you never know
            day_data = (current_date.astimezone(utc), data)
            utc_data.append(day_data)
            if stop:
                break
            current_date += timedelta(days=1)
        return utc_data
    
    def _today_color(self, sprint, actual_data, ideal_data):
        today_color = self.GOOD_COLOR
        if not sprint.is_currently_running:
            return today_color
        # ideal_data can be empty if no actual data exists (e.g. sprint not start yet)
        if len(ideal_data) == 0 or len(actual_data) == 0:
            return today_color
        
        current_actual_burndown = actual_data[-1]
        current_remaining_time = current_actual_burndown.remaining_time
        ideal_remaining_time = self._calculate_ideal_burndown_at_datetime(ideal_data, current_actual_burndown.when)
        
        if (ideal_remaining_time == 0) and (current_remaining_time == 0):
            return today_color
        elif (ideal_remaining_time == 0) \
            or (current_remaining_time / ideal_remaining_time > 1.3):
            return self.BAD_COLOR
        elif current_remaining_time / ideal_remaining_time > 1.1:
            return self.WARNING_COLOR
        return today_color
    
    def _calculate_ticks(self, sprint, viewer_timezone, days_to_remove):
        generator = TickGenerator.for_sprint(sprint, viewer_timezone, days_to_remove)
        return generator.generate_tick_labels()
    
    def _get_capacity_data(self, sprint, viewer_timezone):
        """
        Returns the capacity data for this sprint in the form of a list.
        Capacity per day is calculated as the whole team capacity that day,
        removed a proportional amount for the contingent set by the team in 
        this sprint.
        """
        if sprint.team is None:
            return []
        
        return sprint.team.capacity(viewer_timezone).summed_hourly_capacities_in_sprint(sprint)
    
    def _get_capacity(self, sprint, viewer_timezone, is_filtered_burndown, is_point_burndown=False):
        if is_filtered_burndown or is_point_burndown:
            return []
        return self._get_capacity_data(sprint, viewer_timezone)
    
    def _calculate_ideal_burndown(self, utc_capacity_data, first_remaining_time, sprint):
        has_remaining_time = (first_remaining_time is not None)
        has_capacity_data = (len(utc_capacity_data) > 0 and utc_capacity_data[0][1] != 0)
        if has_remaining_time and has_capacity_data:
            return calculate_ideal_burndown(utc_capacity_data, first_remaining_time, sprint)
        elif has_remaining_time:
            # Just let flot draw a straight line...
            return [(first_remaining_time.when, first_remaining_time.remaining_time), (sprint.end, 0)]
        else:
            return []
    
    def _calculate_ideal_burndown_at_datetime(self, ideal_data, a_datetime):
        before, after = _entries_from_timeseries_nearest_to(ideal_data, a_datetime)
        if before is None or after is None:
            return 0
        
        return Line.from_two_tupples(before, after).y_from_x(a_datetime)
    
    def _get_remaining_time_series(self, sprint_name):
        cmd_rem_times = SprintController.GetActualBurndownCommand(self.env,
            sprint=sprint_name,  filter_by_component=self.data.get('filter_by'),
            remaining_field=self.data.get('remaining_field'))
        return self.sp_controller.process_command(cmd_rem_times)
    
    def _first_remaining_time(self, actual_data):
        if len(actual_data) > 0:
            return actual_data[0]
        return None
    
    def _trend_line(self, actual_data, end):
        return BurndownTrendLineGenerator().calculate(actual_data, end)
    
    def _smart_to_tuple_series(self, a_series):
        return [(item.when, item.value) for item in a_series]
    
    def _is_filtered_backlog(self):
        return self.data.get('filter_by') is not None

    def _is_point_burndown(self):
        return self.data.get('remaining_field') == BurndownDataConstants.REMAINING_POINTS

    def _convert_to_flot_timeseries(self, data, tz):
        flot_data = []
        for point_in_time, value in data:
            flot_milliseconds = self._datetime_to_js_milliseconds(point_in_time, tz)
            if isinstance(value, datetime):
                value = self._datetime_to_js_milliseconds(value, tz)
            flot_data.append((flot_milliseconds, value))
        return flot_data
    
    def _get_weekend_starts(self, start, end, tz):
        weekend_data = []
        # The start is stored in UTC but the weekend should be drawn
        # localized
        day = start.astimezone(tz)
        while day < end:
            if day.isoweekday() in (6, 7):
                weekend_start = midnight_with_utc_shift(day)
                weekend_data.append(DayMarker(weekend_start))
            day += timedelta(days=1)
        return weekend_data
    
    def _get_today_data(self, start, end, tz):
        if not (start <= now(tz) <= end):
            return []
        
        # Now is already calculated in the given timezone so we have to get
        # the midnight in that timezone, shifted to UTC time
        # TODO: this is being shifted later, does midnight suffice?
        today_midnight = midnight_with_utc_shift(now(tz))
        return [DayMarker(today_midnight)]
    
    def _convert_utc_times_to_local_timezone(self, tz):
        for key in self.data.keys():
            if key.startswith('utc_'):
                new_key = key[len('utc_'):]
                flot_data = self._convert_to_flot_timeseries(self.data[key], tz)
                self.burndown_data[new_key] = flot_data
    
    def _compact_values_by_removing_days(self, values, days_to_remove):
        for key, value in values.items():
            compactor = ValuesPerTimeCompactor(value, days_to_remove)
            values[key] = compactor.compact_values()
    

class LabeledTick(ValuePerTime):
    
    def __init__(self, when):
        value = self._tick_label(when)
        when = date_to_datetime(when)
        self.super(value, when)
    
    def _tick_label(self, when):
        return unicode_strftime(when, '%x')
    
    label = property(ValuePerTime._value, ValuePerTime._set_value)

class DayMarker(ValuePerTime):
    
    def __init__(self, when):
        self.when = date_to_datetime(when)
    
    @property
    def value(self):
        return self.when + timedelta(days=1)

class TickGenerator(object):
    """
    Generates ticks on midnight in the viewer's timezone and tries to
    get as close to 10 ticks as possible.
    Will not generate a tick on the end of the last day
    """
    
    MAXIMUM_NUMBER_OF_TICKS = 10
    
    # -------------------------------------------------------------------------
    # PUBLIC METHODS
    # -------------------------------------------------------------------------
    
    def __init__(self, start, end, viewer_timezone, days_to_remove=()):
        self.start = start
        self.end = end
        self.days_per_tick = 1
        self.viewer_timezone = viewer_timezone
        self.days_to_remove = days_to_remove
        self._calculate_number_and_delta_of_ticks()
    
    # REFACT: consider to rename to for_sprint_with_timezone
    @classmethod
    def for_sprint(cls, sprint, viewer_timezone, days_to_remove=()):
        return TickGenerator(sprint.start, sprint.end, viewer_timezone, days_to_remove)
    
    def generate_tick_labels(self):
        return [LabeledTick(when) for when in self.generate_ticks()]
    
    def generate_ticks(self):
        def all_ticks():
            current_tick = self._normalized_start()
            while current_tick < self.end:
                yield current_tick
                current_tick = current_tick + timedelta(days=1)
        
        def possible_ticks(ticks):
            for tick in ticks:
                if tick not in self.days_to_remove:
                    yield tick
        
        def real_ticks(ticks):
            for i, tick in enumerate(ticks):
                if i % self.days_per_tick == 0:
                    yield tick
        
        return list(real_ticks(possible_ticks(all_ticks())))
    
    # -------------------------------------------------------------------------
    # PRIVATE METHODS
    # -------------------------------------------------------------------------
    
    def _normalized_start(self):
        normalized_start = self.start.astimezone(self.viewer_timezone)
        normalized_start = midnight(normalized_start)
        if normalized_start < self.start:
            normalized_start = normalized_start + timedelta(days=1)
        return normalized_start
    
    def _ensure_is_date(self, date_or_datetime):
        if isinstance(date_or_datetime, datetime):
            return date_or_datetime.date()
        else:
            return date_or_datetime
    
    def _total_number_of_days(self):
        return (self.end - self.start).days - len(self.days_to_remove)
    
    def _calculate_number_and_delta_of_ticks(self):
        if self._total_number_of_days() > self.MAXIMUM_NUMBER_OF_TICKS:
            ideal_delta_between_ticks = self._total_number_of_days() / float(self.MAXIMUM_NUMBER_OF_TICKS)
            self.days_per_tick = ceil(ideal_delta_between_ticks)
    

class ValuesPerTimeCompactor(object):
    
    @classmethod
    def final_shift(cls, days_to_remove):
        compactor = cls([], days_to_remove)
        compactor.compact_values()
        return compactor.delta_of_removed_days
    
    def __init__(self, timed_values, days_to_remove):
        self.days_to_remove = sorted(days_to_remove)
        self.remaining_values = sorted(timed_values, key=lambda value: value.when)
        self.values_to_keep = []
        self.delta_of_removed_days = timedelta(0)
    
    def compact_values(self):
        for day_to_remove in self.days_to_remove:
            self._keep_values_before(day_to_remove)
            self._remove_values_within_day(day_to_remove)
            self.delta_of_removed_days = self.delta_of_removed_days + timedelta(days=1)
        
        for value in self.remaining_values:
            self._shift_and_append_value(value)
        
        return self.values_to_keep
    
    def _keep_values_before(self, limit_day):
        is_value_before_limit_day = lambda value: value.when < limit_day
        selected_values = self._select_from_remaining_values(is_value_before_limit_day)
        for value in selected_values:
            self._shift_and_append_value(value)
    
    def _remove_values_within_day(self, limit_day):
        def is_value_on_limit_day(value):
            return limit_day <= value.when < limit_day + timedelta(days=1)
        self._select_from_remaining_values(is_value_on_limit_day)
    
    def _select_from_remaining_values(self, should_select_value):
        selected_values =[]
        while len(self.remaining_values) > 0 and should_select_value(self.remaining_values[0]):
            selected_values.append(self.remaining_values[0])
            del self.remaining_values[0]
        return selected_values
    
    def _shift_and_append_value(self, timed_value):
        timed_value.when = timed_value.when - self.delta_of_removed_days
        self.values_to_keep.append(timed_value)
