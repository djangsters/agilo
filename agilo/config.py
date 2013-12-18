# -*- encoding: utf-8 -*-
#   Copyright 2010 Agile42 GmbH, Berlin (Germany)
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

from agilo.ticket.links import LinkOption
from agilo.scrum.charts import ChartType
from agilo.utils import Key, Type
from agilo.utils.config import AgiloConfig

# Attention: If you modify the __CONFIG_PROPERTIES__, please copy the old 
# definition to db3 and build an upgrade path (if necessary in db4).
# Felix Schwarz 28.10.2008: It seemed not useful to me just duplicating this 
# long thing in db3.

# REFACT: '__CONFIG_PROPERTIES__' should be renamed, it has nothing to do with the object protocol
# List of properties by section that should be created into the trac.ini.
# Values beginning with "+" will be prepended to the existing value as a list
__CONFIG_PROPERTIES__ = {
    'trac': {'permission_policies' : '+AgiloPolicy'},
    'header_logo': {'src': 'agilo/images/default_logo.png'}
}

# This section configure the [components] of agilo in the trac.ini
__CONFIG_PROPERTIES__['components'] = {
    'trac.ticket.api.ticketsystem': 'disabled',
    'trac.ticket.web_ui.ticketmodule': 'disabled',
    'trac.ticket.roadmap.roadmapmodule': 'disabled',
}

# REFACT: extract method to create one custom field (could be re-used in AgiloConfig)
# This is the trac.ini [ticket-custom] section
__CONFIG_PROPERTIES__[AgiloConfig.TICKET_CUSTOM] = {
    Key.INCOMING_LINKS: 'text', 
    '%s.label' % Key.INCOMING_LINKS: 'Referenced By',
    Key.OUTGOING_LINKS: 'text',
    '%s.label' % Key.OUTGOING_LINKS: 'References',
    Key.REMAINING_TIME: 'text',
    Key.STORY_POINTS: 'select',
    Key.STORY_POINTS + '.label': 'Story Points',
    Key.STORY_POINTS + '.options': '|0|1|2|3|5|8|13|20|40|100',
    Key.REMAINING_TIME: 'text',
    Key.REMAINING_TIME + '.label': 'Remaining Time',
    Key.STORY_PRIORITY: 'select',
    Key.STORY_PRIORITY + '.label': 'Importance',
    Key.STORY_PRIORITY + '.options': '|Mandatory|Linear|Exciter',
    Key.STORY_PRIORITY + '.value': '',
    Key.BUSINESS_VALUE: 'select',
    Key.BUSINESS_VALUE + '.label': 'Business Value',
    Key.BUSINESS_VALUE + '.options': '|100|200|300|500|800|1200|2000|3000',
    Key.BUSINESS_VALUE + '.value': '',
    Key.SPRINT: 'select',
    Key.SPRINT + '.value': '',
    Key.SPRINT + '.label': 'Sprint',
    Key.RESOURCES: 'text',
    Key.RESOURCES + '.label': 'Resources',
    # No options are set for Sprint because it will be dynamically loaded
}

def join_keys(*keys):
    return '.'.join(keys)

def join_values(*values):
    return ', '.join(values)

# This is the trac.ini [agilo-links] section
__CONFIG_PROPERTIES__[AgiloConfig.AGILO_LINKS] = {
    'allow': '%(req)s-%(story)s, %(story)s-%(task)s, %(bug)s-%(task)s, %(bug)s-%(story)s' % \
              {'req': Type.REQUIREMENT, 'story': Type.USER_STORY, 'bug': Type.BUG, 'task': Type.TASK},
    join_keys(Type.REQUIREMENT, Type.USER_STORY, LinkOption.COPY): 
                    Key.OWNER,
    join_keys(Type.REQUIREMENT, Type.USER_STORY, LinkOption.SHOW): 
                    join_values(Key.STORY_POINTS, Key.STORY_PRIORITY),
    join_keys(Type.REQUIREMENT, LinkOption.CALCULATE): 
                    ('total_story_points=sum:get_outgoing.%s|type=story,' % Key.STORY_POINTS) + \
                    ('mandatory_story_points=sum:get_outgoing.%s|type=story|%s=Mandatory,' % \
                     (Key.STORY_POINTS, Key.STORY_PRIORITY)) + \
                    ('roif=div:%s;%s' % (Key.BUSINESS_VALUE, 'mandatory_story_points')),
    join_keys(Type.USER_STORY, Type.TASK, LinkOption.COPY): 
                    join_values(Key.OWNER, Key.SPRINT),
    join_keys(Type.USER_STORY, Type.TASK, LinkOption.SHOW): 
                    join_values(Key.OWNER, Key.REMAINING_TIME),
    join_keys(Type.USER_STORY, LinkOption.CALCULATE): \
                  ('total_remaining_time=sum:get_outgoing.%s' % Key.REMAINING_TIME) + ',' + \
                  ('estimated_remaining_time=mul:%s;get_sprint.get_team_metrics.%s' % \
                   (Key.STORY_POINTS, Key.RT_USP_RATIO) ),
    join_keys(Type.BUG, Type.TASK, LinkOption.COPY): join_values(Key.OWNER, Key.SPRINT),
    join_keys(Type.BUG, Type.TASK, LinkOption.SHOW): join_values(Key.OWNER, Key.REMAINING_TIME),
    join_keys(Type.BUG, LinkOption.CALCULATE): \
                  'total_remaining_time=sum:get_outgoing.%s' % Key.REMAINING_TIME,
    'cache.timeout': '0',
    'cache.related': 'false', # Now disable cache by default, to many problems with 2 CPU
}

# This is the trac.ini [agilo-types] section
__CONFIG_PROPERTIES__[AgiloConfig.AGILO_TYPES] = {
    Type.REQUIREMENT:                       join_values(Key.REPORTER, Key.BUSINESS_VALUE, Key.MILESTONE, Key.KEYWORDS),
    join_keys(Type.REQUIREMENT, Key.ALIAS): 'Requirement',
    Type.USER_STORY:                        join_values(Key.OWNER, Key.SPRINT, Key.STORY_POINTS, Key.STORY_PRIORITY, Key.KEYWORDS),
    join_keys(Type.USER_STORY, Key.ALIAS):  'User Story',
    Type.TASK:                              join_values(Key.OWNER, Key.SPRINT, Key.REMAINING_TIME, Key.RESOURCES),
    join_keys(Type.TASK, Key.ALIAS):        'Task',
    Type.BUG:                               join_values(Key.OWNER, Key.SPRINT, Key.PRIORITY),
    join_keys(Type.BUG, Key.ALIAS):         'Bug',
}

# This is the trac.ini [agilo-backlogs] section
__CONFIG_PROPERTIES__[AgiloConfig.AGILO_BACKLOGS] = {
    'product_backlog.name': 'Product Backlog',
    'product_backlog.columns': join_values('%s:editable' % Key.BUSINESS_VALUE,
                                          Key.ROIF,
                                          '%s:editable' % Key.STORY_PRIORITY,
                                          '%s:editable|total_story_points' % Key.STORY_POINTS),
    'sprint_backlog.name': 'Sprint Backlog',
    'sprint_backlog.columns': join_values('%s:editable|total_remaining_time' % Key.REMAINING_TIME,
                                         '%s:editable' % Key.OWNER, 
                                         '%s:editable' % Key.RESOURCES),
    'sprint_backlog.charts': ChartType.BURNDOWN
}
