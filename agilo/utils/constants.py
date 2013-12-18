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

from trac.util.translation import _

__all__ = ['controls', 'Action', 'BacklogType', 'Key', 'MANDATORY_FIELDS',
           'Realm', 'Role', 'Status', 'Type']

# Labels and Titles for Agilo Controls
controls = {
    # Top button bar
    'show':         dict(label=_('Show My Tickets'),        title=_('Show all tickets assigned or owned by the current user')),
    'hide_hide':    dict(label=_('Hide Closed Tickets'),    title=_('Hide or Show tickets that are closed or done')),
    'hide_show':    dict(label=_('Show Closed Tickets'),    title=_('Hide or Show tickets that are closed or done')),
    # Sprint Table
    'sprint_cb':    dict(label=_(''),                       title=_('Select this ticket for deletion')),
    'remaining':    dict(label=_('Remaining Time'),         title=_('Enter the amount of remaining hours for this task')),
    'owner':        dict(label=_('Owner'),                  title=_('Select the Owner of this task')),
    'resources':    dict(label=_('Resources'),              title=_('Enter other people working on this task, separated by commas')),
    # Backlog Button bar
    'save':         dict(label=_('Save Changes'),           title=_('Save all changes made to the tickets')),
    'sort':         dict(label=_('Default Sorting'),        title=_('Sort the Backlog based on chosen keys (see admin for more details)')),
    # Tickets Button bar
    'delete':       dict(label=_('Delete Selected'),        title=_('Delete the checked tickets completely')),
    'remove':       dict(label=_('Remove Selected'),        title=_('Remove the checked tickets from this Backlog, if not global')),
    # Planning Button bar
    'calculate':    dict(label=_('Calculate Story Points/Time'), title=_('Extrapolate hours from User Story Points and uses the factor to recalculate the Burndown')),
    'confirm':      dict(label=_('Confirm Commitment'),     title=_('Confirm the Sprint commitment')),
    # Sprint Contingents
    'add':          dict(label=_('Add'),                    title=_('Add the filled in Contingent')),
    'remove_cb':    dict(label=_(''),                       title=_('Select a Contingent to remove')),
    'contingent':   dict(label=_('Contingent'),             title=_('Name for the Contingent')),
    'amount':       dict(label=_('Amount'),                 title=_('Contingent length in hours')),
    'actual':       dict(label=_('Actual'),                 title=_('Add extra hours to a Contingent')),
    'removesel':    dict(label=_('Remove Selected Items'),  title=_('Remove checked Contingents')),
    'addtoactual':  dict(label=_('Add to Actual Time'),     title=_('Add Actual Hours to the Contingent Amount')),
    # Product Backlog
    'bv_sel':       dict(label=_('Business Value Points'),  title=_('Select the relative value of this Requirement')),
    'prio_sel':     dict(label=_('Priority'),               title=_('Select the Priority of this Requirement')),
    'us_sel':       dict(label=_('User Story Points'),      title=_('Select the relative complexity of this User Story')),
    # Roadmap
    'addsprint':    dict(label=_('Add New Sprint'),         title=_('Add a new Sprint to this Milestone')),
    'addmilestone': dict(label=_('Add New Milestone'),      title=_('Add a new Milestone')),
    }


class Key(object):
    ACTION = 'action'
    ACTUAL_TIME = 'actual_time'
    AGILO_TICKET = 'agilo_ticket'
    ALIAS = 'alias'
    ALTERNATIVE = 'alternative'
    AUTHOR = 'author'
    BACKLOG_NAME = 'backlog_name'
    BUSINESS_VALUE = 'businessvalue'
    CAPACITY = 'capacity'
    COLS = 'cols'
    COMMITMENT = 'commitment'
    COMPONENT = 'component'
    CUSTOM = 'custom'
    DATE = 'date'
    DEFAULT_HEIGHT = 'default_height'
    DEFAULT_WIDTH = 'default_width'
    DESCRIPTION = 'description'
    DISABLED = 'disabled'
    DURATION = 'duration'
    ESTIMATED_REMAINING_TIME = 'estimated_remaining_time'
    ESTIMATED_TIME = 'estimated_time'
    ESTIMATED_VELOCITY = 'estimated_velocity'
    FIELDS = 'fields'
    GLOBAL = 'global'
    HEIGHT = 'height'
    ID = 'id'
    INCOMING_LINKS = 'i_links'
    KEYWORDS = 'keywords'
    LABEL = 'label'
    LEVEL = 'level' # Used in Backlog
    MILESTONE = 'milestone'
    NAME = 'name'
    OPTIONAL = 'optional'
    OPTIONS = 'options'
    OPTIONS_GROUP = 'optgroups'
    ORDER = 'order'
    OUTGOING_LINKS = 'o_links'
    OWNER = 'owner'
    PANE = 'pane'
    POS = 'pos'
    PRIORITY = 'priority'
    PRODUCT_BACKLOG = 'Product Backlog'
    ROIF = 'roif'
    REMAINING_TIME = 'remaining_time'
    REMAINING_POINTS = 'remaining_points'
    RENDERED = 'rendered'
    REPORTER = 'reporter' # Often used as Stakeholder
    RESOLUTION = 'resolution'
    RESOURCES = 'drp_resources'
    ROWS = 'rows'
    RT_USP_RATIO = 'rt_usp_ratio'
    SCOPE = 'scope'
    SELECT = 'select'
    SHOW = 'show'
    SKIP = 'skip'
    SPRINT = 'sprint'
    SPRINT_BACKLOG = 'Sprint Backlog'
    START = 'start'
    STATUS = 'status'
    STOP = 'stop'
    STORY_PRIORITY = 'story_priority'
    STORY_POINTS = 'rd_points'
    SUMMARY = 'summary'
    TABLE = 'table'
    TASK_ID = 'task_id'
    TEAM = 'team'
    TICKET = 'ticket'
    TICKET_TYPES = 'ticket_types'
    TIME_CREATED = 'time'
    TIME_LAST_CHANGED = 'changetime'
    TO_POS = 'to_pos'
    TOTAL_REMAINING_TIME = 'total_remaining_time'
    TYPE = 'type'
    # Constant for the use days for time estimations
    USE_DAYS = 'use_days_for_time'
    VALUE = 'value'
    VELOCITY = 'velocity'
    WARNINGS = 'warnings'
    WIDTH = 'width'


