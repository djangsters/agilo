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

from copy import copy
from datetime import timedelta

from trac.db import Column, Table
from trac.util.datefmt import to_datetime, to_timestamp

from agilo.config import __CONFIG_PROPERTIES__
from agilo.db import create_table_with_cursor, rename_table_and_drop_all_keys
from agilo.utils import Key, Type
from agilo.utils.config import initialize_config, AgiloConfig
from agilo.utils.db import get_db_type

__all__ = ['do_upgrade']

def recreate_table_with_changed_types(table, cursor, db_connector, 
                                      old_table_name=None, old_column_names=None):
    if old_table_name == None:
        old_table_name = table.name
    temporary_table_name = old_table_name + '_old'
    
    rename_table_and_drop_all_keys(cursor, old_table_name, temporary_table_name)
    create_table_with_cursor(table, cursor, db_connector)
    
    colum_names = [c.name for c in table.columns]
    if old_column_names == None:
        old_column_names = colum_names
    assert len(colum_names) == len(old_column_names)
    col_string = ', '.join(colum_names)
    old_col_string = ', '.join(old_column_names)
    insert_sql  = 'INSERT INTO %s (%s) SELECT %s FROM %s' % (table.name, col_string, old_col_string, temporary_table_name)
    cursor.execute(insert_sql)
    cursor.execute("DROP TABLE %s" % temporary_table_name)



# Upgrade from 0.6 to 0.7RC1
def do_upgrade(env, ver, cursor, db_connector):
    burndown = Table('burndown', key=('task_id', 'day')) [
                Column('task_id', type='integer'),
                Column('day', type='integer'),
                Column('time', type='real'),
               ]
    recreate_table_with_changed_types(burndown, cursor, db_connector)
    sprint_table = _create_new_tables(env, cursor, db_connector)
    _update_permissions(cursor)
    _update_configuration(env)
    # theoretically we have to create the backlogs here because they were added
    # in db version 2 but copying seems to be a waste of time because this 
    # upgrade was done AFTER the release of RC1. So I will just create the 
    # backlogs in db3.
    _create_sprints_for_milestones(env, cursor, sprint_table)
    return True


def _create_new_tables(env, cursor, db_connector):
    backlog = \
        Table('backlog', key=('name'))[
            Column('name'),
            Column('b_type', type='integer'),
            Column('description'),
            Column('ticket_types'),
            Column('sorting_keys'),
            Column('b_strict', type='integer')
        ]
    
    backlog_ticket = \
        Table('backlog_ticket', key=('name', 'pos', 'scope'))[
            Column('name'), # The name of the Backlog
            Column('pos', type='integer'), # The position of the ticket
            Column('scope'), # The scope is the name of a Sprint or a Milestone
            Column('level', type='integer'), # The level in the hierarchy of this ticket
            Column('ticket_id', type='integer') # The id of the ticket
        ]
    
    calendar_entry = \
        Table('calendar_entry', key=('date', 'teammember'))[
            Column('date', type='integer'),
            Column('teammember'),
            Column('hours', type='real'),
        ]
    
    team = \
        Table('team', key=('name'))[
            Column('name'),
            Column('description'),
        ]
    
    team_member = \
        Table('team_member', key=('name'))[
            Column('name'),
            Column('team'),
            Column('description'),
            Column('ts_mon', type='real'),
            Column('ts_tue', type='real'),
            Column('ts_wed', type='real'),
            Column('ts_thu', type='real'),
            Column('ts_fri', type='real'),
            Column('ts_sat', type='real'),
            Column('ts_sun', type='real'),
        ]
    new_tables = [backlog, backlog_ticket, calendar_entry, team, team_member,]
    
    sprint = \
        Table('sprint', key=('name'))[
            Column('name'),
            Column('description'),
            Column('start', type='integer'),
            Column('end', type='integer'),
            Column('milestone'),
            Column('team'),
        ]
    if get_db_type(env) == 'postgres':
        # For PostgreSQL 'end' is a reserved word. Agilo 0.7 before final 
        # (db version 3) therefore were unable to run with PostgreSQL.
        # 
        # But we have to create sprints for every milestone in 0.6 and for that
        # we need a sprint table so we just use the table definition from 
        # 0.7 final here. db3 will take not to recreate the table.
        end_column = sprint.columns[3]
        assert end_column.name == 'end'
        end_column.name = 'sprint_end'
    new_tables.append(sprint)
    
    if get_db_type(env) != 'mysql':
        # In MySQL 'key' is a reserved word. Agilo 0.7 before final 
        # (db version 3) therefore were unable to run with MySQL. So we 
        # just skip the table creation here. db3 will create the table with the
        # correct columns (and fixed column names) for us.
        team_metrics_entry = \
            Table('team_metrics_entry', key=('team', 'sprint', 'key'))[
                Column('team'),
                Column('sprint'),
                Column('key'),
                Column('value', type='real'),
            ]
        new_tables.append(team_metrics_entry)
    
    for table in new_tables:
        create_table_with_cursor(table, cursor, db_connector)
    return sprint



