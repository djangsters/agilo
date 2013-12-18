# -*- encoding: utf-8 -*-
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
#   
#   Authors: 
#       - Andrea Tomasini <andrea.tomasini_at_agile42.com>

# Database version identifier. Used for automatic upgrades.
db_version = 7

from trac.db import Column, Table

from agilo.scrum import BURNDOWN_TABLE
from agilo.scrum.backlog import BacklogType
from agilo.scrum.backlog.backlog_config import BacklogConfiguration
from agilo.ticket.links import LINKS_TABLE
from agilo.utils import Key, Type
from agilo.utils.db import create_types


# Tables which don't belong to persistent objects
schema = [
    Table(LINKS_TABLE, key=['src', 'dest'])[
        Column('src', type='integer'),  # The ticket id of the source of the link
        Column('dest', type='integer')  # The ticket id of the destination of the link
    ],
    # Table Burndown
    Table(BURNDOWN_TABLE, key=['task_id', 'date']) [
        Column('task_id', type='integer'),
        Column('date', type='integer'),
        Column('remaining_time', type='real')
    ],
]

def is_environment_stub(env):
    # We must not import trac.test in non-testing code - Fedora's package does
    # not ship trac.test in the main trac package.
    return env.__class__.__name__ in ('EnvironmentStub', 'BetterEnvironmentStub')

def notify_user(message, env):
    if is_environment_stub(env):
        return
    print message

# If you adapt/change these backlog definitions, you have to copy the setup 
# routine into db3 and create an upgrade method in db[4+]
def create_default_backlogs(env):
    """Creates the default Backlog for Product Backlog and Sprint 
    Backlog"""
    # AT: we can now just try to create it, if it is already existing
    # nothing will happen
    notify_user("Creating Product Backlog...", env)
    product_backlog = BacklogConfiguration(env, name=Key.PRODUCT_BACKLOG)
    product_backlog.ticket_types = [Type.REQUIREMENT, Type.USER_STORY]
    product_backlog.save()
    
    notify_user("Creating Sprint Backlog...", env)
    sprint_backlog = BacklogConfiguration(env, name=Key.SPRINT_BACKLOG)
    sprint_backlog.type = BacklogType.SPRINT
    sprint_backlog.ticket_types = [Type.REQUIREMENT, Type.USER_STORY, 
                                   Type.TASK, Type.BUG]
    sprint_backlog.save()
    
def create_default_types(env):
    default_types = (Type.REQUIREMENT, Type.USER_STORY, Type.TASK, 
                     Type.BUG)
    create_types(env, default_types)

