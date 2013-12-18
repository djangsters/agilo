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
#
#   Authors: 
#         - Felix Schwarz <felix.schwarz__at__agile42.com>


__all__ = ['create_table_with_cursor', 'rename_table', 
           'rename_table_and_drop_all_keys']

def drop_table(cursor, table_name):
    cursor.execute('DROP TABLE %s' % table_name)

def create_table_with_cursor(table, cursor, db_connector):
    for sql_statement in db_connector.to_sql(table):
        cursor.execute(sql_statement)


def rename_table(cursor, old_table_name, new_table_name):
    sql = 'ALTER TABLE %s RENAME TO %s' % (old_table_name, new_table_name)
    cursor.execute(sql)


def rename_table_and_drop_all_keys(cursor, old_table_name, new_table_name):
    """If we just want to recreate the table with different types or change 
    columns, we need to rename the table because SQlite can not modify columns
    in existing tables. 
    But in Postgres, names for primary key constraints must be unique and they 
    keep their old name if you just rename a table. So we need a utility 
    function like that one which just moves the data to a temporary table and
    removes all primary keys etc. in the process.
    """
    sql = 'CREATE TABLE %s AS SELECT * FROM %s' % (new_table_name, old_table_name)
    cursor.execute(sql)
    cursor.execute('DROP TABLE %s' % old_table_name)


