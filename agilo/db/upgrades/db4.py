# -*- encoding: utf-8 -*-
#   Copyright 2009 Agile42 GmbH, Berlin (Germany)
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

from datetime import datetime

from trac.db import Column, Table
from trac.util.datefmt import localtz, to_timestamp

from agilo.db.upgrades.db2 import recreate_table_with_changed_types
from agilo.utils.config import AgiloConfig

__all__ = ['do_upgrade']

# Upgrade from 0.7 to 0.8
def do_upgrade(env, ver, cursor, db_connector):
    _rename_burndown_columns(cursor, db_connector)
    _convert_ordinals_to_timestamps(cursor)
    _reset_properly_query_and_report_modules(env)
    return True


def _rename_burndown_columns(cursor, db_connector):
    burndown = Table('agilo_burndown', key=('task_id', 'date')) [
                    Column('task_id', type='integer'),
                    Column('date', type='integer'),
                    Column('remaining_time', type='real'),
               ]
    recreate_table_with_changed_types(burndown, cursor, db_connector, 
                                      old_column_names=['task_id', 'day', 'time'])


def _convert_ordinals_to_timestamps(cursor):
    # In Agilo 0.7 we only stored ordinals (no time, no timezone information)
    # so this conversion can not be perfect. We just assume that the time is 
    # stored at midnight in the local server timezone.
    converted_data = []
    cursor.execute('SELECT task_id, date, remaining_time FROM agilo_burndown')
    for row in cursor.fetchall():
        task_id, day_ordinal, remaining_time = row
        local_midnight_date = datetime.fromordinal(day_ordinal).replace(tzinfo=localtz)
        converted_data.append((task_id, local_midnight_date, remaining_time))
    cursor.execute('DELETE FROM agilo_burndown')
    
    base_sql = 'INSERT INTO agilo_burndown (task_id, date, remaining_time) VALUES '
    for task_id, date, remaining_time in converted_data:
        value_sql = '(%s)' % ', '.join(map(str, (task_id, to_timestamp(date), remaining_time)))
        cursor.execute(base_sql + value_sql)


def _reset_properly_query_and_report_modules(env):
    # Reset the properties of query module and report in the trac.ini, in old
    # agilo was required to remove the original from trac, now we have to make
    # sure that they are reset again, cause the patching is done in AgiloConfig.
    ac = AgiloConfig(env)
    components = ac.get_section('components')
    # even if they would be set to enabled, removing them wouldn't change the
    # behavior
    components.remove_option('trac.ticket.query.querymodule')
    components.remove_option('trac.ticket.report.reportmodule')
    components.save()