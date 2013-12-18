#   Copyright 2008 Agile42 GmbH, Berlin (Germany)
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
#        - Jonas von Poser <jonas.vonposer__at__agile42.com>
#        - Andrea Tomasini <andrea.tomasini__at__agile42.com>
#        - Felix Schwarz <felix.schwarz__at__agile42.com>

from datetime import timedelta

from trac.core import Component, implements
from trac.perm import IPermissionPolicy, IPermissionRequestor, DefaultPermissionPolicy

from agilo.utils import Action, Key, Type, Role, Realm
from agilo.utils.config import AgiloConfig, IAgiloConfigChangeListener
from agilo.utils.days_time import now
from agilo.utils.web_ui import CoreTemplateProvider
from agilo.scrum.sprint import SprintModelManager
from agilo.ticket.model import AgiloTicketModelManager
from agilo.ticket.links.model import LinksConfiguration


class AgiloPermissions(Component):

    implements(IPermissionRequestor, IAgiloConfigChangeListener)
    
    def __init__(self):
        # get all actions we have functions for
        self.static_actions = AgiloPolicy(self.env).action_map.keys()
        # get all actions defined in roles
        for key in dir(Role):
            if key.startswith('_') or key.endswith('_ACTIONS') or \
                    key == 'BASIC_PERMISSIONS':
                continue
            
            # first add the actions defined in this role
            for a in getattr(Role, key + '_ACTIONS', []):
                if a not in self.static_actions and a.startswith('AGILO_'):
                    # We only have to add the Agilo specific rights
                    # the others are added by trac itself
                    self.static_actions.append(a)
            
            # the add a tuple containing the role name
            # and the corresponding actions
            self.static_actions.append( (key, getattr(Role, key + '_ACTIONS', [])) )
        
        self.config_reloaded()
    
    def config_reloaded(self):
        # DefaultPermissionPolicy caches the permitted actions by user for
        # some seconds (not depending on the request). We need to reset this 
        # cache.
        DefaultPermissionPolicy(self.env).last_reap = 0
        self.actions = list(self.static_actions)
        self.get_actions_for_custom_types()
    
    def get_actions_for_custom_types(self):
        for typename in AgiloConfig(self.env).get_available_types():
            plain_name = str('CREATE_' + typename.upper())
            aliased_permission_name = getattr(Action, plain_name, plain_name)
            if aliased_permission_name not in self.actions:
                self.actions.append(aliased_permission_name)
                # Trac admin will get all these permissions implicitly so we
                # don't need to give him the permission explicitly.
                self._add_permission_for_role(Role.TICKET_ADMIN, aliased_permission_name)
    
    def _add_permission_for_role(self, role_name, permission_name):
        """Add the permission for role to self.actions. If there is already a
        list of actions for this role defined, the new permission will be added
        to this list."""
        for item in self.actions:
            if not isinstance(item, basestring):
                role, actions = item
                if role == role_name:
                    if permission_name not in actions:
                        actions.append(permission_name)
                    return
        self.actions.append(role_name, [permission_name])
    
    # IPermissionRequestor methods
    def get_permission_actions(self):
        return self.actions



# TODO fs: The LazyProxy seems overkill now, I'll remove it.
class LazyProxy(object):
    def __init__(self, a_getter):
        self._getter = a_getter
    
    def get_value(self):
        self.ensure_real_value_is_loaded()
        return self._real_value
    
    def ensure_real_value_is_loaded(self):
        if not hasattr(self, '_real_value'):
            self._real_value = self._getter()
    
    def __getitem__(self, name):
        return self.get_value()[name]
    
    def __getattr__(self, name):
        if name == '_real_value':
            raise AttributeError(name)
        return getattr(self.get_value(), name)


