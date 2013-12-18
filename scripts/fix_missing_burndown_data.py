# -*- encoding: utf-8 -*-
# In 0.7.0 we had a stupid bug that no remaining time was saved even when the
# Remaining Time was set initially. Now we rely on the storage of the remaining
# time and burndown will look strage if you created tasks with remaining time
# with 0.7.0.
# This script checks all open tasks if they have a remaining time. If they have,
# it checks in the database that at least one remaining time was set. If that is
# not the case, it stores the current remaining time for the day of the ticket's
# creation.


import sys

from trac.env import Environment

from agilo.scrum.burndown import RemainingTime
from agilo.ticket.model import AgiloTicket
from agilo.utils import Key


def get_all_open_tickets(env):
    db = env.get_db_cnx()
    cursor = db.cursor()
    cursor.execute("select id from ticket where status != 'closed'")
    
    tickets = (AgiloTicket(env, tkt_id=row[0], db=db) for row in cursor.fetchall())
    return tickets


def store_initial_remaining_time_if_not_present(env, ticket):
    current_remaining_time = ticket[Key.REMAINING_TIME]
    if current_remaining_time not in [None, '']:
        current_remaining_time = float(current_remaining_time)
        storage = RemainingTime(env, task=ticket)
        if len(storage.history) == 0:
            assert ticket.time_created != None
            storage.set_remaining_time(current_remaining_time, day=ticket.time_created)
            print 'fixed remaining time storage for #%s' % ticket.id


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print 'Usage ', sys.argv[0], ' <environment>'
    else:
        environment_path = sys.argv[1]
        env = Environment(environment_path)
        
        for ticket in get_all_open_tickets(env):
            store_initial_remaining_time_if_not_present(env, ticket)

