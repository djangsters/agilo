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

from trac.db import DatabaseManager
from trac.util.datefmt import utc, to_datetime, to_timestamp

from agilo.db.db_util import drop_table
from agilo.db.upgrades import db6
from agilo.utils.db import get_db_for_write
from agilo.utils.days_time import now
from agilo.test.functional import AgiloFunctionalTestCase
from agilo.core.model import safe_execute
from agilo.ticket.api import AgiloTicketSystem


class BaseMigrationTestCase(AgiloFunctionalTestCase):
    
    is_abstract_test = True
    
    def setUp(self):
        self.super()
        self.teh.disable_sprint_date_normalization()
        self.set_up_tables()
    
    def set_up_tables(self):
        pass
    
    def db(self):
        return get_db_for_write(self.env)[0]
    
    def db_connector(self):
        db_connector, args = DatabaseManager(self.env)._get_connector()
        return db_connector
    
    def drop_table(self, tablename):
        db = self.db()
        cursor = db.cursor()
        drop_table(cursor, tablename)
        db.commit()
    
    def perform_upgrade(self, upgrade_function, version=None):
        db = self.db()
        self.assert_true(upgrade_function(self.env, version, db.cursor(), self.db_connector()))
        db.commit()
    
    def commit_sql(self, sql, args=None):
        db = self.db()
        cursor = db.cursor()
        safe_execute(cursor, sql, args)
        db.commit()
    
    def execute_sql(self, sql, args=None):
        db = self.db()
        cursor = db.cursor()
        safe_execute(cursor, sql, args)
        return cursor.fetchall()
    
    def assert_is_invalid_sql(self, sql, args=None):
        db = self.db()
        cursor = db.cursor()
        # MySQL, PostgreSQL: ProgrammingError
        # sqlite: OperationalError
        exception_names = ('OperationalError', 'ProgrammingError')
        execute_sql = lambda: safe_execute(cursor, sql, args)
        return self.assert_raises_db_exception(exception_names, execute_sql, db)
    
    def assert_raises_db_exception(self, exception_names, callable, db):
        exception = self.assert_raises(Exception, callable)
        # necessary for postgres
        db.rollback()
        exception_name = exception.__class__.__name__
        self.assert_contains(exception_name, exception_names)
        return exception


class TestCanMigrateBurndownDataForSprintWithoutTeam(BaseMigrationTestCase):
    
    def setUp(self):
        self.super()
        self.env.config.set('components', 'agilo.scrum.backlog.model.backlogupdater', 'disabled')
        self.env.config.set('components', 'agilo.scrum.burndown.changelistener.burndowndatachangelistener', 'disabled')
        # so the changes persist after the shutdown
        self.env.config.save()
        if not AgiloTicketSystem(self.env).is_trac_012():
            self.env.shutdown()
        # restart: so the listeneres that where registered before this test are actually disabled
        self.env = self.testenv.get_trac_environment()
        self.task = self.teh.create_task(sprint=self.sprint_name())
    
    def set_up_tables(self):
        self.super()
        self.commit_sql('DELETE FROM agilo_burndown')
        self.drop_table('agilo_burndown_data_change')
    
    def inject_remaining_time(self, when, remaining_time):
        sql = 'INSERT INTO agilo_burndown (task_id, date, remaining_time) VALUES (%d, %d, %s)'
        values = (self.task.id, to_timestamp(when), remaining_time)
        self.commit_sql(sql % values)
    
    def burndown_changes(self):
        return self.execute_sql('SELECT scope, burndown_type, value, timestamp FROM agilo_burndown_data_change')
    
    def assert_change_contains_correct_data(self, date, remaining_time, row):
        self.assert_equals(self.sprint_name(), row[0])
        self.assert_equals('remaining_time', row[1])
        self.assert_equals(remaining_time, float(row[2]))
        self.assert_equals(date.replace(microsecond=0), to_datetime(row[3], tzinfo=utc))
    
    def test_can_migrate_burndown_data(self):
        whens = map(lambda delta: now() - delta, (
            timedelta(days=8), 
            timedelta(days=5), 
            timedelta(days=4), 
            timedelta(days=1)
        ))
        self.inject_remaining_time(whens[0], 10)
        self.inject_remaining_time(whens[1], 8)
        self.inject_remaining_time(whens[2], 15)
        self.inject_remaining_time(whens[3], 2)
        self.perform_upgrade(db6.do_upgrade)
        
        rows = self.burndown_changes()
        self.assert_length(4, rows)
        self.assert_change_contains_correct_data(whens[0], 10, rows[0])
        self.assert_change_contains_correct_data(whens[1], -2, rows[1])
        self.assert_change_contains_correct_data(whens[2], 7, rows[2])
        self.assert_change_contains_correct_data(whens[3], -13, rows[3])
    
    def test_can_ignore_tasks_without_sprint(self):
        self.task = self.teh.create_task()
        self.inject_remaining_time(now(), 42)
        self.perform_upgrade(db6.do_upgrade)
        
        rows = self.burndown_changes()
        self.assert_length(0, rows)
    
    def test_uses_correct_sprint_if_task_was_moved_once(self):
        previous_sprint_name = 'Previous' + self.sprint_name()
        self.task = self.teh.create_task(sprint=previous_sprint_name)
        self.task['sprint'] = self.sprint_name()
        self.task.save_changes(None, None)
        when = now()
        self.inject_remaining_time(when, 42)
        self.perform_upgrade(db6.do_upgrade)
        
        rows = self.burndown_changes()
        self.assert_length(1, rows)
        self.assert_change_contains_correct_data(when, 42, rows[0])
    
    def test_unplanned_task_is_discarded(self):
        when = now()
        self.inject_remaining_time(when, 42)
        
        self.task['sprint'] = ''
        self.task.save_changes(None, None)
        self.perform_upgrade(db6.do_upgrade)
        
        rows = self.burndown_changes()
        self.assert_length(0, rows)
    
    def test_record_change_even_if_remaining_time_was_never_changed(self):
        self.task = self.teh.create_task(remaining_time=12, sprint=self.sprint_name())
        self.perform_upgrade(db6.do_upgrade)
        
        rows = self.burndown_changes()
        self.assert_length(1, rows)
        row = rows[0]
        self.assert_equals(12, float(row[2]))
        self.assert_time_equals(now(), to_datetime(row[3], tzinfo=utc))

