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

from datetime import timedelta, datetime
from trac.util.datefmt import get_timezone, localtz

from agilo.test import AgiloTestCase
from agilo.utils.days_time import now, midnight
from agilo.scrum.burndown.charts import TickGenerator


class TimeAggregationTest(AgiloTestCase):
    
    now = now()
    today = midnight(now)
    one_week_ago = today - timedelta(days=7)
    yesterday = today - timedelta(days=1)
    tomorrow = today + timedelta(days=1)
    
    def _generate_ticks_in_interval(self, start, end, viewer_timezone=localtz, days_to_remove=()):
        return TickGenerator(start, end, viewer_timezone, days_to_remove=days_to_remove).generate_ticks()
    
    def test_can_generate_ticks_for_one_week(self):
        ticks = self._generate_ticks_in_interval(self.one_week_ago, self.now)
        self.assert_length(8, ticks)
        for number_of_day in range(0, 8):
            self.assert_equals(ticks[number_of_day], self.one_week_ago + timedelta(days=number_of_day))
    
    def test_can_generate_ticks_for_one_day(self):
        ticks = self._generate_ticks_in_interval(self.yesterday, self.now)
        self.assert_length(2, ticks)
        for number_of_day in range(0, 2):
            self.assert_equals(ticks[number_of_day], self.yesterday + timedelta(days=number_of_day))
    
    def test_generate_no_ticks_for_negative_timeframe(self):
        ticks = self._generate_ticks_in_interval(self.now, self.yesterday)
        self.assert_length(0, ticks)
    
    def test_can_generate_ticks_for_two_weeks(self):
        two_weeks_ago = self.today - timedelta(days=14)
        ticks = self._generate_ticks_in_interval(two_weeks_ago, self.now)
        self.assert_length(8, ticks)
        for number_of_day in range(0, 8):
            self.assert_equals(ticks[number_of_day], two_weeks_ago + timedelta(days=2*number_of_day))
    
    def test_can_generate_ticks_for_sprint(self):
        self.teh.disable_sprint_date_normalization()
        sprint = self.teh.create_sprint('fnord', start=self.now, duration=4)
        ticks = TickGenerator.for_sprint(sprint, localtz).generate_ticks()
        self.assert_length(3, ticks)
        self.assert_equals(ticks[0].date(), sprint.start.date() + timedelta(days=1))
        self.assert_equals(ticks[-1].date(), sprint.end.date())
    
    def test_can_generate_tick_labels(self):
        some_friday = datetime(day=30, month=4, year=2010, tzinfo=localtz)
        ticks = TickGenerator(some_friday, some_friday+timedelta(3), localtz).generate_tick_labels()
        first_label = ticks[0]
        
        self.assert_contains('4', first_label.label)
        self.assert_contains('30', first_label.label)
        self.assert_contains('10', first_label.label)
    
    def test_ticks_are_at_midnight_in_viewers_timezone(self):
        viewer_timezone = get_timezone("GMT -4:00")
        ticks = self._generate_ticks_in_interval(self.yesterday, self.now, viewer_timezone)
        for tick in ticks:
            self.assert_equals(0, tick.hour) # should all be on midnight
            self.assert_equals(0, tick.minute)
            self.assert_equals(viewer_timezone, tick.tzinfo)
    
    def test_can_leave_out_specified_days(self):
        days_to_remove = [self.today]
        ticks = self._generate_ticks_in_interval(self.yesterday, self.tomorrow, localtz, days_to_remove)
        self.assert_length(1, ticks)
        self.assert_equals(self.yesterday, ticks[0])
    
    def test_leaving_out_specific_days_works_with_tick_interval_bigger_than_one(self):
        days_to_remove = [self.today]
        start = self.today - timedelta(days=20)
        ticks = self._generate_ticks_in_interval(start, self.tomorrow, localtz, days_to_remove)
        self.assert_length(10, ticks)
        
