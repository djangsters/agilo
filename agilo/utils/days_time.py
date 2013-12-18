# -*- encoding: utf-8 -*-
#   Copyright 2008 Agile42 GmbH, Berlin (Germany)
#   Copyright 2007 Andrea Tomasini <andrea.tomasini_at_agile42.com>
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
#       - Andrea Tomasini <andrea.tomasini_at_agile42.com>

from datetime import date, datetime, time, timedelta
import locale
import re
import sys
from time import strptime

from trac.core import TracError
from trac.util import datefmt
from trac.util.datefmt import FixedOffset, localtz, to_datetime, utc

# Defines one day interval
one_day = timedelta(days=1)

# TODO: (AT) set as preferences the start of the
# working day and the end in hour in UTC
DAY_STARTS_AT = datetime(2008, 1, 1, 9, 0, 0, 0, utc)
DAY_ENDS_AT = datetime(2008, 1, 1, 18, 0, 0, 0, utc)


class AgiloCalendar(object):
    """Represent a month calendar object"""
    def __init__(self, year=None, month=None, day=None, first_day_of_the_week=0):
        """Initialize a Calendar for the given date"""
        assert (day is not None and (isinstance(day, date) or isinstance(day, datetime))) or \
                (year is not None and month is not None), 'day must be a date or datetime object'
        if day is not None:
            if isinstance(day, datetime):
                day = day.date()
            self.month = day.month
            self.year = day.year
        else:
            self.month = month
            self.year = year
        self.first_day_of_the_week = first_day_of_the_week
        
    def iter_days(self):
        """Generator to return all the days as dates in this month"""
        day = datetime(self.year, self.month, 1).date()
        # Go back to the beginning of the week
        while True:
            yield day
            day += one_day
            if day.month != self.month:
                break
    
    def get_days(self):
        """Return the list of the days of this month"""
        return list(self.iter_days())
    
    def count_days(self):
        """Return the number of days in the month"""
        return len(self.get_days())
    
    def get_first_day(self):
        """Return the first day of the month"""
        return self.get_days()[0]
    
    def get_last_day(self):
        """Return the last day of the month"""
        return self.get_days()[-1]
    
    def next_month(self):
        """Returns the calendar for next month"""
        year = self.year
        month = self.month
        if month == 12:
            year += 1
            month = 1
        else:
            month += 1
        return AgiloCalendar(month=month, year=year)
    

def is_working_day(date, week_days_off=None):
    """Returns True if the date is a working day"""
    if week_days_off is None:
        week_days_off = 6, 7 # default to: saturdays and sundays
    if date is not None:
        if isinstance(date, datetime):
            date = date.date()
        return date.isoweekday() not in week_days_off

def _shift_to_next_working_day(day, start):
    # Patch the time if shifted otherwise leave it like it is
    if hasattr(day, 'hour') and day.hour == 0 and not is_working_day(day):
        if start:
            day = day.replace(hour=9, second=0)
        else:
            day = day.replace(hour=18, second=0)
    # shift the day if it is a weekend day
    while not is_working_day(day):
        day += one_day
    # now times are stored in UTC timezone
    return day

def normalize_date(day, start=True, shift_to_next_work_day=True):
    """
    Returns a normalized datetime:
         - If the day is a working day is returned
         - If the day is not a working day, the first working day
           available before the date will be returned.
         - If there is no time information and start is True, it will
           be normalized to 9am, otherwise to 6pm
    Removes also the microseconds that will be not stored in the db
    """
    if day in [None, 0]:
        # Our PersistentObject does not convert types if the value 0 so we have
        # to catch that here explicitly (else testLoadSprintWhichHasNoStartDate
        # would fail).
        day = None
    else:
        if shift_to_next_work_day:
            day = _shift_to_next_working_day(day, start)
        if hasattr(day, 'microsecond'):
            # Removes the microseconds from the datetime and shift to utc
            day = shift_to_utc(day.replace(microsecond=0))
    return day

def shift_to_utc(day):
    """Shifts the given date to UTC timezone and returns it. In case
    of naive datetime it sets it to UTC"""
    if day.tzinfo is None:
        day = day.replace(tzinfo=utc)
    else:
        day = day.astimezone(utc)
    return day

