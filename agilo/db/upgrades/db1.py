#   Copyright 2008 agile42 GmbH
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


__all__ = ['do_upgrade']

# Upgrade from pre-0.6 to 0.6
def do_upgrade(env, ver, cursor, db_connector):
    link_table = Table('link', key=('src', 'dest'))[
        Column('src', type='integer'),
        Column('dest', type='integer')
    ]
    
    create_table_with_cursor(link_table, cursor, db_connector)
    return True




