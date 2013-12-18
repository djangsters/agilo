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

from trac.db import Column, Table
from trac.util.datefmt import to_datetime, to_timestamp, utc

from agilo.core.model import safe_execute
from agilo.db import create_table_with_cursor

__all__ = ['do_upgrade']

# Upgrade from 0.8.4.2 to 0.8.4.3
def do_upgrade(env, ver, cursor, db_connector):
    return DB6(env, cursor, db_connector).upgrade()


class DB6(object):
    def __init__(self, env, cursor, db_connector):
        self.env = env
        self.cursor = cursor
        self.db_connector = db_connector
    
    def upgrade(self):
        self.create_burndown_changes_table()
        self.store_actual_burndown_for_all_sprints()
        return True
    
    def create_burndown_changes_table(self):
        burndown_changes_table = Table('agilo_burndown_data_change', key=('id',))[
            Column('id', type='integer', auto_increment=True),
            Column('burndown_type'),
            Column('scope'),
            Column('timestamp', type='int'),
            Column('value')
        ]
        create_table_with_cursor(burndown_changes_table, self.cursor, self.db_connector)
    
    def store_actual_burndown_for_all_sprints(self):
        remaining_times = self.all_remaining_times()
        for task_id, remaining in remaining_times.items():
            last_sprint_name = self.last_sprint_name_for_ticket(task_id)
            if last_sprint_name in (None, ''):
                continue
            # Assumption: Each task is worked in each sprint
            # Justification: The 0.8 burndown chart relies on the sprint backlog
            # and this will not contain the task for previous sprints anyway.
            previous_remaining_time = 0
            for when, absolute_remaining_time in remaining:
                delta = absolute_remaining_time - previous_remaining_time
                self.store_burndown_change(last_sprint_name, when, delta)
                previous_remaining_time = absolute_remaining_time
    
    def store_burndown_change(self, sprint_name, when, delta):
        sql = 'INSERT INTO agilo_burndown_data_change (burndown_type, scope, timestamp, value) values (%(burndown_type)s, %(scope)s, %(timestamp)s, %(value)s)'
        parameters = dict(burndown_type='remaining_time', scope=sprint_name, timestamp=to_timestamp(when), value=delta)
        safe_execute(self.cursor, sql, parameters)
    
    def all_remaining_times(self):
        remaining_times = {}
        self.cursor.execute("SELECT task_id, date, remaining_time from agilo_burndown order by task_id, date")
        for task_id, timestamp, remaining_time in self.cursor.fetchall():
            when = to_datetime(timestamp, tzinfo=utc)
            remaining_times.setdefault(task_id, [])
            remaining_times[task_id].append((when, remaining_time))
        return remaining_times
    
    def last_sprint_name_for_ticket(self, ticket_id):
        self.cursor.execute("SELECT value FROM ticket_custom where ticket=%d and name='sprint'" % ticket_id)
        row = self.cursor.fetchone()
        if row is not None:
            return row[0]
        return None
    
    def all_sprint_names(self):
        self.cursor.execute('SELECT name FROM agilo_sprint')
        return self.cursor.fetchall()

