# -*- encoding: utf-8 -*-
#   Copyright 2008-2009 Agile42 GmbH, Berlin (Germany)
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
#   Authors: 
#       - Andrea Tomasini <andrea.tomasini_at_agile42.com>

from agilo import AGILO_TABLE_PREFIX

SPRINT_TABLE = AGILO_TABLE_PREFIX + 'sprint'
SPRINT_URL = '/sprint'

BACKLOG_TABLE = AGILO_TABLE_PREFIX + 'backlog'
BACKLOG_TICKET_TABLE = AGILO_TABLE_PREFIX + 'backlog_ticket'
BACKLOG_URL = '/backlog'

BURNDOWN_TABLE = AGILO_TABLE_PREFIX + 'burndown'

TEAM_TABLE = AGILO_TABLE_PREFIX + 'team'
TEAM_URL = '/team'

TEAM_MEMBER_TABLE = AGILO_TABLE_PREFIX + 'team_member'
TEAM_MEMBER_URL = '/team_member'
TEAM_MEMBER_CALENDAR_TABLE = AGILO_TABLE_PREFIX + 'team_member_calendar'

DASHBOARD_URL = '/dashboard'

# Import all so that Models are not directly visible, this should allow to keep
# the architecture safe as far as the others modules are importing from __init__
from agilo.scrum.team import *
from agilo.scrum.sprint import *
from agilo.scrum.contingent import *
from agilo.scrum.backlog import *
from agilo.scrum.burndown import *
from agilo.scrum.metrics import *