class AgiloPolicy(Component):
    """
    Check access to all Agilo resources against the corresponding roles.
    """
    
    implements(IPermissionPolicy)
    
    def __init__(self):
        self.action_map = {
            Action.ATTACHMENT_CREATE: self.check_attachment_create,
            Action.CONFIRM_COMMITMENT: self.confirm_commitment,
            Action.TICKET_EDIT: self.check_ticket_edit,
            # We need also to catch trac's Actions for modifying tickets 
            # - otherwise too many things will be allowed!
            Action.TICKET_CHANGE: self.check_ticket_edit,
            Action.TICKET_MODIFY: self.check_ticket_edit,
            Action.TICKET_EDIT_PAGE_ACCESS: self.check_ticket_edit_page_access,
            Action.TICKET_EDIT_DESCRIPTION: self.check_edit_description,
            
            # We don't have add a check for TICKET_APPEND because all three 
            # roles get the TICKET_APPEND permission via meta permissions. 
            # Therefore checking for team members is useless.
            # Action.TICKET_APPEND: self.check_ticket_append,
            Action.LINK_EDIT: self.check_link_edit,
            Action.SAVE_REMAINING_TIME: self.check_save_remaining_time,
            Action.BACKLOG_EDIT: self.check_backlog_edit,
        }
        self.tm = AgiloTicketModelManager(self.env)
    
    # --- permission checks ----------------------------------------------------
    
    # REFACT: Clean up the whole permission implementation. 
    # Currently it's confusing + inconsistent with CREATE_... and edit.
    def check_ticket_edit(self, username, resource, perm, t_type=None):
        """
        Check agilo ticket edit permissions, the schema should be as follows:
            Action.PRODUCT_OWNER: can edit Type.REQUIREMENT, Type.USER_STORY
            Action.SCRUM_MASTER: can link Type.USER_STORY, edit Type.TASK
            Action.TEAM_MEMBER: can link Type.USER_STORY, edit own Type.TASK
                                or unassigned Type.TASK, or Type.TASK where is
                                a Key.RESOURCE.
        The permission try to be as much loose as possible to allow 
        customization the idea is to extend Type.USER_STORY to any Type.TASK
        container.
        """
        # check if is admin cause we don't need to check anything else
        if Action.TRAC_ADMIN in perm or Action.TICKET_ADMIN in perm:
            return True
        
        if not resource and t_type is None:
            return None
        
        ticket, t_type = self._get_ticket_and_type(resource, t_type)
        if t_type is None:
            return None
        
        if t_type not in (Type.TASK, Type.USER_STORY, Type.REQUIREMENT, Type.BUG):
            # We don't make any assumptions about ticket types which are not 
            # part of the Agilo Core.
            return None
        if t_type == Type.BUG:
            return perm.has_permission(Action.CREATE_BUG, resource)
        
        # Task is our leaf, if we would consider task everything with Remaining Time
        # we may still encounter a type like Spike, with remaining time, but indeed
        # a potential task container.
        ticket_is_task = t_type == Type.TASK # We can't make it more loose
        is_team_member = Role.TEAM_MEMBER in perm
        is_scrum_master = Role.SCRUM_MASTER in perm
        is_ticket_owner = is_reporter = False
        if ticket.get_value() is not None:
            is_ticket_owner = (username == ticket[Key.OWNER]) or \
                (username in ticket.get_resource_list())
            is_reporter = (username == ticket[Key.REPORTER])
        ticket_has_no_owner = (ticket.get_value() is None or not ticket[Key.OWNER])
        is_product_owner = (Role.PRODUCT_OWNER in perm)
        
        if is_ticket_owner or \
            (ticket_is_task and (is_team_member or is_reporter) and ticket_has_no_owner) or \
            (is_product_owner and not ticket_is_task) or \
            (ticket_is_task and is_scrum_master):
            return True
        # We must stop the default policy which does not know anything about
        # types and does not check owners. Therefore anyone with TICKET_EDIT
        # permission could edit tickets if we don't deny here!
        return False
    
    def check_ticket_edit_page_access(self, username, resource, perm):
        def can_create_at_least_one_referenced_type(ticket_type):
            for allowed_type in LinksConfiguration(self.env).get_allowed_destination_types(ticket_type):
                permission_name = CoreTemplateProvider(self.env).get_permission_name_to_create(allowed_type)
                if permission_name in perm:
                    return True
            return False
        
        ticket_type = self._get_ticket_type(resource)
        if ticket_type is None:
            return True
        if can_create_at_least_one_referenced_type(ticket_type):
            return True
        return perm.has_permission(Action.TICKET_MODIFY, resource)
    
    def check_edit_description(self, username, resource, perm):
        # For now we just ignore trac's TICKET_EDIT_DESCRIPTION privileges
        return self.check_ticket_edit(username, resource, perm)
    
    def check_attachment_create(self, username, resource, perm):
        # The idea is that any user with ATTACHMENT_CREATE can create 
        # attachments *if* she is allowed to edit the ticket. This check 
        # places additional constraints on ATTACHMENT_CREATE: It denies access 
        # for users who may not edit the ticket but leaves the final decision
        # to other trac policies.
        ticket = self._get_agilo_ticket(resource)
        if not ticket:
            return
        may_edit_ticket = self.check_ticket_edit(username, resource, perm)
        if may_edit_ticket == False:
            return False
        return None
    
    def check_link_edit(self, username, resource, perm):
        """
        Checks it the current user can edit links on the given resource.
        The rules are:
            - Product Owner can link every ticket which is not a task, this 
            means that the Product Owner will not be allowed to create tasks
            - Team Member and Scrum Master, can create link only to task, this
            means they can edit link on task containers
        This all works fine because the links can only be created from container
        to destination, therefore there is no problem with the direction.
        """
        is_product_owner = Role.PRODUCT_OWNER in perm
        is_tm_or_sm = Role.SCRUM_MASTER in perm or Role.TEAM_MEMBER in perm
        ticket = self._get_agilo_ticket(resource)
        is_task_container = False
        if ticket is not None:
            is_task_container = Type.TASK in [al.get_dest_type() for al in ticket.get_alloweds()]
        return (is_product_owner and not is_task_container) or \
               (is_tm_or_sm and is_task_container) or \
               None
    
    def check_backlog_edit(self, username, resource, perm):
        """
        Checks if the current user can edit the given Backlog Resource.
        The rules are:
            - Product Backlog: only Product Owner can edit
            - Sprint Backlog: only Scrum Master can fully edit, team 
            member will have rights on individual tickets (see ticket_edit)
            - Other Backlog: every authenticated user, as we can't make any
            other assumption.
        """
        name = self._get_backlog_name(resource)
        
        is_product_owner = Role.PRODUCT_OWNER in perm
        if is_product_owner and (name in (None, Key.PRODUCT_BACKLOG)):
            return True
        
        is_scrum_master = Role.SCRUM_MASTER in perm
        if is_scrum_master and (name in (None, Key.SPRINT_BACKLOG)):
            return True
        
        if name is None:
            return None
        
        is_custom_backlog = name not in (Key.PRODUCT_BACKLOG, Key.SPRINT_BACKLOG)
        is_authenticated_user = username is not None and username != 'anonymous'
        if is_custom_backlog and is_authenticated_user:
            return True
        return None
    
    def check_save_remaining_time(self, username, resource, perm):
        """
        Checks if the current user can change the remaining time
        on the given ticket resource. The rules are:
            - Scrum Master: can always change the remaining time
            - Team Member: can change remaining time only if owner or resource
            of the given task, or the task has not yet been assigned, in which
            case the current user will become also owner.
        """
        is_scrum_master = Role.SCRUM_MASTER in perm
        if not is_scrum_master:
            return self.check_ticket_edit(username, resource, perm)
        return True
    
    def sprint(self, sprint_name):
        return SprintModelManager(self.env).get(name=sprint_name)
    
    def _has_sprint_started_more_than_one_day_ago(self, sprint):
        return now() - sprint.start > timedelta(days=1)
    
    def confirm_commitment(self, username, resource, perm):
        if (resource is None) or resource.realm != Realm.SPRINT:
            return None
        sprint = self.sprint(resource.id)
        if sprint is None:
            return None
        
        if sprint.team is None:
            # Actually this check is not really a policy decision (but technical
            # necessity) - however it makes some other code simpler
            return False
        if self._has_sprint_started_more_than_one_day_ago(sprint):
            # TODO: Maybe TRAC_ADMIN should be able to do it anyway?
            return False
        return None
    
    # IPermissionPolicy methods
    def check_permission(self, action, username, resource, perm):
        """
        Check that the action can be performed by username on the resource
        
        :param action: the name of the permission
        :param username: the username string or 'anonymous' if there's no
                         authenticated user
        :param resource: the resource on which the check applies.
                         Will be `None`, if the check is a global one and
                         not made on a resource in particular
        :param perm: the permission cache for that username and resource,
                     which can be used for doing secondary checks on other
                     permissions. Care must be taken to avoid recursion.
        
        :return: `True` if action is allowed, `False` if action is denied,
                 or `None` if indifferent. If `None` is returned, the next
                 policy in the chain will be used, and so on.
        """
        # run the function associated with this action
        if action in self.action_map:
            return self.action_map[action](username, resource, perm)
        # Return None because we don't care about this action so other 
        # PermissionPolicies can vote on this request.
        return None
    
    # --- helpers -------------------------------------------------------------.
    
    def _get_resource_id_with_realm(self, resource, realm):
        while resource:
            if resource.realm == realm:
                break
            resource = resource.parent
        if not resource or (resource.realm != realm) or (resource.id is None):
            return None
        return resource.id
    
    def _get_agilo_ticket(self, resource):
        resource_id = self._get_resource_id_with_realm(resource, Realm.TICKET)
        return self.tm.get(tkt_id=resource_id)
    
    def _get_backlog_name(self, resource):
        return self._get_resource_id_with_realm(resource, Realm.BACKLOG)
    
    def _get_ticket_and_type(self, resource=None, ticket_type=None):
        ticket = LazyProxy(lambda: self._get_agilo_ticket(resource))
        if ticket_type is None:
            if ticket.get_value() is None:
                return None, None
            ticket_type = ticket.get_type()
        if ticket_type is not None:
            return ticket, ticket_type
        return None, None
    
    def _get_ticket_type(self, resource):
        ticket = self._get_agilo_ticket(resource)
        if ticket is not None:
            return ticket.get_type()
        return None

