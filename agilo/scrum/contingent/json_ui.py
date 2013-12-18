# -*- coding: utf-8 -*-
#   Copyright 2007-2009 agile42 GmbH
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

from trac.util.translation import _
from trac.perm import PermissionError

from agilo.api import ICommand
from agilo.api.view import JSONView
from agilo.scrum.contingent.controller import ContingentController
from agilo.utils import Action


__all__ = ['AddTimeToContingentJSONView', 'ListContingentsJSONView', ]


def contingent_to_json(req, contingent_data, contingent_view):
    contingent_data = contingent_view.dbobject_to_json(req, contingent_data, 'contingent', [Action.CONTINGENT_ADD_TIME])
    # fs/mh: Adding all the sprint data in the json dict is not that useful.
    # still the sprint name should be in the dict to be a bit more 
    # consistent for JS/Python model
    contingent_data.content.sprint = contingent_data.content.sprint['name']
    # The exists parameter is completely useless
    del contingent_data.content['exists']
    return contingent_data

class AbstractContingentJSONView(JSONView):

    abstract = True

    def _get_contingent(self, contingent_name, sprint_name):
        return ContingentController(self.env).get(name=contingent_name, sprint=sprint_name)
    
    def current_data(self, req, contingent_name, sprint_name):
        contingent = self._get_contingent(contingent_name, sprint_name)
        if contingent is None:
            error = _('No contingent "%s" for sprint "%s"') % (contingent_name, sprint_name)
            self.error_response(req, {}, [error])
        return contingent_to_json(req, contingent, self)
    


class AddTimeToContingentJSONView(AbstractContingentJSONView):
    
    url = '/json/sprints'
    url_regex = '/(?P<sprint>.+?)/contingents/(?P<contingent>.+?)/add_time/?$'
    
    def _current_contingent_or_error_response(self, req, contingent_name, sprint_name):
        try:
            return self.current_data(req, contingent_name, sprint_name)
        except ICommand.NotValidError:
            error = _('No sprint with name "%s"') % (sprint_name)
            self.error_response(req, {}, [error])
    
    def add_time_for_contingent(self, req, delta, contingent_name, sprint_name):
        old_contingent = self._current_contingent_or_error_response(req, contingent_name, sprint_name)
        parameters = dict(sprint=sprint_name, name=contingent_name, delta=delta)
        try:
            command = ContingentController.AddTimeToContingentCommand(self.env, **parameters)
            ContingentController(self.env).process_command(command)
        except (ICommand.CommandError), e:
            self.exception_response(req, old_contingent, e)
        except PermissionError, e:
            self.exception_response(req, old_contingent, e)
    
    def do_post(self, req, data):
        """@param: actual the new value of the contingents actual value (not the difference that was entered)"""
        # It should be Action.CONTINGENTS_VIEW - but we don't have that yet
        req.perm.assert_permission(Action.BACKLOG_VIEW)
        sprint_name = data['sprint']
        contingent_name = data['contingent']
        delta = data.get('delta', 0)
        if not req.perm.has_permission(Action.CONTINGENT_ADD_TIME):
            error = _("Not enough permissions to add time to contingent '%s' for sprint '%s") % (contingent_name, sprint_name)
            self.error_response(req, self.current_data(req, contingent_name, sprint_name), [error])
        self.add_time_for_contingent(req, delta, contingent_name, sprint_name)
        return self.current_data(req, contingent_name, sprint_name)


class AddContingentJSONView(AbstractContingentJSONView):
    
    url = '/json/sprints'
    url_regex = '/(?P<sprint>.+?)/contingents/?$'

    def do_put(self, req, data):
        req.perm.assert_permission(Action.BACKLOG_VIEW)
        req.perm.assert_permission(Action.CONTINGENT_ADMIN)
        
        sprint_name = data['sprint']
        contingent_name = data.get('name', None)
        amount = data.get('amount', None)

        params = dict(sprint=sprint_name, name=contingent_name, amount=amount)
        try:
            cmd = ContingentController.AddContingentCommand(self.env, **params)
        except ICommand.NotValidError, e:
            self.exception_response(req, {}, e)

        try:
            ContingentController(self.env).process_command(cmd)
        except ICommand.CommandError, e:
            self.exception_response(req, {}, e)
        return self.current_data(req, contingent_name, sprint_name)


class ListContingentsJSONView(AbstractContingentJSONView):
    
    url = '/json/sprints'
    url_regex = '/(?P<sprint>.+?)/contingents/?$'
    
    def _get_contingents(self, sprint_name):
        return ContingentController(self.env).list(sprint=sprint_name)
    
    def do_get(self, req, data):
        sprint_name = data['sprint']
        try:
            contingents = self._get_contingents(sprint_name)
        except ICommand.NotValidError:
            error = _('No sprint with name "%s"') % (sprint_name)
            self.error_response(req, {}, [error])
        permissions = []
        if req.perm.has_permission(Action.CONTINGENT_ADMIN):
            permissions.append(Action.CONTINGENT_ADMIN)
        return self.list_to_json(req, contingents, 'contingent_list', contingent_to_json, permissions=permissions)

