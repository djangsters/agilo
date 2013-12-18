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
#
#   Authors: 
#         - Robert Buchholz <robert.buchholz__at__agile42.com>

__all__ = ['do_upgrade']

# Upgrade from 0.8.4.2 to 0.8.4.3
def do_upgrade(env, ver, cursor, db_connector):
    _rename_contingent_permissions(cursor)
    return True

def _rename_contingent_permissions(cursor):
    rename_sql = r"UPDATE permission SET action='%s' WHERE action='%s'"
    permission_map = { 'AGILO_ADD_TIME_FOR_CONTINGENT' : 'AGILO_CONTINGENT_ADD_TIME',
                       'AGILO_MODIFY_CONTINGENTS' :'AGILO_CONTINGENT_ADMIN', }
    
    for from_perm, to_perm in permission_map.iteritems():
        cursor.execute(rename_sql % (to_perm, from_perm))