def _fetch_tickets_with_custom_property(cursor, property_name):
    sql = "select id, value from ticket join %(tc)s on ticket.id=%(tc)s.ticket " + \
          "where %(tc)s.name='%propname' and %(tc)s.value is not null" 
    query = sql % dict(tc='ticket_custom', propname=property_name)
    cursor.execute(query)
    return cursor.fetchall()

def _fetch_custom_property(cursor, ticket_id, property_name):
    sql = "select value from ticket join %(tc)s on ticket.id=%(tc)s.ticket " + \
          "where ticket.id=%(ticket_id)d and %(tc)s.name='%(propname)s' and %(tc)s.value is not null"
    query = sql % dict(ticket_id=ticket_id, tc='ticket_custom', 
                       propname=property_name)
    cursor.execute(query)
    row = cursor.fetchone()
    if row != None:
        return row[0]
    return None


def _fetch_tasks_and_stories(cursor):
    tickets_by_milestone = dict()
    
    sql = "select id, milestone from ticket where milestone is not null and milestone != ''"
    cursor.execute(sql)
    for ticket_id, milestone in cursor.fetchall():
        story_points = _fetch_custom_property(cursor, ticket_id, Key.STORY_POINTS)
        remaining_time = _fetch_custom_property(cursor, ticket_id, Key.REMAINING_TIME)
        if story_points != None or remaining_time != None:
            if milestone not in tickets_by_milestone:
                tickets_by_milestone[milestone] = list()
            tickets_by_milestone[milestone].append(ticket_id)
    return tickets_by_milestone


def _get_developer_names(cursor):
    cursor.execute('select distinct owner from ticket where owner is not null')
    developers = dict()
    for row in cursor.fetchall():
        name = row[0]
        if name.strip() != '':
            developers[name] = True
    
    cursor.execute("select distinct value from ticket_custom where name='drp_resources' and value is not null")
    for row in cursor.fetchall():
        resources = row[0].strip()
        if resources != '':
            for resource in resources.split(','):
                resource = resource.strip()
                if len(resource) > 0:
                    developers[resource] = True
    return developers.keys()


def _create_team(cursor):
    team_name = 'Agilo Scrum Team'
    sql = "INSERT INTO team (name) VALUES ('%s')" % team_name
    cursor.execute(sql)
    for name in _get_developer_names(cursor):
        sql = "INSERT INTO team_member (name, team, ts_mon, ts_tue, ts_wed, " + \
              "ts_thu, ts_fri, ts_sat, ts_sun) VALUES ('%s', '%s', 6, 6, 6, 6, 6, 0, 0)" 
        cursor.execute(sql % (name, team_name))
    return team_name


def _create_sprints_for_milestones(env, cursor, sprint_table):
    team_name = _create_team(cursor)
    colum_names = [c.name for c in sprint_table.columns]
    new_sprint_query = ("INSERT INTO sprint (%s) " % ", ".join(colum_names)) + \
                       "VALUES ('%(milestone)s', NULL, %(start)s, %(end)s, '%(milestone)s', '%(team)s')"
    
    tickets_by_milestone = _fetch_tasks_and_stories(cursor)
    cursor.execute('select name, due, duration from milestone where due is not null and duration is not null')
    for milestone_name, due, duration in cursor.fetchall():
        sprint_end = due
        end_date = to_datetime(sprint_end)
        start_date = end_date - timedelta(days=duration) + timedelta(days=2)
        sprint_start = to_timestamp(start_date)
        
        ticket_ids = tickets_by_milestone.get(milestone_name, [])
        if len(ticket_ids) > 0:
            parameters = dict(milestone=milestone_name, start=sprint_start, 
                              end=sprint_end, team=team_name)
            sql = new_sprint_query % parameters
            cursor.execute(sql)
            
            for ticket_id in tickets_by_milestone.get(milestone_name, []):
                sql = "INSERT INTO ticket_custom (ticket, name, value) values (%d, 'sprint', '%s')"
                cursor.execute(sql % (ticket_id, milestone_name))


