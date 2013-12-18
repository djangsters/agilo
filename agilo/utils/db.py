#   Copyright 2008 Agile42 GmbH, Berlin (Germany)
#   Copyright 2007 Andrea Tomasini <andrea.tomasini_at_agile42.com>
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
#   Author: Andrea Tomasini <andrea.tomasini_at_agile42.com>

from trac.env import Environment
from trac.db import DatabaseManager, Table
from trac.util.translation import _

from agilo.utils.log import debug, warning, error
from agilo.utils.compat import exception_to_unicode


def get_users_last_visits(env, db=None):
    """Returns a list of tuples (username, lastvisit) from the session table"""
    db, handle_ta = get_db_for_write(env, db)
    users = []
    try:
        cursor = db.cursor()
        cursor.execute("SELECT sid, last_visit FROM session WHERE authenticated = 1")
        for row in cursor.fetchall():
            if row and len(row) == 2:
                users.append((row[0], row[1]))
        return users
    except Exception, e:
        warning(env, _("Could not load users from session table: %s" % \
                       exception_to_unicode(e)))

def get_user_attribute_from_session(env, attr, username, db=None):
    """
    Returns the given attribute value if present in the session_attribute
    table, for this team members
    """
    db = get_db_for_read(env, db)
    try:
        cursor = db.cursor()
        cursor.execute("SELECT value FROM session_attribute WHERE sid=%s AND name=%s",
                       [username, attr])
        value = cursor.fetchone()
        if value is not None:
            return value[0]
    except Exception, e:
        warning(env, _("Could not load attribute: %s for TeamMember: %s => %s" % \
                        (attr, username, exception_to_unicode(e))))

def set_user_attribute_in_session(env, attr, value, username, db=None):
    db, handle_ta = get_db_for_write(env, db)
    try:
        cursor = db.cursor()
        if get_user_attribute_from_session(env, attr, username, db=db) is not None:
            cursor.execute("UPDATE session_attribute SET value=%s WHERE sid=%s" \
                           " AND name=%s", [value, username, attr])
        else:
            cursor.execute("INSERT INTO session_attribute (sid, authenticated, name, value)" \
                           " VALUES (%s, %s, %s, %s)", [username, 1, attr, value])
        if handle_ta:
            db.commit()
    except Exception, e:
        if handle_ta:
            db.rollback()
        warning(env, _("Could not store attribute: %s=%s for TeamMember: %s => %s" % \
                        (attr, value, username, exception_to_unicode(e))))

def get_db_for_write(env, db=None):
    """
    Returns a tuple, (db_conn, handle_ta) where handle_ta is True
    in case the connection is generated from the passed environment
    or False in case the passed db is alredy a valid connection
    """
    if db:
        return (db, False)
    else:
        return (env.get_db_cnx(), True)

def get_db_for_read(env, db=None):
    return get_db_for_write(env, db)[0]

def get_null(env, equal=True):
    """
    Return the SQL expression to test NULL for the current database
    type, if equal is True returns a positive check, otherwise a negative
    """
    nulls = {
#             'sqlite':   (' NOT', ' ISNULL'), 
#             'default':  ('!', '=NULL')}
             'default': (' IS NOT NULL', ' IS NULL'),
            }
    t_null = nulls.get(get_db_type(env)) or nulls.get('default')
    if equal:
        return t_null[1]
    else:
        return t_null[0]

def get_db_type(env):
    """Returns the DB type for the given trac Environment"""
    assert isinstance(env, Environment), \
        "env should be an instance of trac.Environment, got %s" % str(env)
    # Get The Databse Manager
    dbm = DatabaseManager(env)
    # Get the Connector Object for the current DB schema
    connector, args = dbm._get_connector()
    
    # Since trac r8582 get_supported_schemes is now a generator so we need to 
    # unroll it first (also to stay compatible with trac < 0.11.6)
    supported_schemes = [i for i in connector.get_supported_schemes()]
    db_type, trans = supported_schemes[0]
    return db_type

def create_table(env, table, conn=None):
    """
    Creates a the given table in the given environment. The Table
    has to be of type trac.db.Table, and the Environment a 
    trac.env.Environment.
    """
    assert isinstance(env, Environment), \
        "[DB]: env should be an instance of trac.env.Environment, got %s" % type(env)
    assert isinstance(table, Table), \
        "[DB]: table should be an instance of trac.sb.Table, got %s" % type(table)
    # Get The Databse Manager
    dbm = DatabaseManager(env)
    # Get the Connector Object for the current DB schema
    connector, args = dbm._get_connector()
    # Ask the connector to generate the proper DDL for the table
    ddl_gen = connector.to_sql(table)
    # Get a DB Connection from the pool, create a cursor and the table
    conn, handle_ta = get_db_for_write(env, conn)
    try:
        cursor = conn.cursor()
        for statement in ddl_gen:
            debug(env, "[DB]: Table: %s\n%s" % (table.name, statement))
            cursor.execute(statement)
        if handle_ta:
            conn.commit()
        debug(env, "[DB]: Successfully Created Table %s" % table.name)
    except Exception, e:
        if handle_ta:
            conn.rollback()
        error(env, "[DB]: Unable to Create Table %s, an error occurred: %s" % \
                    (table.name, exception_to_unicode(e)))
        raise

def create_types(env, type_names, db=None):
    db, handle_ta = get_db_for_write(env, db)
    # Query definitions
    sql_select_type = "SELECT count(*) FROM enum WHERE type = 'ticket_type' AND name = '%s'"
    sql_select_max_value = "SELECT max(value) FROM enum WHERE type = 'ticket_type'"
    sql_insert_type = "INSERT INTO enum (type,name,value) VALUES('ticket_type','%s',%d)"

    # For every default type check, if already in db, otherwise insert it.
    # To consistently insert, we need to know the value of the highest ticket_type entry first.
    cursor = db.cursor()
    cursor.execute(sql_select_max_value)
    ticket_type_max_value = int(cursor.fetchone()[0])
    for t in type_names:
        try:
            cursor.execute(sql_select_type % t)
            if cursor.fetchone()[0] == 0:
                ticket_type_max_value += 1
                debug(env, "ticket_type '%s' not found within table 'enum' - will " \
                      "insert it with value %d..." % (t,ticket_type_max_value))
                # If the type is not present already insert with the next value available
                cursor.execute(sql_insert_type % (t,ticket_type_max_value))
                if handle_ta:
                    db.commit()
            else:
                debug(env, "Found ticket_type '%s' within table 'enum'" % (t))
        except Exception, e:
            if handle_ta:
                db.rollback()
            exception_to_unicode(e)

