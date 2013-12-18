# -*- encoding: utf-8 -*-
#   Copyright 2008 Agile42 GmbH, Berlin (Germany)
#   Copyright 2007 Andrea Tomasini <andrea.tomasini_at_agile42.com>

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


from trac.core import TracError
from trac.resource import Resource
from trac.util.text import to_unicode

from agilo.core import PersistentObject, Field, Relation,\
    PersistentObjectModelManager, Manager, safe_execute
from agilo.utils import Key, Realm
from agilo.utils.config import AgiloConfig
from agilo.utils.log import debug
from agilo.utils.db import get_db_for_write
from agilo.utils.days_time import count_working_days, add_to_date, normalize_date, now
from agilo.scrum import BACKLOG_TICKET_TABLE
from agilo.scrum.team.model import Team


class Sprint(PersistentObject):
    """
    Represent a Sprint, a Scrum iteration of development. A sprint is characterized
    by being a timeboxed iteration, in which a team will work to develop a selected
    amount of User Stories (AgiloTicket <story>) before the end. The team_members
    create Tasks (AgiloTicket <task>) to work on every aspect related to the User
    Stories as well as infrastructure needed in order to deliver a finished product
    at the end of the Sprint.
    """
    class Meta(object):
        manager = Manager('agilo.scrum.sprint.SprintModelManager')
        name = Field(primary_key=True)
        description = Field()
        start = Field(type='datetime') # We need also the hours
        end = Field(type='datetime', db_name='sprint_end') # We need also the hours
        milestone = Field()
        team = Relation(Team, db_name='team')
        
    def __init__(self, env, **kwargs):
        """
        Initialize a Sprint, in particular check the duration parameter
        used as virtual to set the end date of the sprint
        """
        # duration is not a real db field so the PersistentObject suspect an
        # programmer error
        duration = kwargs.pop(Key.DURATION, None)
        super(Sprint, self).__init__(env, **kwargs)
        if duration is not None:
            self.duration = duration
    
    def __unicode__(self):
        return u"<Sprint@%s (%s) for '%s' %s>" % (id(self),
                                                  self.name, 
                                                  self.milestone, 
                                                  self._old)
    
    def __repr__(self):
        name = self.name
        milestone = repr(self.milestone)
        old = repr(self._old)
        return '<Sprint@%s (%s) for %s %s>' % (id(self), name, milestone, old)
    
    def resource(self):
        return Resource(Realm.SPRINT, self.name)
    
    def _before_set_start(self, value):
        """Sets the start date of a sprint normalizing it"""
        shift_to_next_work_day = not AgiloConfig(self.env).sprints_can_start_or_end_on_weekends
        return normalize_date(value, shift_to_next_work_day=shift_to_next_work_day)
    
    def _before_set_end(self, value):
        """Sets the end of the sprint, normalizing it"""
        shift_to_next_work_day = not AgiloConfig(self.env).sprints_can_start_or_end_on_weekends
        return normalize_date(value, start=False, shift_to_next_work_day=shift_to_next_work_day)
    
    def _set_duration(self, value):
        """Sets the duration of the Sprint and recalculates the end Date"""
        if value is not None:
            week_days_off = None
            if AgiloConfig(self.env).sprints_can_start_or_end_on_weekends:
                week_days_off = []
            self.end = add_to_date(self.start, value, week_days_off=week_days_off)
            debug(self, "Setting Sprint end date to: %s" % self.end)
        
    def _get_duration(self):
        """Gets the duration of the Sprint"""
        duration = count_working_days(self.start, self.end)
        debug(self, "Returning duration %d start: %s, end: %s" % \
                    (duration, self.start, self.end))
        return duration

    duration = property(_get_duration, _set_duration)

    def _after_set_name(self, old_value, new_value):
        """Sets the name of the sprint, and rename all the tickets accordingly"""
        if old_value is not None and new_value is not None and old_value != new_value:
            self._rename(old_value, new_value)
    
    @property
    def is_currently_running(self):
        """Returns True if this sprint is active (today is between start and
        end)."""
        if None not in (self.start, self.end):
            return (self.start <= now()) and (now() <= self.end)
        return False

    @property
    def is_closed(self):
        """Returns True if this sprint is already closed"""
        if None not in (self.start, self.end):
            return self.end < now() 
        return False
    
    def _rename(self, name, new_name, db=None):
        """Renames this sprint and reassigns all tickets to the new 
        name."""
        # avoid circular imports
        from agilo.scrum.metrics.model import TeamMetrics
        params = {
            'name' : name,
            'new_name' : new_name,
        }
        team_metrics_entry_table = TeamMetrics.TeamMetricsEntry._table.name
        queries = [
            "UPDATE ticket_custom SET value=%(new_name)s WHERE name='sprint' AND value=%(name)s",
            "UPDATE " + team_metrics_entry_table + " SET sprint=%(new_name)s WHERE sprint=%(name)s",
        ]
        db, handle_ta = get_db_for_write(self.env, db)
        try:
            cursor = db.cursor()
            for q in queries:
                debug(self, "RENAME => Executing query: %s (%s)" % (q, params))
                safe_execute(cursor, q, params)
            if handle_ta:
                db.commit()
        except Exception, e:
            if handle_ta:
                db.rollback()
            raise TracError("An error occurred while renaming sprint: %s" % to_unicode(e))

    def get_team_metrics(self):
        """
        Return the team metrics object for this sprint or None if no team
        is assigned for this sprint.
        """
        metrics = None
        if self.team != None:
            # Avoid recursive imports
            from agilo.scrum.metrics.model import TeamMetrics
            metrics = TeamMetrics(self.env, sprint=self, 
                                  team=self.team)
        return metrics
    
    def get_capacity_hours(self):
        """Returns the Working Capacity expressed in our for this sprint. This
        of course related to the capacity of the individual members of the team
        assigned to this sprint. If there is no team assigned it will not be
        possible to calculate the capacity."""
        sum = 0
        if self.team:
            for member in self.team.members:
                sum += member.get_total_hours_for_interval(self.start, 
                                                           self.end)
        return sum
    
    def backlog(self):
        from agilo.scrum.backlog.model import BacklogModelManager
        return BacklogModelManager(self.env).get(name=self.name, scope=Key.SPRINT)
    
    def _fetch_tickets(self, db=None):
        """
        Fetch from the DB the ids, type, status of the tickets planned for this sprint,
        and returns a list of id, type, status.
        """
        params = {'table': BACKLOG_TICKET_TABLE, 'scope': self.name}
        t_sql = "SELECT DISTINCT id, type, status FROM ticket INNER JOIN ticket_custom ON "\
                "ticket.id=ticket_custom.ticket LEFT OUTER JOIN %(table)s ON " \
                "ticket.id=%(table)s.ticket_id WHERE (%(table)s.name='Sprint Backlog' " \
                "AND scope='%(scope)s') or (ticket_custom.name='sprint' AND " \
                "ticket_custom.value='%(scope)s')" % params
        
        tickets = [(0, '', '')]
        
        db, handle_ta = get_db_for_write(self.env, db)
        try:
            cursor = db.cursor()
            debug(self, "SQL (_fetch_tickets_stats): %s" % t_sql)
            cursor.execute(t_sql)
            tickets = cursor.fetchall()
        except:
            if handle_ta:
                db.rollback()
        return tickets
    
    def save(self, db=None):
        """Override save to reset ticket fields in the ticket system"""
        result = super(Sprint, self).save(db=db)
        # Reset the fields for trac 0.11.2
        from agilo.ticket.api import AgiloTicketSystem
        ats = AgiloTicketSystem(self.env)
        if hasattr(ats, 'reset_ticket_fields'):
            ats.reset_ticket_fields()
        return result


class SprintModelManager(PersistentObjectModelManager):
    """ModelManager to take care of the Sprint Model Object"""
    model = Sprint

