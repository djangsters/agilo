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

from datetime import timedelta

import agilo.utils.filterwarnings

from agilo.scrum.burndown.charts import ValuesPerTimeCompactor
from agilo.test import AgiloTestCase
from agilo.utils.days_time import midnight, now
from agilo.api.controller import ValuePerTime

class CompactorTest(AgiloTestCase):
    now = now()
    today = midnight(now)
    one_week_ago = today - timedelta(days=7)
    yesterday = today - timedelta(days=1)
    tomorrow = today + timedelta(days=1)
    next_week = today + timedelta(days=7)
    
    def _compact_values(self, timed_values, days_to_remove):
        compactor = ValuesPerTimeCompactor(timed_values, days_to_remove)
        return compactor.compact_values()
    
    def _remove_today(self, timed_values):
        return self._compact_values(timed_values, [self.today])
    
    def test_hiding_a_day_does_not_remove_previous_days(self):
        timed_values = [ValuePerTime('fnord', self.yesterday),
                        ValuePerTime('fnord', self.now) ]
        compacted_days = self._remove_today(timed_values)
        self.assert_length(1, compacted_days)
        self.assert_equals(self.yesterday, compacted_days[0].when)
    
    def test_does_nothing_when_no_days_are_hidden(self):
        timed_values = [ValuePerTime('fnord', self.yesterday),
                        ValuePerTime('fnord', self.now),
                        ValuePerTime('fnord', self.tomorrow), ]
        compacted_days = self._compact_values(timed_values, [])
        self.assert_length(3, compacted_days)
        self.assert_equals(timed_values, compacted_days)
    
    def test_returns_empty_list_when_values_are_empty(self):
        timed_values = []
        compacted_days = self._remove_today(timed_values)
        self.assert_length(0, compacted_days)
    
    def test_hiding_a_day_does_not_remove_future_days(self):
        timed_values = [ValuePerTime('fnord', self.today),
                        ValuePerTime('fnord', self.now),
                        ValuePerTime('fnord', self.tomorrow),]
        
        compacted_days = self._remove_today(timed_values)
        self.assert_length(1, compacted_days)
        #self.assert_equals(self.tomorrow, compacted_days[0].when)
    
    def test_hiding_one_day_shifts_future_values_by_one_day(self):
        timed_values = [ValuePerTime('fnord', self.tomorrow),]
        
        compacted_days = self._remove_today(timed_values)
        self.assert_length(1, compacted_days)
        self.assert_equals(self.today, compacted_days[0].when) # tomorrow now becomes today
    
    def test_does_not_blow_up_if_no_values_are_present_on_day(self):
        timed_values = [ValuePerTime('fnord', self.yesterday),
                        ValuePerTime('fnord', self.tomorrow), ]
        compacted_days = self._remove_today(timed_values)
        self.assert_length(2, compacted_days)
        self.assert_equals(timed_values, compacted_days)
    
    def test_works_with_several_days_to_remove(self):
        timed_values = [ValuePerTime(1, self.one_week_ago),
                        ValuePerTime(2, self.yesterday),
                        ValuePerTime(3, self.today),
                        ValuePerTime(4, self.now),
                        ValuePerTime(5, self.yesterday),
                        ValuePerTime(6, self.next_week), ]
        compacted_days = self._compact_values(timed_values, [self.yesterday, self.tomorrow])
        self.assert_length(4, compacted_days)
        self.assert_equals([1,3,4,6], [value.value for value in compacted_days])
        self.assert_equals(self.one_week_ago - timedelta(days=0), compacted_days[0].when)
        self.assert_equals(self.today        - timedelta(days=1), compacted_days[1].when)
        self.assert_equals(self.now          - timedelta(days=1), compacted_days[2].when)
        self.assert_equals(self.next_week    - timedelta(days=2), compacted_days[3].when)
    
    def test_compactor_can_generate_final_shift(self):
        self.assert_equals(timedelta(), ValuesPerTimeCompactor.final_shift([]))
        self.assert_equals(timedelta(days=1), ValuesPerTimeCompactor.final_shift([self.today]))
        self.assert_equals(timedelta(days=2), ValuesPerTimeCompactor.final_shift([self.yesterday, self.tomorrow]))
    
