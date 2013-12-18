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

from trac.db import Column, Table

from agilo.db import create_table_with_cursor, rename_table
from agilo.db.upgrades.db2 import recreate_table_with_changed_types
from agilo.db.db_default import create_default_backlogs, create_default_types
from agilo.utils.db import get_db_type

__all__ = ['do_upgrade']

# Upgrade from 0.7RC1 to 0.7 final
def do_upgrade(env, ver, cursor, db_connector):
    _create_new_tables(cursor, db_connector)
    _rename_column_end_in_sprint_table(env, cursor, db_connector)
    _rename_column_key_in_team_metrics_entry(env, cursor, db_connector)
    _remove_views_which_depend_on_link_table(env, cursor)
    _prefix_all_tables_with_agilo(cursor)
    
    # If the backlog definition is changed, you have to copy the old definition
    # in here. See the comment in db2 for more information.
    create_default_backlogs(env)
    create_default_types(env)
    return True


def _create_new_tables(cursor, db_connector):
    contingent = \
        Table('agilo_contingent', key=('name', 'sprint'))[
            Column('name'),
            Column('sprint'),
            Column('amount', type='real'),
            Column('actual', type='real'),
        ]
    create_table_with_cursor(contingent, cursor, db_connector)


def _prefix_all_tables_with_agilo(cursor):
    old_tables_names = ['backlog', 'backlog_ticket', 'burndown', 
                        'calendar_entry', 'link', 'sprint', 'team', 
                        'team_member', 'team_metrics_entry']
    for table_name in old_tables_names:
        rename_table(cursor, table_name, 'agilo_' + table_name)


def _remove_views_which_depend_on_link_table(env, cursor):
    if get_db_type(env) == 'postgres':
        # These views were created by Agilo 0.6. As they create references to
        # the link table, we can not prefix it with 'agilo_' later. These views
        # are not needed for Agilo 0.7 so we just drop them.
        cursor.execute('DROP VIEW aggregated_user_stories')
        cursor.execute('DROP VIEW aggregated_rt')


def _rename_column_end_in_sprint_table(env, cursor, db_connector):
    if get_db_type(env) != 'postgres':
        # Agilo 0.7 before final (db version 3) was unable to run with 
        # PostgreSQL. As we need the sprint table in db2 already, we had to 
        # create it with the new table layout. Therefore we don't change the
        # postgres table here.
        sprint = \
            Table('sprint', key=('name'))[
                Column('name'),
                Column('description'),
                Column('start', type='integer'),
                Column('sprint_end', type='integer'),
                Column('milestone'),
                Column('team'),
            ]
        old_sprint_column_names = ['name', 'description', 'start', 'end', 
                                   'milestone', 'team']
        recreate_table_with_changed_types(sprint, cursor, db_connector, 
                                          old_column_names=old_sprint_column_names)


def _rename_column_key_in_team_metrics_entry(env, cursor, db_connector):
    team_metrics_entry = \
        Table('team_metrics_entry', key=('team', 'sprint', 'metrics_key'))[
            Column('team'),
            Column('sprint'),
            Column('metrics_key'),
            Column('value', type='real'),
        ]
    if get_db_type(env) == 'mysql':
        # Agilo 0.7 before final (db version 3) was unable to run with 
        # MySQL. So the table could not be created in db version 2. 
        # Therefore we can just create a new one.
        create_table_with_cursor(team_metrics_entry, cursor, db_connector)
    else:
        old_team_metrics_entry_colum_names = ['team', 'sprint', 'key', 'value']
        recreate_table_with_changed_types(team_metrics_entry, cursor, db_connector, 
                                          old_column_names=old_team_metrics_entry_colum_names)


