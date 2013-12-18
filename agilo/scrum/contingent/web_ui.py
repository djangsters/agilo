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
#     - Felix Schwarz <felix.schwarz__at__agile42.com>
#     - Andrea Tomasini <andrea.tomasini__at__agile42.com>

from pkg_resources import resource_filename
from trac.core import TracError
from trac.util.translation import _

from agilo.api import view
#from agilo.scrum import BACKLOG_URL
from agilo.scrum.contingent import ContingentController
from agilo.scrum.contingent.controller import CONTINGENTS_URL
from agilo.scrum.contingent.widget import ContingentWidget
from agilo.utils import Action, Key
from agilo.utils.compat import exception_to_unicode

__all__ = ['AddTimeToContingentView', 'AddContingentView', 'DeleteContingentView']

# Compatibility with Old Backlog
BACKLOG_URL = '/oldbacklog'


class AbstractContingentView(view.HTTPView):
    
    abstract = True
    
    controller_class = ContingentController
    url = CONTINGENTS_URL
    
    def match_request(self, req):
        return super(AbstractContingentView, self).match_request(req) and self.get_handler(req)
    
    def get_redirect_url(self, req, sprint):
        backlog_url = req.href(BACKLOG_URL, Key.SPRINT_BACKLOG, bscope=sprint.name)
        if 'backlog' in req.args:
            url = backlog_url
        elif sprint.team:
            url = req.href.team(sprint.team.name, sprint.name)
        else:
            url = req.environ.get('HTTP_REFERER', backlog_url)
        return url
    
    def _get_sprint(self, req):
        from agilo.scrum import SprintController
        cmd = SprintController.GetSprintCommand(self.env, sprint=req.args['sprint'])
        sprint = SprintController(self.env).process_command(cmd)
        return sprint


class AddTimeToContingentView(AbstractContingentView):
    
    def match_request(self, req):
        if super(AddTimeToContingentView, self).match_request(req):
            return ('add_time' in req.args)
    
    def _extract_added_times(self, req):
        added_times = dict()
        prefix = 'col_add_time_'
        for key in req.args:
            if key.startswith(prefix) and req.args[key].strip() != '':
                name = key[len(prefix):]
                try:
                    additional_time = float(req.args[key])
                except ValueError:
                    raise TracError(_('Invalid number for additional time: %s') % repr(req.args[key]))
                added_times[name] = additional_time
        return added_times
    
    def do_post(self, req):
        req.perm.assert_permission(Action.CONTINGENT_ADD_TIME)
        sprint = self._get_sprint(req)
        
        added_times = self._extract_added_times(req)
        cc = ContingentController(self.env)
        for name, amount in added_times.items():
            cmd = ContingentController.AddTimeToContingentCommand(self.env, sprint=sprint.name, name=name, delta=amount)
            cc.process_command(cmd)
        req.redirect(self.get_redirect_url(req, sprint))
    
    def prepare_data(self, req, req_data):
        data = super(AddTimeToContingentView, self).prepare_data(req, req_data)
        
        sprint = self._get_sprint(req)
        widget = ContingentWidget(self.env, sprint=sprint.name, backlog=True)
        widget.prepare_rendering(req)
        
        data['redirect_url'] = self.get_redirect_url(req, sprint)
        data['contingent_widget'] = widget
        
        return data


class AddContingentView(AbstractContingentView):
    
    def match_request(self, req):
        if super(AddContingentView, self).match_request(req):
            add_button_pressed = req.args.get('cont_add') not in (None, '')
            return add_button_pressed
    
    def do_post(self, req):
        req.perm.assert_permission(Action.CONTINGENT_ADMIN)
        
        name = req.args.get('cont_name')
        amount = req.args.get('cont_amount')
        sprint = self._get_sprint(req)
        params = dict(sprint=sprint.name, name=name, amount=amount)
        try:
            cmd = ContingentController.AddContingentCommand(self.env, **params)
            ContingentController(self.env).process_command(cmd)
        except Exception, e:
            raise TracError(exception_to_unicode(e))
        req.redirect(self.get_redirect_url(req, sprint))


class DeleteContingentView(AbstractContingentView):
    
    def match_request(self, req):
        if super(DeleteContingentView, self).match_request(req):
            return ('remove' in req.args)
    
    def do_post(self, req):
        req.perm.assert_permission(Action.CONTINGENT_ADMIN)
        
        contingents_to_remove = req.args.getlist('sel')
        sprint = self._get_sprint(req)
        
        cc = ContingentController(self.env)
        for name in contingents_to_remove:
            cmd = ContingentController.DeleteContingentCommand(self.env, sprint=sprint.name, name=name)
            cc.process_command(cmd)
        req.redirect(self.get_redirect_url(req, sprint))

