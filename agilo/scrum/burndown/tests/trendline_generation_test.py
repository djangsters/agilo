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
    BurndownDataChange, BurndownDataConstants, BurndownTrendLineGenerator)
from agilo.test import AgiloTestCase
from agilo.utils.days_time import now


class TrendlineGeneratorTest(AgiloTestCase):
    
    def setUp(self):
        self.super()
        self.generator = BurndownTrendLineGenerator() #self.env), intervall=timedelta(days=3)
    
    def test_smoke(self):
        self.assert_not_none(self.generator)
    
    def test_generate_no_trendline_from_empty_input(self):
        self.assert_is_empty(self.generator.calculate([], now()))
    
    def test_generate_no_trendline_from_one_input(self):
        burndown_values = [burndown_entry(now(), 0)]
        self.assert_is_empty(self.generator.calculate(burndown_values, now()))
    
    def test_continues_straight_line_if_only_two_values_further_apart_than_the_interval_are_given(self):
        until = now()
        first = burndown_entry(until - timedelta(days=10), 10)
        second = burndown_entry(until - timedelta(days=5), 5)
        extrapolation = self.generator.calculate([first, second], until)
        self.assert_length(2, extrapolation)
        self.assert_equals([burndown_entry(second.when, 5), burndown_entry(until, 0)], extrapolation)
    
    def test_continues_straight_line_if_two_values_are_closer_together_than_the_interval_are_given(self):
        until = now()
        first = burndown_entry(until - timedelta(minutes=10), 10)
        second = burndown_entry(until - timedelta(minutes=5), 5)
        extrapolation = self.generator.calculate([first, second], until)
        self.assert_length(2, extrapolation)
        self.assert_equals([burndown_entry(second.when, 5), burndown_entry(until, 0)], extrapolation)
    
    def test_takes_average_of_three_days_ago_to_compute_interval(self):
        until = now()
        values = [
            burndown_entry(until - timedelta(days=9), 40), # five per day
            burndown_entry(until - timedelta(days=5), 10),
            burndown_entry(until - timedelta(days=4), 15),
        ]
        generator = BurndownTrendLineGenerator(reference_interval=timedelta(days=3))
        extrapolation = generator.calculate(values, until)
        self.assert_length(2, extrapolation)
        self.assert_equals([burndown_entry(values[-1].when, 15), burndown_entry(until, 15 - 4*5)], extrapolation)
        
