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

from datetime import datetime, date, timedelta, time

from trac.env import Environment
from trac.util.datefmt import get_timezone, localtz, parse_date, to_datetime
from trac.util.text import to_unicode
from trac.util.translation import _


from agilo.api import ValueObject
from agilo.core import Field, Manager, PersistentObject, \
    PersistentObjectModelManager, Relation
from agilo.utils.db import get_db_for_write, \
    get_user_attribute_from_session, set_user_attribute_in_session
from agilo.utils.days_time import DAY_STARTS_AT, DAY_ENDS_AT, standard_working_hours,\
    midnight, date_to_datetime
from agilo.utils.log import warning, error
from agilo.api.controller import ValuePerTime

__all__ = ['Team', 'TeamModelManager', 'TeamMemberModelManager', 'TeamMemberCalendar']


def _get_sprint(sp_manager, sprint_or_name):
    """Returns a Sprint object given a sprint, or a name of a sprint"""
    from agilo.scrum.sprint import Sprint
    sprint = None
    if isinstance(sprint_or_name, Sprint):
        sprint = sprint_or_name
    elif isinstance(sprint_or_name, basestring):
        sprint = sp_manager.get(name=sprint_or_name)
    return sprint

class CapacityPerHour(ValuePerTime):
    capacity = property(ValuePerTime._value, ValuePerTime._set_value)


class Team(PersistentObject):
    """
    This class represents a Scrum Team.
    """
    class Meta(object):
        manager = Manager('agilo.scrum.team.TeamModelManager')
        name = Field(primary_key=True)
        description = Field()
    
    def __init__(self, *args, **kwargs):
        """Set managers instance for other persistent objects"""
        super(Team, self).__init__(*args, **kwargs)
        from agilo.scrum.sprint import SprintModelManager
        self.sp_manager = SprintModelManager(self.env)
    
    def __unicode__(self):
        return u"<Team '%s'>" % self.name
    
    def __repr__(self):
        return '<Team %s>' % repr(self.name)
    
    @property
    def resource(self):
        realm = self.__class__.__name__.lower()
        return '%s:%s' %  (realm, self.name)
    
    @property
    def members(self):
        """Returns the set of Members of this Team."""
        if not hasattr(self, '_cached_members'):
            self._cached_members = TeamMemberModelManager(self.env).select(criteria={'team': self})
        return list(self._cached_members)

    def invalidate_team_member_cache(self):
        if not hasattr(self, '_cached_members'):
            return
        del self._cached_members

    def capacity(self, tz=localtz):
        return TeamCapacity(self, tz)
    