class Type(object):
    """
    Class grouping all the needed types string definition needed for
    Agilo.
    """
    BUG = 'bug'
    IDEA = 'idea'
    IMPEDIMENT = 'impediment'
    REQUIREMENT = 'requirement'
    TASK = 'task'
    USER_STORY = 'story'


class BacklogType(object):
    GLOBAL = 0     # The Backlog is valid for the whole project database
    SPRINT = 1     # The Backlog requires a Sprint parameter
    MILESTONE = 2  # The Backlog requires a Milestone parameter
    LABELS = { # No unicode here, they can be used as key for a dictionary.
               0 : 'global',
               1 : 'sprint',
               2 : 'milestone',
               }


class Action(object):
    """Class grouping all actions needed for Agilo"""
    ATTACHMENT_CREATE = 'ATTACHMENT_CREATE'
    ATTACHMENT_VIEW = 'ATTACHMENT_VIEW'
    BACKLOG_ADMIN = 'AGILO_BACKLOG_ADMIN'
    BACKLOG_EDIT = 'AGILO_BACKLOG_EDIT'
    BACKLOG_VIEW = 'AGILO_BACKLOG_VIEW'
    BROWSER_VIEW = 'BROWSER_VIEW'
    CHANGESET_VIEW = 'CHANGESET_VIEW'
    CONFIRM_COMMITMENT = 'AGILO_CONFIRM_COMMITMENT'
    CONTINGENT_ADD_TIME = 'AGILO_CONTINGENT_ADD_TIME'
    CONTINGENT_ADMIN = 'AGILO_CONTINGENT_ADMIN'
    CREATE_BUG = 'AGILO_CREATE_BUG'
    CREATE_REQUIREMENT = 'AGILO_CREATE_REQUIREMENT'
    CREATE_STORY = 'AGILO_CREATE_STORY'
    CREATE_TASK = 'AGILO_CREATE_TASK'
    DASHBOARD_VIEW = 'AGILO_DASHBOARD_VIEW'
    EMAIL_VIEW = 'EMAIL_VIEW'
    LOG_VIEW = 'LOG_VIEW'
    LINK_EDIT = 'AGILO_LINK_EDIT'
    MILESTONE_CREATE = 'MILESTONE_CREATE'
    MILESTONE_MODIFY = 'MILESTONE_MODIFY'
    MILESTONE_VIEW = 'MILESTONE_VIEW'
    REPORT_VIEW = 'REPORT_VIEW'
    REPORT_ADMIN = 'REPORT_ADMIN'
    ROADMAP_VIEW = 'ROADMAP_VIEW'
    SAVE_REMAINING_TIME = 'AGILO_SAVE_REMAINING_TIME'
    SEARCH_VIEW = 'SEARCH_VIEW'
    SPRINT_ADMIN = 'AGILO_SPRINT_ADMIN'
    SPRINT_EDIT = 'AGILO_SPRINT_EDIT'
    SPRINT_VIEW = 'AGILO_SPRINT_VIEW'
    TEAM_CAPACITY_EDIT = 'AGILO_TEAM_CAPACITY_EDIT'
    TEAM_VIEW = 'AGILO_TEAM_VIEW'
    TICKET_ADMIN = 'TICKET_ADMIN'
    TICKET_APPEND = 'TICKET_APPEND'
    TICKET_CHANGE = 'TICKET_CHGPROP'
    TICKET_CREATE = 'TICKET_CREATE'
    TICKET_DELETE = 'TICKET_DELETE'
    TICKET_EDIT = 'AGILO_TICKET_EDIT'
    TICKET_EDIT_DESCRIPTION = 'TICKET_EDIT_DESCRIPTION'
    TICKET_EDIT_PAGE_ACCESS = 'AGILO_TICKET_EDIT_PAGE_ACCESS'
    TICKET_MODIFY = 'TICKET_MODIFY'
    TICKET_VIEW = 'TICKET_VIEW'
    TIMELINE_VIEW = 'TIMELINE_VIEW'
    TRAC_ADMIN = 'TRAC_ADMIN'
    WIKI_VIEW = 'WIKI_VIEW'


