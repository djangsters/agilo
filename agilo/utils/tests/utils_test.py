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
#       - Andrea Tomasini <andrea.tomasini_at_agile42.com>

from datetime import datetime

from trac.util.datefmt import localtz, get_timezone, to_datetime

from agilo.test import AgiloTestCase
from agilo.utils.config import AgiloConfig
import agilo.utils.days_time as dt
from agilo.utils import Key


class TestDaysTime(AgiloTestCase):
    """Tests the days time module"""
    
    def setUp(self):
        self.super()
        self.start_sunday = datetime(2008, 8, 31, hour=9, tzinfo=localtz)
        self.end_sunday = datetime(2008, 9, 7, hour=18, tzinfo=localtz)
    
    def testWorkingDays(self):
        """Test the working days calculation"""
        # Normal Working days
        self.assert_equals(5, dt.count_working_days(self.start_sunday, self.end_sunday))
        # Now without any day off
        self.assert_equals((self.end_sunday - self.start_sunday).days + 1,
                         dt.count_working_days(self.start_sunday, self.end_sunday, week_days_off=[]))
        # Now check that the start and end dates are in
        days = dt.get_working_days(self.start_sunday, self.end_sunday, week_days_off=[])
        self.assert_true(self.start_sunday in days, "Start Sunday: %s is not in!" % self.start_sunday)
        self.assert_true(self.end_sunday in days, "End Sunday: %s is not in!" % self.end_sunday)
        
    def testCalendarDays(self):
        """Test Calendar Days"""
        days = dt.get_calendar_days(self.start_sunday, 5)
        self.assert_equals(6, len(days))
        
    def testAgiloCalendar(self):
        """Test the AgiloCalendar Object"""
        ac = dt.AgiloCalendar(month=9, year=2008)
        self.assert_equals(ac.count_days(), 30)
        self.assert_equals(ac.get_first_day().day, 1)
        self.assert_equals(ac.get_last_day().day, 30)
        
        ac = ac.next_month() # October
        self.assert_equals(ac.count_days(), 31)
        self.assert_equals(ac.get_first_day().day, 1)
        self.assert_equals(ac.get_last_day().day, 31)
        
    def testUTCDayTimeConversions(self):
        """Tests the UTC Datetime conversion, using timezone and utcoffsets"""
        bangkok_tz = get_timezone('GMT +7:00')
        now_in_bangkok = to_datetime(datetime(2009, 7, 11, 2, 30, tzinfo=bangkok_tz))
        midnight_in_bangkok = dt.midnight(now_in_bangkok)
        midnight_in_bangkok_as_utc = dt.midnight_with_utc_shift(now_in_bangkok)
        self.assert_equals(midnight_in_bangkok, midnight_in_bangkok_as_utc)


class TestAgiloConfig(AgiloTestCase):
    
    def test_reload_config(self):
        """Tests the reload of the config"""
        types = AgiloConfig(self.env).get_section(AgiloConfig.AGILO_TYPES)
        
        # Add a ticket type
        types.change_option('my_type', ', '.join([Key.PRIORITY, Key.COMPONENT]))
        types.change_option('my_type.alias', 'My Type')
        types.save()
        self.assert_true('my_type' in AgiloConfig(self.env).ALIASES, 
                         "Type not found in aliases, AgiloConfig not reloaded?")


if __name__ == '__main__':
    from agilo.test.testfinder import run_unit_tests
    run_unit_tests(__file__)