# REFACT: consider to make the interval an attribute of the TeamCapacity, so the method names read better
#     reason: each method deals with intervals
# REFACT: move all capacity methods from team insie this object
class TeamCapacity(object):
    """Intervals use datetimes, but interpret them as dates with timezones only.
    
    You can not use intervals smaller than one day (REFACT this)
    """
    def __init__(self, team, viewer_timezone):
        self.team = team
        # REFACT: Hand in this in the constructor
        self.env = self.team.env
        self.viewer_timezone = viewer_timezone
    
    def hourly_capacities_for_day(self, day):
        """Combines the capacities of all team members on a specific day into one. 
        Takes timezones into account to get all capacity that might happen on a different day,
        but viewed from a specific timezone is still happening on that day."""
        return CapacityCollector(self.env, self.team, day, self.viewer_timezone).execute()
    
    def has_no_capacity_on_day(self, day):
        return 0 == len(self.hourly_capacities_for_day(day))
    
    # REFACT: REMOVE if possible
    # TODO: gives wrong results if team members have customized their capacity for specific days
    # only used in Admin/Team where this behavior is ok
    # Does not take the viewer_timezone into account
    def default_hours_of_capacity_per_week(self):
        """Returns the total capacity of the whole Team in hours."""
        sum = 0
        for member in self.team.members:
            sum += member.get_total_hours_per_week()
        return sum
    
    def _days_in_interval(self, start, end):
        def midnight_in_timezone(timestamp):
            return midnight(date_to_datetime(timestamp, self.viewer_timezone).astimezone(self.viewer_timezone))
        current_date = midnight_in_timezone(start)
        while current_date <= midnight_in_timezone(end):
            yield current_date
            current_date += timedelta(days=1)
    
    def days_without_capacity_in_interval(self, start, end):
        """
        Need to interpret the interval wide, to make sure any capacityless 
        days on the border of the interval are considered.
        """
        capacityless_days = []
        for current_date in self._days_in_interval(start, end):
            if self.has_no_capacity_on_day(current_date):
                capacityless_days.append(current_date)
        return capacityless_days
    
    def hourly_capacities_in_interval(self, start, end):
        """
        Need to interpret the interval narrow, to make sure no capacities outside the
        interval can ever be considered.
        """
        capacities = []
        for current_day in self._days_in_interval(start, end):
            capacities.extend(self.hourly_capacities_for_day(current_day))
        
        return self._filter_entries_outside_of_interval(capacities, start, end)
    
    def _filter_entries_outside_of_interval(self, capacities, start, end):
        start = date_to_datetime(start, self.viewer_timezone)
        end = date_to_datetime(end, self.viewer_timezone)
        
        is_within_interval = lambda capacity: start <= capacity.when <= end
        return filter(is_within_interval, capacities)
    
    def _deduct_contingent_from_daily_capacity(self, summed_contingents, capacities):
        # days with more capacity should get a bigger share of the 
        # contingent work than days with less capacity
        # This is the easiest way of implementing contingent 
        # deduction - if every working day gets the same ammount of
        # the contingent amount, you have to pay attention that no
        # day capacity becomes negative and handle the overflows
        total_capacity = sum(map(lambda each: each.capacity, capacities))
        for each in capacities:
            capacity_percentage = each.capacity / total_capacity
            contingent_deduction = capacity_percentage * summed_contingents
            each.capacity -= contingent_deduction
        return capacities
    
    def _extend_hourly_capacity_until_end_of_sprint(self, capacities, sprint):
        if len(capacities) > 0 and capacities[-1].when >= sprint.end:
            return
        
        current_time = sprint.start
        if len(capacities) > 0:
            current_time = capacities[-1].when
        while current_time <= sprint.end:
            capacities.append(CapacityPerHour(0, current_time))
            current_time += timedelta(hours=1)
    
    def hourly_capacities_in_sprint(self, sprint):
        "Removes the sprints contingents from the capacity"
        # REFACT: I think it's a code smell to call up to the controller layer from the model layer like this
        from agilo.scrum.contingent import ContingentController
        summed_contingents = ContingentController(sprint.env).summed_contingents(sprint).amount
        
        capacities = self.hourly_capacities_in_interval(sprint.start, sprint.end)
        self._extend_hourly_capacity_until_end_of_sprint(capacities, sprint)
        if len(capacities) == 0 or summed_contingents <= 0:
            return capacities
        return self._deduct_contingent_from_daily_capacity(summed_contingents, capacities)
    
    def summed_hourly_capacities_in_sprint(self, sprint):
        capacities = self.hourly_capacities_in_sprint(sprint)
        if 0 == len(capacities):
            return []
        
        values = map(lambda capacity: capacity.capacity, capacities)
        summed_capacities = []
        for i, capacity in enumerate(capacities):
            summed_capacities.append(CapacityPerHour(sum(values[i:]), capacity.when))
        
        return summed_capacities
    