def _update_configuration(env):
    my_config = copy(__CONFIG_PROPERTIES__)
    del my_config[AgiloConfig.AGILO_LINKS]
    del my_config[AgiloConfig.AGILO_TYPES]
    initialize_config(env, my_config)
    
    config = AgiloConfig(env).tc # Only the trac config wrapper
    _update_agilo_types(config)
    _update_calculated_properties(config, env)


def _update_agilo_types(config):
    section_name = AgiloConfig.AGILO_TYPES
    # sets the autosave to false
    config.auto_save = False
    type_options = config.get_options(section_name).items()
    for option_name, values in type_options:
        if option_name == Type.REQUIREMENT and (Key.KEYWORDS not in values):
            values.append(Key.KEYWORDS)
            config.change_option(option_name, ', '.join(values), section_name)
        elif option_name in (Type.BUG, Type.USER_STORY, Type.TASK):
            if Key.MILESTONE in values:
                values.remove(Key.MILESTONE)
                values.append(Key.SPRINT)
            
            if option_name == Type.USER_STORY and (Key.KEYWORDS not in values):
                values.append(Key.KEYWORDS)
            elif option_name == Type.TASK and (Key.OWNER not in values):
                values.append(Key.OWNER)
            config.change_option(option_name, ', '.join(values), section_name)
    # Save config changes
    config.save()


def _extract_typename(option_name, log):
    typename = None
    parts = option_name[:-len('.calculate')].split('.')
    if len(parts) != 2:
        log.error(u'Skipping migration of %s: Unexpected format' % option_name)
    else:
        typename = parts[0]
    return typename


def _update_formula(option_name, value, log):
    parts = value.split('=')
    if len(parts) != 2:
        msg = u'Skipping migration of %s: Unexpected formula format %s'
        log.error(msg % (option_name, value))
        return None
    calculated_property_name, calculation = parts
    calculated_property_name = calculated_property_name.strip()
    
    calculation = calculation.strip()
    parts = calculation.split(':')
    if len(parts) != 2:
        msg = u'Skipping migration of %s: Unexpected formula %s for property %s'
        log.error(msg % (option_name, calculation, calculated_property_name))
        return None
    operator_name = parts[0].strip()
    if operator_name != 'sum':
        msg = u'Skipping migration of %s: Unknown operator %s for property %s'
        log.error(msg % (option_name, calculation, calculated_property_name))
        return None
    property_name = parts[1].strip()
    new_formula = '%s=%s:get_outgoing.%s' % (calculated_property_name, operator_name, property_name)
    return new_formula


def _extract_formulas(option_name, values, log):
    formulas = []
    for value in values:
        new_formula = _update_formula(option_name, value, log)
        formulas.append(new_formula)
    return formulas


def _add_formulas(config, typename, new_formulas, section=None):
    option_name = '%s.calculate' % typename
    formulas = config.get_list(option_name, section=section)
    formulas += new_formulas
    config.change_option(option_name, ', '.join(formulas), section=section)


def _update_calculated_properties(config, env):
    section_name = AgiloConfig.AGILO_LINKS
    type_options = config.get_options(section_name).items()
    for option_name, values in type_options:
        if option_name.endswith('.calculate'):
            typename = _extract_typename(option_name, env.log)
            if typename == None:
                continue
            formulas = _extract_formulas(option_name, values, env.log)
            
            option_name = '%s.calculate' % typename
            config.change_option(option_name, ', '.join(formulas), section=section_name)
    
    # AT: I leave here the strings and I don't replace with constants because it
    # will make the formulas difficult to read, but it is a place to keep in mind
    # when changing something.
    formulas = ['total_story_points=sum:get_outgoing.rd_points|type=story',
                'mandatory_story_points=sum:get_outgoing.rd_points|type=story|story_priority=Mandatory',
                'roif=div:businessvalue;mandatory_story_points']
    _add_formulas(config, Type.REQUIREMENT, formulas, section=section_name)
    
    formulas = ['estimated_remaining_time=mul:rd_points;get_sprint.get_team_metrics.rt_usp_ratio']
    _add_formulas(config, Type.USER_STORY, formulas, section=section_name)
    
    formulas = ['summed_time=sum:remaining_time;actual_time']
    _add_formulas(config, Type.TASK, formulas, section=section_name)


def _update_permissions(cursor):
    sql = "update permission set action='SCRUM_MASTER' where action='DRP_SCRUMASTER'"
    cursor.execute(sql)
    sql = "update permission set action='TEAM_MEMBER' where action='DRP_TEAM_MEMBER'"
    cursor.execute(sql)
    sql = "update permission set action='PRODUCT_OWNER' where action='DRP_REQUIREMENT'"
    cursor.execute(sql)


