####### WARNING THIS IS NOT A TEST IS HERE ONLY AS A REMINDER ########

from trac.db import DatabaseManager, Table, Column
from trac.test import EnvironmentStub

from agilo.utils import Key

def test_db_table():
    # Create a EnvironmentStub
    env = EnvironmentStub()
    
    # Create a test table
    table = Table('test', key=['id'])[
        Column('id', type='integer'),
        Column(Key.NAME, type='text')
    ]
    # Get The Databse Manager
    dbm = DatabaseManager(env)
    # Get the Connector Object for the current DB schema
    connector, args = dbm._get_connector()
    # Ask the connector to generate the proper DDL for the table
    ddl_gen = connector.to_sql(table)
    # Get a DB Connection from the pool, create a cursor and the table
    conn = dbm.get_connection()
    try:
        cursor = conn.cursor()
        for statement in ddl_gen:
            print "Table: %s\n%s" % (table.name, statement)
            cursor.execute(statement)
        conn.commit()
        print "Successfully Created Table %s" % table.name
    except Exception, e:
        conn.rollback()
        print "[ERROR]: Unable to Create Table %s, an error occurred: %s" % \
                      (table.name, str(e))
    # Now try to do something with the table...
    try:
        cursor = conn.cursor()
        cursor.execute('INSERT INTO test (id, name) VALUES (1, "Name me how you want")')
        conn.commit()
        print "Successfully Inserted 1 row"
    except Exception, e:
        conn.rollback()
        print "[ERROR]: An error occurred: %s" % \
                      (table.name, str(e))

if __name__ == '__main__':
    test_db_table()