class CapacityCollector(object):
    def __init__(self, env, team, day, timezone):
        self.env = env
        self.team = team
        self.day = day
        self.timezone = timezone
        self.relevant_capacities = []
    
    def execute(self):
        self.collect_relevant_capacities()
        self.remove_entries_on_wrong_day()
        self.sort_by_time()
        self.convert_all_timezones_to_viewer_timezone()
        self.combine_same_times()
        self.terminate_capacities_with_zero_change()
        return self.relevant_capacities
    
    def collect_relevant_capacities(self):
        yesterday = self.day - timedelta(days=1)
        tomorrow = self.day + timedelta(days=1)
        for member in self.team.members:
            self.relevant_capacities.extend(member.calendar.hourly_capacities_for_day(yesterday))
            self.relevant_capacities.extend(member.calendar.hourly_capacities_for_day(self.day))
            self.relevant_capacities.extend(member.calendar.hourly_capacities_for_day(tomorrow))
    
    def remove_entries_on_wrong_day(self):
        first_hour_of_day = datetime.combine(self.day, time(0, tzinfo=self.timezone))
        last_hour_of_day = datetime.combine(self.day, time(23, tzinfo=self.timezone))
        is_on_same_day = lambda capacity: first_hour_of_day <= capacity.when <= last_hour_of_day
        self.relevant_capacities = filter(is_on_same_day, self.relevant_capacities)
    
    def sort_by_time(self):
        self.relevant_capacities.sort(key=lambda capacity: capacity.when)
    
    def convert_all_timezones_to_viewer_timezone(self):
        for capacity in self.relevant_capacities:
            capacity.when = capacity.when.astimezone(self.timezone)
    
    def combine_same_times(self):
        if len(self.relevant_capacities) == 0:
            return []
        
        hourly_capacities = [self.relevant_capacities[0]]
        for capacity in self.relevant_capacities[1:]:
            last_capacity = hourly_capacities[-1]
            if capacity.when == hourly_capacities[-1].when:
                hourly_capacities[-1] = CapacityPerHour(last_capacity.capacity + capacity.capacity, last_capacity.when)
            else:
                hourly_capacities.append(capacity)
        
        self.relevant_capacities = hourly_capacities
    
    def terminate_capacities_with_zero_change(self):
        if 0 == len(self.relevant_capacities):
            return
        
        when = self.relevant_capacities[-1].when + timedelta(hours=1)
        self.relevant_capacities.append(CapacityPerHour(0, when))

class TeamModelManager(PersistentObjectModelManager):
    """Manager to take care of the Team Object"""
    model = Team


