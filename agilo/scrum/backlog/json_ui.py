# -*- coding: utf-8 -*-
#   Copyright 2007-2008 Agile42 GmbH - Andrea Tomasini
#   Copyright 2011 Agilo Software GmbH All rights reserved 
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
# 
# Authors:
#     - Andrea Tomasini <andrea.tomasini__at__agile42.com>
#     - Felix Schwarz <felix.schwarz__at__agile42.com>
#     - Martin Häcker <martin.haecker__at__agile42.com>

from trac.util.translation import _

from agilo.api import ICommand
from agilo.api.view import JSONView
from agilo.scrum.backlog.controller import BacklogController
from agilo.scrum.backlog.model import backlog_resource
from agilo.scrum.metrics.controller import MetricsController
from agilo.scrum.sprint import SprintController
from agilo.scrum.team.controller import TeamController
from agilo.ticket import AgiloTicketSystem, LinksConfiguration
from agilo.utils import Action, Key, Role
from agilo.utils.compat import exception_to_unicode
from agilo.utils.config import AgiloConfig, get_label
from agilo.utils.constants import BacklogType
from agilo.utils.web_ui import CoreTemplateProvider

__all__ = ['BacklogJSONView', 'BacklogMoveView', 'SprintListView',
           'ConfiguredChildTypesView', 'SprintBacklogJSONView', 'BacklogTicketPositionView',
           'ConfirmCommitmentJSONView', 'BacklogInfoJSONView',]


class BacklogAbstractJSONView(JSONView):
    """Abstract Backlog View to extend the normal JSONView with specific
    Backlog methods"""
    abstract = True
    
    def _get_backlog(self, name, scope):
        cmd_get = BacklogController.GetBacklogCommand(self.env, name=name, scope=scope)
        backlog = BacklogController(self.env).process_command(cmd_get)
        return backlog
    

class BacklogMoveView(JSONView):
    """Class that represent the view to move tickets in the backlog using JSON
    commands"""
    url = '/json/backlogs'
    url_regex = '/(?P<name>[^/]+)(/(?P<scope>[^/]+))?/?$'
    
    def do_post(self, req, data):
        name = req.args.get(Key.NAME)
        scope = req.args.get(Key.SCOPE)
        # These should be in the JSON posted data.
        ticket = int(data.get(Key.TICKET))
        to_pos = int(data.get(Key.TO_POS))
        cmd_move = BacklogController.MoveBacklogItemCommand(self.env,
                                                            name=name,
                                                            scope=scope,
                                                            ticket=ticket,
                                                            to_pos=to_pos)
        return BacklogController(self.env).process_command(cmd_move)
    

class ConfiguredChildTypesView(JSONView):
    url = '/json/config/ticket/link'
    url_regex = ''
    
    def user_may_create(self, req, child_type):
        creation_permission = CoreTemplateProvider(self.env).get_permission_name_to_create
        action = creation_permission(child_type)
        return req.perm.has_permission(action)
    
    def possible_child_types_with_attributes_to_copy(self, parent_type):
        possible_types_with_attributes = []
        for allowed_link in LinksConfiguration(self.env).get_alloweds(parent_type):
            child_type = allowed_link._dest_type
            options_to_copy = allowed_link.get_option('copy')
            possible_types_with_attributes.append((child_type, options_to_copy))
        return possible_types_with_attributes
    
    def link_tree(self, req=None):
        child_config = {}
        for parent_type in AgiloConfig(self.env).get_available_types(strict=True):
            child_config[parent_type] = {}
            for child_type, options_to_copy in self.possible_child_types_with_attributes_to_copy(parent_type):
                if req is not None and not self.user_may_create(req, child_type):
                    continue
                child_config[parent_type][child_type] = options_to_copy
        return child_config
    
    def do_get(self, req, data):
        return {'permitted_links_tree': self.link_tree(req),
                'configured_links_tree': self.link_tree(),}
    