class Role(object):
    """Constants defining the roles used in Agilo. Aggregates certain actions
    that the Role is allowed to do. The constant name defines the permission
    that a user must have to inhabit this role."""
    BASIC_PERMISSIONS = [
        Action.ATTACHMENT_VIEW,
        Action.BACKLOG_VIEW,
        Action.DASHBOARD_VIEW,
        Action.EMAIL_VIEW,
        Action.MILESTONE_VIEW,
        Action.REPORT_VIEW,
        Action.ROADMAP_VIEW,
        Action.SEARCH_VIEW,
        Action.SPRINT_VIEW,
        Action.TEAM_VIEW,
        Action.TICKET_VIEW,
        Action.TIMELINE_VIEW,
        Action.WIKI_VIEW,
        # Edit permissins
        Action.ATTACHMENT_CREATE,
        Action.TICKET_CREATE, # Needed to create a ticket
        Action.TICKET_CHANGE, # Needed to change any ticket at all
        Action.TICKET_MODIFY, # Needed to be able to change status
        Action.TICKET_APPEND,
        Action.TICKET_EDIT,
        Action.TICKET_EDIT_DESCRIPTION,
        ]
    TICKET_ADMIN = 'TICKET_ADMIN'
    TICKET_ADMIN_ACTIONS = BASIC_PERMISSIONS + [
        # fs 2008-09-26:  Don't know why ticket admin gets these permissions again - he
        # should have these by the default trac policy. Probably this was because until
        # this revision we had own constants for ATTACHMENT_CREATE etc. so TICKET_ADMIN
        # did not get these.
        #        Action.ATTACHMENT_CREATE,
        #        Action.ATTACHMENT_VIEW,
        #        Action.TICKET_APPEND,

        # There is no TICKET_EDIT in trac (only more fine-grained permissions)
        # but we check just for TICKET_EDIT so TICKET_ADMIN must get this
        # permission, too
        Action.TICKET_DELETE,
        Action.CREATE_BUG,
        Action.CREATE_REQUIREMENT,
        Action.CREATE_STORY,
        Action.CREATE_TASK,
        Action.LINK_EDIT,
        ]
    CONTINGENT_ADMIN = Action.CONTINGENT_ADMIN
    CONTINGENT_ADMIN_ACTIONS = [Action.CONTINGENT_ADD_TIME]
    PRODUCT_OWNER = 'PRODUCT_OWNER'
    PRODUCT_OWNER_ACTIONS = BASIC_PERMISSIONS + [
        Action.BACKLOG_EDIT,
        Action.CREATE_REQUIREMENT,
        Action.CREATE_STORY,
        Action.SPRINT_EDIT,
        Action.MILESTONE_CREATE,
        Action.MILESTONE_MODIFY
    ]
    SCRUM_MASTER = 'SCRUM_MASTER'
    SCRUM_MASTER_ACTIONS = BASIC_PERMISSIONS + [
        Action.BACKLOG_EDIT,
        Action.CREATE_TASK,
        Action.CONFIRM_COMMITMENT,
        Action.CONTINGENT_ADD_TIME,
        Action.CONTINGENT_ADMIN,
        Action.REPORT_ADMIN,
        Action.SAVE_REMAINING_TIME,
        Action.SPRINT_EDIT,
        Action.TEAM_CAPACITY_EDIT,
        #        Action.LINK_EDIT,
    ]
    TEAM_MEMBER = 'TEAM_MEMBER'
    TEAM_MEMBER_ACTIONS = BASIC_PERMISSIONS + [
        Action.CONTINGENT_ADD_TIME,
        Action.CREATE_BUG,
        Action.CREATE_TASK,
        Action.BROWSER_VIEW,
        Action.LOG_VIEW,
        ]


class Status(object):
    """Class to encapsulate the status for a ticket life-cycle"""
    NEW = 'new'
    ACCEPTED = 'accepted'
    ASSIGNED = 'assigned'
    REOPENED = 'reopened'
    CLOSED = 'closed'
    RES_FIXED = 'fixed'
    RES_INVALID = 'invalid'
    RES_WONTFIX = 'wontfix'
    RES_DUPLICATE = 'duplicate'
    RES_WORKSFORME = 'worksforme'


class Realm(object):
    """
    Class to encapsulate all the defined Realms
    """
    BACKLOG = 'agilo-backlog'
    CONTINGENT = 'agilo-contingent'
    SPRINT = 'agilo-sprint'
    TICKET = 'ticket'


# List with ticket mandatory fields
MANDATORY_FIELDS = [
    Key.ID,
    Key.SUMMARY,
    Key.DESCRIPTION,
    Key.OWNER,
    Key.REPORTER,
    Key.TYPE,
    Key.STATUS,
    Key.RESOLUTION,

    # These are actually necessary for Trac 0.12
    Key.TIME_CREATED,
    Key.TIME_LAST_CHANGED
]

