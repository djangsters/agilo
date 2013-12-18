# -*- encoding: utf-8 -*-
#   Copyright 2008-2009 Agile42 GmbH, Berlin (Germany)
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
#       - Jonas von Poser <jonas.vonposer__at__agile42.com>
#       - Felix Schwarz <felix.schwarz__at__agile42.com>
#       - Andrea Tomasini <andrea.tomasini__at__agile42.com>

from datetime import datetime, date, timedelta
import warnings

from trac.core import TracError, Component, implements
from trac.ticket.api import ITicketChangeListener
from trac.util.datefmt import localtz, to_timestamp
from trac.util.text import to_unicode

from agilo.core.model import Field, PersistentObject, Relation
from agilo.scrum import BURNDOWN_TABLE
from agilo.scrum.sprint.model import Sprint
from agilo.utils import Key
from agilo.utils.days_time import midnight, now, today
from agilo.utils.db import get_db_for_write
from agilo.utils.log import debug, error


#############################
# REFACT: remove this file! #
#############################

__all__ = ['RemainingTime']

class RemainingTime(object):
    """Represents the history of remaining time on a certain task. Whenever the
    remaining time changes, the remaining time on that day is saved into the
    database."""
    def __init__(self, env, task, db=None):
        """Initialize the Sprint, getting the history from the database, if 
        present."""
        self.env = env
        self.log = self.env.log
        self.task = task
        self.db = db
        # List of (timestamp, remaining time) tuples. Timestamps are epoch
        # seconds, remaining time is a number (int or float) in hours. Ordered 
        # in descending order by timestamp.
        self.history = self._load(db)
    
    def _get_timestamp(self, value, ordinal_on_midnight=True):
        # Keep in mind that to have an identity function to make sure that the
        # value on the DB are correctly read and interpreted you need to:
        # timestamp = 1246116716
        # the_datetime = datetime.fromtimestamp(timestamp)
        # the_localized_datetime = the_datetime.replace(tzinfo=datefmt.localtz)
        # datefmt.to_timestamp(the_localized_datetime) == timestamp
        # this is True
        if isinstance(value, int):
            if value < 900000000:
                warnings.warn('Please use datetime instances not ordinals!',
                              DeprecationWarning, stacklevel=3)
                if ordinal_on_midnight:
                    value = datetime.fromordinal(value).replace(tzinfo=localtz)
                else:
                    naive_tomorrow = datetime.fromordinal(value + 1)
                    value = naive_tomorrow.replace(tzinfo=localtz) - timedelta(minutes=1)
        if isinstance(value, date) and not isinstance(value, datetime):
            value = datetime(value.year, value.month, value.day, tzinfo=localtz)
        if isinstance(value, datetime):
            value = to_timestamp(value)
        elif not isinstance(value, int):
            raise NotImplementedError('Unknown type %s' % value.__class__)
        return value
    
    def get_remaining_time(self, day=None):
        """Returns the remaining time on a specific day, passed as a date or
        ordinal value. If none, returns remaining time for today"""
        if day is None:
            # if is today, just return the current remaining time
            return float(self.task[Key.REMAINING_TIME] or 0)
        timestamp = self._get_timestamp(day)
        
        available_timestamps = sorted(self.history)
        remaining_time = None
        if len(available_timestamps) > 0:
            if timestamp < available_timestamps[0]:
                return 0.0
            elif timestamp >= available_timestamps[-1]:
                return self.history[available_timestamps[-1]]
            else:
                last_timestamp = available_timestamps[0]
                for a_timestamp in available_timestamps:
                    if a_timestamp > timestamp:
                        # the last one was the good one
                        remaining_time = self.history[last_timestamp]
                        break
                    last_timestamp = a_timestamp
        else:
            # In case timestamp was built from an ordinal, we must use 0:00 to 
            # check instead of the current time
            if timestamp >= to_timestamp(midnight(today(), tz=localtz)):
                remaining_time = float(self.task[Key.REMAINING_TIME] or 0)
            else:
                remaining_time = 0.0
        return remaining_time
    
    def set_remaining_time(self, remaining_time, day=None):
        """Sets value for remaining time today"""
        timestamp = self._get_timestamp(day or now())
        self._save(timestamp, remaining_time, 
                   update=(timestamp in self.history))
        self.history[timestamp] = remaining_time
        
    def _save(self, timestamp, value, update=False, db=None):
        """Saves a remaining time value to the database. The update parameter
        decides if the value should be updated (True) or inserted (False)"""
        params = {
            Key.TABLE : BURNDOWN_TABLE,
            Key.TASK_ID : self.task.id,
            Key.DATE : timestamp,
            Key.REMAINING_TIME : value,
        }
        if update:
            sql_query = "UPDATE %(table)s SET remaining_time=%(remaining_time)d " \
                        "WHERE task_id=%(task_id)d AND date=%(date)f" % params
        else:
            sql_query = "INSERT INTO %(table)s (task_id, date, remaining_time) " \
                        "VALUES (%(task_id)s, %(date)s, %(remaining_time)s)" % params
        
        db, handle_ta = get_db_for_write(self.env, db)
        try:
            cursor = db.cursor()
            cursor.execute(sql_query)
            if handle_ta:
                db.commit()
                debug(self, 
                      "DB Committed, saved remaining time (%s) for task %d" % \
                      (params[Key.REMAINING_TIME], self.task.id))
        except Exception, e:
            error(self, to_unicode(e))
            if handle_ta:
                db.rollback()
            raise TracError("Error while saving remaining time: %s" % \
                            to_unicode(e))
    
    def _load(self, db=None):
        """Try to load the Sprint from the database"""
        db, handle_ta = get_db_for_write(self.env, db)
        sql_query = "SELECT date, remaining_time FROM %s" \
                    " WHERE task_id=%d ORDER BY date DESC" % (BURNDOWN_TABLE, self.task.id)
        debug(self, "Burndown-SQL Query: %s" % sql_query)
        try:
            history = dict()
            cursor = db.cursor()
            cursor.execute(sql_query)
            for row in cursor.fetchall():
                timestamp, remaining_time = row
                history[timestamp] = remaining_time
            
            self.loaded = True
        except Exception, e:
            error(self, to_unicode(e))
            if handle_ta:
                db.rollback()
            raise TracError("An error occurred while loading Burndown data: %s" % to_unicode(e))

        return history