class TeamMember(PersistentObject):
    """
    This class represents a Scrum Team Member
    """
    class Meta(object):
        manager = Manager('agilo.scrum.team.TeamMemberModelManager')
        name = Field(primary_key=True)
        team = Relation(Team, db_name='team')
        description = Field()
        ts_mon = Field(type='real')
        ts_tue = Field(type='real')
        ts_wed = Field(type='real')
        ts_thu = Field(type='real')
        ts_fri = Field(type='real')
        ts_sat = Field(type='real') 
        ts_sun = Field(type='real')
    
    DAYS = {0: 'mon', 1: 'tue', 2: 'wed', 3: 'thu', 4: 'fri', 5: 'sat', 6: 'sun'}
    
    def __init__(self, env, default_capacity=[6,6,6,6,6,0,0], **kwargs):
        """
        Initialize the TeamMember object wrapping the default capacity
        into a list of value
        """
        days = dict()
        for i, day in self.DAYS.items():
            days['ts_%s' % day] = default_capacity[i]
        kwargs.update(days)
        super(TeamMember, self).__init__(env, **kwargs)
        # Instance of Sprint Model Manager
        from agilo.scrum.sprint import SprintModelManager
        self.sp_manager = SprintModelManager(self.env)
    
    def __repr__(self):
        team = u''
        if self.team is not None:
            team = ' (%s)' % repr(self.team.name)
        return '<TeamMember %s%s>' % (repr(self.name), team)
    
    def _get_capacity(self):
        capacity = list()
        for day in [self.DAYS[d] for d in sorted(self.DAYS.keys())]:
            capacity.append(getattr(self, 'ts_%s' % day))
        return capacity
    
    def _set_capacity(self, capacity):
        """Sets the capacity for this Member. If capacity is not a valid object or 
        None, this method does nothing."""
        if capacity is not None and len(capacity)==7:
            for i, value in enumerate(capacity):
                setattr(self, 'ts_%s' % self.DAYS[i], value)
        
    capacity = property(_get_capacity, _set_capacity)
    
    def _get_full_name(self):
        return get_user_attribute_from_session(self.env, 'name', self.name)
    
    def _set_full_name(self, fullname):
        set_user_attribute_in_session(self.env, 'name', fullname, self.name)
        
    full_name = property(_get_full_name, _set_full_name)
    
    def _get_email(self):
        return get_user_attribute_from_session(self.env, 'email', self.name)
    
    def _set_email(self, email):
        set_user_attribute_in_session(self.env, 'email', email, self.name)
    
    email = property(_get_email, _set_email)
    
    def timezone(self):
        "timezone object as set in user preferences, or server timezone"
        if not hasattr(self, '_cached_timezone'):
            timezone_name = get_user_attribute_from_session(self.env, 'tz', self.name)
            self._cached_timezone = timezone_name and get_timezone(timezone_name) or localtz
        return self._cached_timezone
    
    def time_workday_starts(self):
        return time(hour=DAY_STARTS_AT.hour, tzinfo=self.timezone())
    
    def time_workday_ends(self):
        return time(hour=DAY_ENDS_AT.hour, tzinfo=self.timezone())
    
    def number_of_working_hours_on_workday(self):
        return standard_working_hours()
    
    # REFACT: Do not load the calendar every time - better tests and faster :-)
    @property
    def calendar(self):
        """
        Returns the TeamMemberCalendar object for this TeamMember. it loads
        from the DB every time, intentionally so that the capacity changes
        are also updated.
        """
        if not hasattr(self, '_cached_calendar'):
            self._cached_calendar = TeamMemberCalendar(self.env, self)
        return self._cached_calendar
    
    def get_total_hours_per_week(self):
        """Returns the sum of working hours for a standard week."""
        return sum(self.capacity)
    
    # -----------------------------------------------------------------------------
    # FIXME: SMELL
    # We're running into an endless recursion if we serialize the TeamMember 
    # completely due to a cycle team.members -> TeamMember -> team. This can be
    # fixed by lazy-serialization in the valueobject.
    # The quick hack workaround is to exclude the team property from serialization.
    def as_dict(self):
        data = dict()
        for name in ('name', 'description', 'ts_mon', 'ts_tue', 'ts_wed', 
                     'ts_thu', 'ts_fri', 'ts_sat', 'ts_sun',
                     'full_name', 'email', 'capacity'):
            data[name] = getattr(self, name)
        # Don't serialize the calendar - it contains an inifite amount of data.
        return ValueObject(data)
    # -----------------------------------------------------------------------------
    
    def get_total_hours_for_interval(self, start, end):
        """Calculates the sum of working hours for the given interval."""
        return sum(self.calendar.get_hours_for_interval(start, end).values())
    

class TeamMemberModelManager(PersistentObjectModelManager):
    """Manager for TeamMember objects"""
    model = TeamMember


