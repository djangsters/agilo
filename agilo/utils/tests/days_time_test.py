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
#
#   Authors: 
#       - Felix Schwarz <felix.schwarz__at__agile42.com>

from datetime import date, datetime

from trac.util.datefmt import FixedOffset, get_timezone, localtz, utc

from agilo.test import AgiloTestCase
from agilo.utils.days_time import date_to_datetime, datetime_str_to_datetime, \
    normalize_date, midnight, now, today


class DateConvenienceFunctionsTest(AgiloTestCase):
    
    def test_date_to_datetime_conversion_returns_datetimes_unmodified(self):
        some_datetime = now()
        self.assert_equals(some_datetime, date_to_datetime(some_datetime))
    
    def test_can_convert_date_to_datetime(self):
        expected_datetime = datetime(2009, 5, 23, 0, 0, tzinfo=localtz)
        some_datetime = date_to_datetime(date(2009, 5, 23))
        self.assert_not_none(some_datetime.tzinfo)
        self.assert_equals(expected_datetime, some_datetime)
    
    def test_can_parse_datetime_str(self):
        self.assert_equals(datetime(2009, 9, 10, 14, 55, 11), 
                                  datetime_str_to_datetime('2009-09-10 14:55:11'))
    
    def test_can_parse_datetime_str_with_tz(self):
        self.assert_equals(datetime(2009, 9, 10, 14, 55, 11, tzinfo=utc), 
                         datetime_str_to_datetime('2009-09-10 14:55:11+00:00'))
        berlin = get_timezone('GMT +2:00')
        self.assert_equals(datetime(2009, 9, 10, 14, 55, 11, tzinfo=berlin), 
                         datetime_str_to_datetime('2009-09-10 14:55:11+02:00'))
        teheran = FixedOffset(3*60+30, 'GMT +3:30')
        self.assert_equals(datetime(2009, 9, 10, 14, 55, 11, tzinfo=teheran), 
                         datetime_str_to_datetime('2009-09-10 14:55:11+03:30'))
    
    def test_can_parse_subsecond_precision_datetimes(self):
        self.assert_equals(datetime(2010, 9, 23, 13, 12, 24, 5482), 
                                  datetime_str_to_datetime('2010-09-23 13:12:24.005482'))
        berlin = get_timezone('GMT +2:00')
        self.assert_equals(datetime(2010, 9, 23, 13, 12, 24, 305482, tzinfo=berlin), 
                         datetime_str_to_datetime('2010-09-23 13:12:24.305482+02:00'))
    
    def test_normalize_date_can_work_with_dates(self):
        self.assert_isinstance(today(), date)
        
        normalize_date(today(), shift_to_next_work_day=True)
        normalize_date(today(), shift_to_next_work_day=False)
    
    def test_midnight_uses_localtz_if_no_other_tz_given(self):
        self.assert_equals(utc, midnight(date.today(), tz=utc).tzinfo)
        self.assert_equals(localtz, midnight(date.today()).tzinfo)
        self.assert_equals(utc, midnight(datetime.now(), tz=utc).tzinfo)
        self.assert_equals(localtz, midnight(datetime.now()).tzinfo)
    
    def test_midnight_keeps_timezone_if_already_specified(self):
        los_angeles = get_timezone('GMT -8:00')
        self.assert_equals(los_angeles, midnight(datetime.now(tz=los_angeles)).tzinfo)