def _compute_interval(start, end=None, duration=None, week_days_off=None):
    """
    Compute the days in the interval and return a list of
    calendar days
    """
    assert duration is not None or end is not None, \
            "You must provide either duration or end"
    day = start
    if not isinstance(day, datetime):
        # Normalize the start to 9:00 am
        day = shift_to_utc(datetime(day.year, day.month, 
                                     day.day, hour=9, 
                                     tzinfo=localtz))
    if end is not None and not isinstance(end, datetime):
        # Normalize the end to 6:00 pm
        end = shift_to_utc(datetime(end.year, end.month, 
                                     end.day, hour=18, 
                                     tzinfo=localtz))
    days = list()
    first = True
    if duration is not None:
        while duration >= 0: # We need also the current day
            if is_working_day(day, week_days_off):
                duration -= 1
            if duration == 0: # in case it ends over the weekend
                day = day.replace(hour=18) # Set it to 6pm
                days.append(day)
                break
            days.append(day)
            day += one_day
            # Normalize to a whole day resetting time info
            if first:
                first = False
                day = day.replace(hour=0, minute=0, second=0, microsecond=0)
    elif end is not None:
        while day.date() <= end.date():
            if is_working_day(day, week_days_off):
                if day.date() == end.date():
                    days.append(end) # The real time is taken
                else:
                    days.append(day)
            day += one_day
            # Normalize to a whole day resetting time info
            if first:
                first = False
                day = day.replace(hour=0, minute=0, second=0, microsecond=0)
    return days

def add_to_date(start, duration, holidays=0, week_days_off=None):
    """
    Returns the date "duration" working days after the given start date. 
    """
    days = _compute_interval(start, 
                             duration=duration+holidays,
                             week_days_off=week_days_off)
    if len(days) > 0:
        return days[-1]
    else: 
        return start

def get_calendar_days(start, duration, week_days_off=None):
    """
    Returns the list of elapsed days from a given start date
    and a given duration, expressing an amount of working days
    """
    if start is not None and duration is not None and \
            isinstance(start, (datetime, date)) and isinstance(duration, int):
        return _compute_interval(start, 
                                 duration=duration,
                                 week_days_off=week_days_off)
    return []

def get_working_days(start, end, week_days_off=None):
    """Returns a list of working days within the given interval, start and end
    are passed either as datetimes, dates or ordinal values."""
    if start is not None and end is not None:
        if isinstance(start, (date, datetime)) and isinstance(end, (date, datetime)):
            # passed dates are date values
            return _compute_interval(start, 
                                     end=end, 
                                     week_days_off=week_days_off)
        elif isinstance(start, int) and isinstance(end, int):
            # passed dates are ordinal values
            return _compute_interval(date.fromordinal(start), 
                                     end=date.fromordinal(end),
                                     week_days_off=week_days_off)
    return []

def standard_working_hours():
    """Returns the amount of hours of work for a working day, based
    on the two parameters DAY_STARTS_AT, DAY_ENDS_AT"""
    return diff_in_hours(DAY_ENDS_AT, DAY_STARTS_AT)

def diff_in_hours(one_datetime, two_datetime):
    """Returns the diff in hours between two given datetimes"""
    return abs((one_datetime - two_datetime).seconds / 3600)

def count_working_days(start, end, holidays=0, week_days_off=None):
    """Returns the count of the working days between start and end"""
    return len(get_working_days(start, end, week_days_off)) - holidays

def ustrfdate(day, format='%x %X'):
    return unicode_strftime(day, format)

def now(tz=None):
    """Return the current date/time in the requested timezone (or the server 
    timezone if not specified explicitely."""
    return to_datetime(None, tzinfo=tz)

# REFACT fs: today is a nice name for a local variable, consider putting all of 
# these methods into a class (can also go around the 'hand-in tz' problem.
# REFACT: today, yesterday, tomorrow should all return datetimes - date 
# functionality is not used anymore
def today(tz=None):
    """Return the current date in the requested timezone (or the server 
    timezone if not specified explicitely."""
    return now(tz=tz).date()

def yesterday(tz=None):
    """As today - only one day earlier"""
    return today(tz=tz) - timedelta(days=1)

def tomorrow(tz=None):
    "As today - only one day later"
    return today(tz=tz) + timedelta(days=1)

def day_after_tomorrow(tz=None):
    return tomorrow(tz=tz) + timedelta(days=1)

def midnight(when, tz=None):
    """Return midnight (0am) of the given date/datetime at the given timezone"""
    if isinstance(when, datetime):
        mid_night = when.replace(hour=0, minute=0, second=0, microsecond=0)
        if mid_night.tzinfo is None:
            mid_night = mid_night.replace(tzinfo=(tz or localtz))
        return mid_night
    assert isinstance(when, date)
    return datetime(when.year, when.month, when.day, tzinfo=(tz or localtz))

def date_to_datetime(a_date, tz=localtz):
    if isinstance(a_date, datetime):
        return a_date
    return datetime.combine(a_date, time(tzinfo=tz))

def midnight_with_utc_shift(when):
    """Returns the Midnight of the given day, considering the UTC offset, as a
    UTC shifted datetime.
        E.g.: for datetime(2009, 7, 10, 20, 30, tz=<Bangkok GMT+7>) will return
              datetime(2009, 7, 9, 17, 0, tz<UTC 00:00>) that is 7h offset 
              counting also the timeslack of 20:30
    """
    if isinstance(when, datetime):
        return midnight(when).astimezone(utc)
    