class BurndownHourRecord(PersistentObject):
    """Stores information on a hourly base, at the end of an hour related to the
    historical burndown chart. The information persisted are:
    - Remaining Time (changes on task change or story drop or add)
    - Capacity (changes on TeamMember availability change or add/remove a Team
    Member from the Team)
    - Story Points (changes on story drop or add)
    """
    class Meta(object):
        timestamp = Field("datetime", primary_key=True)
        sprint = Relation(Sprint, primary_key=True)
        remaining_time = Field("real")
        capacity = Field("real")
        story_points = Field("real")
        

class RemainingTimeUpdater(Component):
    implements(ITicketChangeListener)
    
    #===========================================================================
    # ITicketChangeListener methods
    #===========================================================================
    def ticket_created(self, ticket):
        """Called when a ticket is created."""
        ticket_remaining = ticket[Key.REMAINING_TIME] or None
        if ticket_remaining != None:
            ticket_remaining = float(ticket_remaining or 0)
            rt = RemainingTime(self.env, ticket)
            rt.set_remaining_time(ticket_remaining)

    def ticket_changed(self, ticket, comment, author, old_values):
        """Called when a ticket is modified.
        `old_values` is a dictionary containing the previous values of the
        fields that have changed.
        """
        debug(self, "Invoked for ticket #%s of type %s" % \
                     (ticket.id, ticket[Key.TYPE]))
        if Key.REMAINING_TIME in old_values:
            # remaining time has been changed
            previous_remaining_time = old_values.get(Key.REMAINING_TIME)
            ticket_remaining = float(ticket[Key.REMAINING_TIME] or '0')
        
            if previous_remaining_time != ticket_remaining:
                rt = RemainingTime(self.env, ticket)
                rt.set_remaining_time(ticket_remaining)
                debug(self, "Updated remaining_time for ticket #%s from: %s to %s" % \
                      (ticket, previous_remaining_time, ticket_remaining))

    def ticket_deleted(self, ticket):
        "Called when a ticket is deleted."
        pass