# REFACT: Can we do it as separate Python object?
class BacklogInfoJSONView(BacklogAbstractJSONView):
    
    def backlog_info(self, req, scope, name):
        backlog = self._get_backlog(name, scope)
        return self.backlog_info_for_backlog(req, backlog)
    
    def backlog_info_for_backlog(self, req, backlog):
        return dict(content_type='backlog_info',
                    content=self._backlog_info_content(req, backlog),
                    permissions=self._backlog_permissions(req, backlog),)
    
    def _backlog_info_content(self, req, backlog):
        backlog_info = self._basic_info(backlog)
        backlog_info.update(self._access_control_info(req, backlog))
        backlog_info.update(self._type_and_column_configuration_info(req, backlog))
        backlog_info.update(self._filter_info())
        backlog_info.update(self._ticket_fields(backlog))
        backlog_info.update(self._type_aliases())
        return backlog_info
    
    def _basic_info(self, backlog):
        return dict(
            # type: 'global backlog', 'sprint backlog' 'milestone backlog' # actually part of the configuration
            type=BacklogType.LABELS[backlog.config.type], # REFACT: should be display_name_of_backlog
            # scope: name of a specific sprint or a release
            sprint_or_release=backlog.scope,
            # name: of the backlog (e.g. product backlog, sprint backlog, impediment backlog, bug backlog)
            name=backlog.name)
    
    def _access_control_info(self, req, backlog):
        username = req.authname
        is_read_only, reason = self._is_read_only_and_reason_from_backlog(req, backlog)
        return dict(access_control=dict(is_read_only=is_read_only, reason=reason),
                    username=username)
    
    def _is_read_only_and_reason_from_backlog(self, req, backlog):
        resource = backlog_resource(Key.SPRINT_BACKLOG)
        if backlog.is_sprint_backlog():
            if backlog.sprint().is_closed:
                return (True, _('Cannot modify sprints that have ended.'))
        # if sprint backlog: has ended or team member role required
            elif not (req.perm.has_permission(Action.BACKLOG_EDIT, resource)
                      or req.perm.has_permission(Role.TEAM_MEMBER)):
                return (True, _('Not enough permissions to modify this sprint.'))
        # must be a global backlog
        elif not (req.perm.has_permission(Action.BACKLOG_EDIT, resource)
                        or req.perm.has_permission(Role.PRODUCT_OWNER)):
            return (True, _('Not enough permissions to modify this backlog.'))
        
        return (False, '')
    
    def _type_and_column_configuration_info(self, req, backlog):
        return dict(configured_child_types=self._configured_child_types(req),
                    types_to_show=self._backlog_configuration(backlog),
                    configured_columns=self._configured_columns(backlog),
                    )
    
    def _configured_columns(self, backlog):
        return dict(columns=backlog.config.backlog_column_names(),
                    human_readable_names=backlog.config.backlog_human_readable_column_labels())
    
    def _backlog_configuration(self, backlog):
        return backlog.config.ticket_types
    
    def _configured_child_types(self, req):
        view = ConfiguredChildTypesView(self.env)
        return view.do_get(req, req.args)
    
    def _filter_info(self):
        config = AgiloConfig(self.env)
        if not config.backlog_filter_attribute:
            return dict()
        return dict(should_filter_by_attribute=config.backlog_filter_attribute,
                    should_reload_burndown_on_filter_change_when_filtering_by_component= \
                    config.should_reload_burndown_on_filter_change_when_filtering_by_component)
    
    def _backlog_permissions(self, req, backlog):
        permissions = []
        if backlog.is_sprint_backlog():
            sprint_resource = backlog.sprint().resource()
            if req.perm.has_permission(Action.CONFIRM_COMMITMENT, sprint_resource):
                permissions.append(Action.CONFIRM_COMMITMENT)
        
        return permissions

    def _calculated_fields(self):
        for calculated_property_name in LinksConfiguration(self.env).get_calculated():
            calculated_field = dict(is_calculated=True, type='text', label=get_label(calculated_property_name))
            yield calculated_property_name, calculated_field

    def _configured_fields(self):
        for field in AgiloTicketSystem(self.env).get_ticket_fields():
            field_name = field['name']
            del field['name']
            yield field_name, field

    def convert_owner_field_to_select_if_needed(self, field_dict, backlog):
        if not AgiloTicketSystem(self.env).restrict_owner:
            return

        owner_properties = field_dict.get(Key.OWNER)
        if owner_properties is None:
            return

        sprint_name = None
        if backlog.is_sprint_backlog():
            sprint_name = backlog.sprint().name

        AgiloTicketSystem(self.env).eventually_restrict_owner(owner_properties, sprint_name=sprint_name)


    def _ticket_fields(self, backlog):
        field_dict = {}
        for field_name, field_properties in self._calculated_fields():
            field_dict[field_name] = field_properties
        for field_name, field_properties in self._configured_fields():
            field_dict[field_name] = field_properties

        self.convert_owner_field_to_select_if_needed(field_dict, backlog)
        return dict(ticket_fields=field_dict)

    def _type_aliases(self):
        type_aliases = AgiloConfig(self.env).ALIASES
        return dict(type_aliases=type_aliases)


