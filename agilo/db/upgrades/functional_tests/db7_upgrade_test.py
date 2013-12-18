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

from trac.db import Table, Column

from agilo.db.db_util import create_table_with_cursor
from agilo.db.upgrades import db7
from agilo.db.upgrades.functional_tests.db6_upgrade_test import BaseMigrationTestCase


class TestBacklogTicketTableUpdate(BaseMigrationTestCase):
    
    def setUp(self):
        self.super()
        self.sample_row = {"name": "backlog_name", "pos": 0, "scope": "fnord_scope", "ticket_id": 0}
    
    def set_up_tables(self):
        self.drop_table('agilo_backlog_ticket')
        old_table = Table('agilo_backlog_ticket', key=['name', 'pos', 'scope'])[
            Column('name'),
            Column('pos', type='integer'),
            Column('scope'),
            Column('level', type='integer'),
            Column('ticket_id', type='integer')
        ]
        db = self.db()
        create_table_with_cursor(old_table, db.cursor(), self.db_connector())
        db.commit()
    
    def _generate_insert_query(self, row):
        sql = "INSERT INTO agilo_backlog_ticket (%s) VALUES (%s)"
        columns = []
        values = []
        for column, value in row.items():
            columns.append(column)
            values.append(value)
        column_names = ', '.join(columns)
        value_placeholders = ', '.join( ('%s',) * len(columns))
        return sql % (column_names, value_placeholders), values
    
    def test_upgraded_backlog_ticket_table_has_no_level_column(self):
        self.execute_sql('SELECT level FROM agilo_backlog_ticket')
        
        self.perform_upgrade(db7.do_upgrade)
        self.assert_is_invalid_sql('SELECT level FROM agilo_backlog_ticket')
    
    def test_position_is_no_primary_key_for_upgraded_backlog_ticket_table(self):
        self.perform_upgrade(db7.do_upgrade)
        
        self.commit_sql(*self._generate_insert_query(self.sample_row))
        self.sample_row['ticket_id'] = 1
        self.commit_sql(*self._generate_insert_query(self.sample_row))
    
    def test_ticket_id_is_primary_key_for_upgraded_backlog_ticket_table(self):
        self.perform_upgrade(db7.do_upgrade)
        
        self.sample_row['ticket_id'] = 5
        self.commit_sql(*self._generate_insert_query(self.sample_row))
        
        duplicate_insert = lambda: self.commit_sql(*self._generate_insert_query(self.sample_row))
        self.assert_raises_db_exception(('IntegrityError',), duplicate_insert, self.db())
    
    def test_ignore_rows_without_ticket_id(self):
        del self.sample_row['ticket_id']
        self.commit_sql(*self._generate_insert_query(self.sample_row))
        
        # This must not throw an exception
        # (test will always pass for sqlite as sqlite just ignores null values 
        # in unique constraints)
        self.perform_upgrade(db7.do_upgrade)
    
    def test_ignore_tickets_with_multiple_positions(self):
        self.sample_row.update({'pos': 1, 'ticket_id': 5})
        self.commit_sql(*self._generate_insert_query(self.sample_row))
        self.sample_row['pos'] = 2
        self.commit_sql(*self._generate_insert_query(self.sample_row))
        
        # This must not throw an exception
        self.perform_upgrade(db7.do_upgrade)
    

class TestCanUpgradeFromAgilo06EnvironmentWithMissingIndex(TestBacklogTicketTableUpdate):
    
    def set_up_tables(self):
        self.drop_table('agilo_backlog_ticket')
        old_table = Table('agilo_backlog_ticket')[
            Column('name'),
            Column('pos', type='integer'),
            Column('scope'),
            Column('level', type='integer'),
            Column('ticket_id', type='integer')
        ]
        db = self.db()
        create_table_with_cursor(old_table, db.cursor(), self.db_connector())
        db.commit()
    