def unicode_strftime(value, format):
    """Actually Python's strftime does not return unicode strings but
    only byte strings. This function takes a date or datetime instance
    and returns the unicode string representation according to the 
    given format.
    The code is a part of format_datetime() (trac.util.datefmt) in
    Trac 0.11.2."""
    text = value.strftime(format)
    encoding = locale.getpreferredencoding() or sys.getdefaultencoding()
    if sys.platform != 'win32' or sys.version_info[:2] > (2, 3):
        encoding = locale.getlocale(locale.LC_TIME)[1] or encoding
        # Python 2.3 on windows doesn't know about 'XYZ' alias for 'cpXYZ'
    return unicode(text, encoding, 'replace')

def datetime_str_to_datetime(value):
    """Parses the output of str(datetime) and returns a (timezone-aware) 
    datetime instance."""
    match = re.search('^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})'\
                      + '(?:\.(\d{6}))?'\
                      + '(?:\+(\d{2}):(\d{2}))?$', value)
    assert match
    datetime_string = match.group(1)
    microsecond = match.group(2)
    tz_hours = match.group(3)
    tz_minutes = match.group(4)
    
    naive_datetime = datetime(*strptime(datetime_string, '%Y-%m-%d %H:%M:%S')[0:6])
    if microsecond:
        naive_datetime = naive_datetime.replace(microsecond=int(microsecond))
    
    if tz_hours is None:
        return naive_datetime
    tz_label = 'GMT +%s:%s' % (tz_hours, tz_minutes)
    tz = FixedOffset(int(tz_hours)*60 + int(tz_minutes), tz_label)
    return naive_datetime.replace(tzinfo=tz)

# AT: Monkey patching for parse_date that doesn't consider the 
# daylight saving in the timezone
def better_parse_date(text, tzinfo=None):
    tzinfo = tzinfo or localtz
    if text == 'now': # TODO: today, yesterday, etc.
        return datetime.now(utc)
    tm = None
    text = text.strip()
    # normalize ISO time
    match = datefmt._ISO_8601_RE.match(text)
    if match:
        try:
            g = match.groups()
            years = g[0]
            months = g[1] or '01'
            days = g[2] or '01'
            hours, minutes, seconds = [x or '00' for x in g[3:6]]
            z, tzsign, tzhours, tzminutes = g[6:10]
            if z:
                tz = timedelta(hours=int(tzhours or '0'),
                               minutes=int(tzminutes or '0')).seconds / 60
                if tz == 0:
                    tzinfo = utc
                else:
                    tzinfo = datefmt.FixedOffset(tzsign == '-' and -tz or tz,
                                                 '%s%s:%s' %
                                                 (tzsign, tzhours, tzminutes))
            tm = strptime('%s ' * 6 % (years, months, days,
                                            hours, minutes, seconds),
                               '%Y %m %d %H %M %S ')
        except ValueError:
            pass
    else:
        for format in ['%x %X', '%x, %X', '%X %x', '%X, %x', '%x', '%c',
                       '%b %d, %Y']:
            try:
                tm = strptime(text, format)
                break
            except ValueError:
                continue
    if tm == None:
        hint = datefmt.get_date_format_hint()        
        raise TracError('"%s" is an invalid date, or the date format '
                        'is not known. Try "%s" instead.' % (text, hint),
                        'Invalid Date')
    if not hasattr(tzinfo, 'localize'):
        # This is a tzinfo define by trac which don't have to deal with dst
        dt = datetime(*(tm[0:6] + (0, tzinfo)))
    else:
        # We need to detect daylight saving correctly - see #...
        dt = tzinfo.localize(datetime(*tm[0:6]))
    # Make sure we can convert it to a timestamp and back - fromtimestamp()
    # may raise ValueError if larger than platform C localtime() or gmtime()
    try:
        datefmt.to_datetime(datefmt.to_timestamp(dt), tzinfo)
    except ValueError:
        raise TracError('The date "%s" is outside valid range. '
                        'Try a date closer to present time.' % (text,),
                        'Invalid Date')
    return dt

if len(datefmt.parse_date.func_defaults) == 1:
    # Monkey patching
    # The better_parse_date is a copy of Trac 0.11's parse_date except
    # it will try to localize the datetime (if pytz is installed)
    # Trac since 0.11.6 does the same thing, so monkey patching is not
    # needed there (yet we still monkey-patch 0.11.6 and .7 here)
    # In Trac 0.12, the function got a new default parameter (hint)
    # so our monkey patching does not apply anymore
    datefmt.parse_date = better_parse_date