class BacklogJSONView(BacklogAbstractJSONView):
    
    url = '/json/backlogs'
    url_regex = '/(?P<backlog_name>[^/]+?)(?:/(?P<backlog_scope>[^/]+))?/?$'
    
    def backlog_as_json(self, req, name, scope):
        from agilo.ticket.web_ui import AgiloTicketModule
        ticket_module = AgiloTicketModule(self.env)
        json_data = []
        backlog =  self._get_backlog(name, scope)
        for backlog_item in backlog:
            ticket_dict = ticket_module.ticket_as_json(req, backlog_item.ticket)
            json_data.append(ticket_dict)
        return json_data
    
    def do_get(self, req, data):
        return self.backlog_as_json(req, data['backlog_name'], data['backlog_scope'])
    


class SprintBacklogJSONView(BacklogJSONView):
    
    url = '/json/sprints'
    url_regex = '/(?P<sprint>.+?)/backlog/?$'
    
    def do_get(self, req, data):
        return self.backlog_as_json(req, Key.SPRINT_BACKLOG, data.get(Key.SPRINT))
    

class BacklogTicketPositionView(BacklogAbstractJSONView):
    
    url = '/json/backlogs'
    url_regex = '/(?P<backlog_name>[^/]+?)(?:/(?P<backlog_scope>[^/]+))?/positions/?$'
    
    def do_get(self, req, data):
        return self._backlog_ticket_positions_as_json(data['backlog_name'], data['backlog_scope'])
    
    def _backlog_ticket_positions_as_json(self, name, scope):
        backlog = self._get_backlog(name, scope)
        if backlog:
            return [bi.ticket.id for bi in backlog]

    def do_post(self, req, data):
        name = data['backlog_name']
        scope = data['backlog_scope']
        positions = data.get('positions')
        self._set_ticket_positions(name, scope, positions)
        # TODO: if this fails we should inform the user and still include the old values...
        return self.do_get(req, data)
    
    def _set_ticket_positions(self, name, scope, positions):
        BacklogController.set_ticket_positions(self.env, name=name, scope=scope, positions=positions)
    

# REFACT: Is this used somewhere?
class SprintListView(JSONView):
    url = '/json/sprints'
    url_regex = '\/?$'
    
    def list_sprints(self, req):
        # imported here to break an import cycle
        from agilo.scrum.backlog.web_ui import BacklogModule
        return BacklogModule(self.env).running_to_start_closed_sprints(req)
    
    def do_get(self, req, data):
        return self.list_sprints(req)


class ConfirmCommitmentJSONView(BacklogAbstractJSONView):
    url = '/json/sprints'
    url_regex = '/(?P<sprint>.+?)/commit/?$'
    
    def _store_estimated_velocity(self, sprint):
        return TeamController.store_team_velocity(self.env, sprint, True)
    
    def _store_team_commitment(self, sprint):
        backlog = self._get_backlog(Key.SPRINT_BACKLOG, sprint.name)
        command = TeamController.\
            CalculateAndStoreTeamCommitmentCommand(self.env, sprint=sprint,
                                                   team=sprint.team,
                                                   tickets=backlog)
        return TeamController(self.env).process_command(command)
    
    def _store_team_capacity_if_necessary(self, sprint):
        capacity = self._get_team_capacity(sprint)
        command = MetricsController.StoreMetricsCommand(self.env, sprint=sprint, name=Key.CAPACITY, value=capacity)
        return MetricsController(self.env).process_command(command)
    
    def _get_team_capacity(self, sprint):
        command = TeamController.CalculateSummedCapacityCommand(self.env, sprint=sprint, team=sprint.team)
        return TeamController(self.env).process_command(command)
    
    def _sprint(self, req, sprint_name):
        try:
            get_sprint = SprintController.GetSprintCommand(self.env, sprint=sprint_name)
            get_sprint.native = True
            return SprintController(self.env).process_command(get_sprint)
        except ICommand.NotValidError, e:
            self.error_response(req, {}, [exception_to_unicode(e)])
    
    def do_post(self, req, data):
        sprint = self._sprint(req, data['sprint'])
        # REFACT: Actually we might want to check for SPRINT_VIEW even before
        # checking confirm commitment to prevent information disclosure
        req.perm.assert_permission(Action.CONFIRM_COMMITMENT, sprint.resource())
        # AgiloPolicy actually checks that the sprint has a team but we should
        # not rely on a specific policy to do necessary parameter validation
        if sprint.team is None:
            self.error_response(req, {}, [_('Cannot confirm sprint with no team assigned.')])
        
        self._store_estimated_velocity(sprint)
        self._store_team_commitment(sprint)
        self._store_team_capacity_if_necessary(sprint)


