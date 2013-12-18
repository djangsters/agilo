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

from agilo.db import create_table_with_cursor
from agilo.utils.db import get_db_type


def do_upgrade(env, ver, cursor, db_connector):
    return DB7(env, cursor, db_connector).upgrade()


class DB7(object):
    def __init__(self, env, cursor, db_connector):
        self.env = env
        self.cursor = cursor
        self.db_connector = db_connector
    
    def upgrade(self):
        self.update_backlog_ticket_table()
        return True
    
    def new_table(self):
        return Table('agilo_backlog_ticket', key=['name', 'scope', 'ticket_id'])[
            Column('name'),
            Column('scope'),
            Column('ticket_id', type='integer'),
            Column('pos', type='integer'),
        ]
    
    def drop_postgres_primary_key(self):
        if get_db_type(self.env) != 'postgres':
            return
        if not self.has_postgres_primary_key('agilo_backlog_ticket_pk'):
            return
        self.cursor.execute('ALTER TABLE agilo_backlog_ticket_old DROP CONSTRAINT agilo_backlog_ticket_pk')
    
    def has_postgres_primary_key(self, constraint_name, schema='tractest'):
        self.cursor.execute("SELECT constraint_name "
                            "FROM information_schema.table_constraints "
                            "WHERE constraint_name='%s' AND constraint_schema = '%s'" % (constraint_name, schema))
        return 0 != len(self.cursor.fetchall())
    
    def delete_items_without_ticket_id(self):
        self.cursor.execute('DELETE FROM agilo_backlog_ticket where ticket_id is NULL')
    
    def copy_values_to_new_table(self):
        seen = dict()
        
        table_argument = {'name': 'agilo_backlog_ticket'}
        self.cursor.execute('SELECT name, pos, ticket_id, scope FROM %(name)s_old' % table_argument)
        for row in self.cursor.fetchall():
            key = (row[0], row[2], row[3])
            if key in seen:
                continue
            sql = """INSERT INTO %(name)s 
                        (name, pos, ticket_id, scope) 
                        VALUES (%%s, %%s, %%s, %%s)""" % table_argument
            self.cursor.execute(sql, row)
            seen[key] = True
    
    def update_backlog_ticket_table(self):
        self.delete_items_without_ticket_id()
        table_name = {'name': 'agilo_backlog_ticket'}
        self.cursor.execute('ALTER TABLE %(name)s RENAME TO %(name)s_old' % table_name)
        self.drop_postgres_primary_key()
        create_table_with_cursor(self.new_table(), self.cursor, self.db_connector)
        self.copy_values_to_new_table()
        self.cursor.execute('DROP TABLE %(name)s_old' % table_name)