class TeamMemberCalendar(object):
    """
    Represent the availability calendar for a TeamMember. It stores in the
    Database the 'exceptions' to the standard planned hours per week, but 
    will return for a given interval the hours for every day in the interval, 
    for the given TeamMember
    """
    class CalendarEntry(PersistentObject):
        """
        Represent and entry in the calendar for a specific TeamMember.
        The keys are the ordinal of the day and the TeamMember name.
        """
        class Meta(object):
            date = Field(type='integer', primary_key=True)
            teammember = Relation(TeamMember, primary_key=True, 
                                  db_name='teammember')
            hours = Field(type='real')
        
    
    def __init__(self, env, team_member):
        """Initialize the calendar for the team member"""
        assert env is not None and isinstance(env, Environment)
        # Create a dictionary to store calendar info, the key
        # will be the ordinal of the date, the value the hours
        self.env = env
        self.log = env.log
        if isinstance(team_member, basestring):
            self.team_member = TeamMemberModelManager(self.env).get(name=team_member)
        elif isinstance(team_member, TeamMember):
            self.team_member = team_member
        # set and instance of CalendarEntryModelManager
        self.ce_manager = CalendarEntryModelManager(self.env)
        self._calendar = dict()
        self._load()
    
    def _get_day_key(self, day):
        """Returns the key and the date for the given day"""
        d_day = None
        if isinstance(day, datetime):
            d_day = day.date()
        elif isinstance(day, date):
            d_day = day
        elif isinstance(day, basestring):
            d_day = parse_date(day).date()
        elif isinstance(day, (int, long)):
            try:
                d_day = to_datetime(day).date()
            except TypeError, e:
                warning(self, _("Unable to covert %s to a date: %s" % \
                                (day, to_unicode(e))))
        return d_day.toordinal(), d_day
    
    def set_hours_for_day(self, hours, day=None, d_ordinal=None):
        """Sets a specific amount of hours for the given day"""
        assert day is not None or d_ordinal is not None
        k_day = None
        if day is not None:
            k_day, d_day = self._get_day_key(day)
        else:
            d_ordinal = int(d_ordinal)
            k_day, d_day = d_ordinal, datetime.fromordinal(d_ordinal).date()
        if k_day is not None:
            if not isinstance(hours, float):
                hours = float(hours)
            self._calendar[k_day] = hours
    
    def get_hours_for_day(self, day=None, d_ordinal=None):
        """Returns the hours of availability for the given day"""
        assert day is not None or d_ordinal is not None
        k_day = d_day = None
        if day is not None:
            k_day, d_day = self._get_day_key(day)
        else:
            d_ordinal = int(d_ordinal)
            k_day, d_day = d_ordinal, datetime.fromordinal(d_ordinal).date()
        if k_day is not None:
            hours = self._calendar.get(k_day)
            if hours is None:
                # Kind of lazy initialization...
                self._calendar[k_day] = self.team_member.capacity[d_day.weekday()]
                hours = self._calendar[k_day]
            return hours
    
    def hourly_capacities_for_day(self, day):
        capacity = self.get_hours_for_day(day)
        if capacity == 0:
            return []
        
        number_of_work_hours = self.team_member.number_of_working_hours_on_workday()
        capacity_per_hour = capacity / float(number_of_work_hours)
        
        capacities = []
        current_time = self.team_member.time_workday_starts()
        for i in range(number_of_work_hours):
            capacity_hour_start = datetime.combine(day, current_time)
            capacities.append(CapacityPerHour(capacity_per_hour, capacity_hour_start))
            # time doesn't combine with timedelta... :(
            current_time = time(current_time.hour + 1, tzinfo=self.team_member.timezone())
        return capacities
    
    def get_hours_for_interval(self, start_date, end_date):
        """
        Returns a dictionary with date: hours from the given
        start_date to the given end_date included.
        """
        k_start, d_start = self._get_day_key(start_date)
        k_end, d_end = self._get_day_key(end_date)
        if None not in (k_start, k_end):
            hours = dict()
            one_day = timedelta(days=1)
            for i in range(k_end - k_start + 1):
                hours[d_start + (one_day) * i] = self.get_hours_for_day(d_ordinal=k_start + i)
            return hours
    
    def _load(self, db=None):
        """loads the CalendarEntries for the given Team Member
        from the database into the local calendar"""
        c_entries = self.ce_manager.select(criteria={'teammember': self.team_member})
        for ce in c_entries:
            self._calendar[ce.date] = ce.hours
    
    def save(self, db=None):
        """saves the object to the database"""
        db, handle_ta = get_db_for_write(self.env, db)
        try:
            for o_day, hours in self._calendar.items():
                entry = self.ce_manager.get(date=o_day, teammember=self.team_member, db=db)
                if not entry:
                    entry = self.ce_manager.create(date=o_day, teammember=self.team_member, db=db)
                # Save only exceptions
                if hours != self.team_member.capacity[datetime.fromordinal(o_day).date().weekday()]:
                    entry.hours = hours
                    self.ce_manager.save(entry, db=db)
                elif entry.exists: # we don't need it anymore
                    self.ce_manager.delete(entry, db=db)
            if handle_ta:
                db.commit()
            # Invalidate the Chart generator cache cause the capacity may be changed
            from agilo.charts import ChartGenerator
            ChartGenerator(self.env).invalidate_cache()
            return True
        except Exception, e:
            error(self, _("An error occurred while saving Calendar Entry: %s" % to_unicode(e)))
            if handle_ta:
                db.rollback()
            raise
        return False


class CalendarEntryModelManager(PersistentObjectModelManager):
    """Manager to manage the CalendarEntry objects"""
    
    model = TeamMemberCalendar.CalendarEntry

