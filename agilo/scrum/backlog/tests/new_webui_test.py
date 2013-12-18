# -*- encoding: utf-8 -*-
#   Copyright 2008-2009 Agile42 GmbH, Berlin (Germany)
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
#       - Martin Häcker <martin.haecker__at__agile42.com>


from datetime import timedelta

from trac.perm import PermissionError

from agilo.api import ValueObject
from agilo.scrum.backlog.web_ui import NewBacklogView
from agilo.scrum.sprint import SessionScope
from agilo.test import AgiloTestCase, Usernames
from agilo.utils import Action, BacklogType
from agilo.utils.compat import json
from agilo.utils.days_time import date_to_datetime, today

# This should really create two teams and attach one to the sprint that this backlog is about
# then test that members of the one team can edit it and the other can't
# For now this works because the permissions model is quite poor and doesn't check that 
# a team member belongs to the team assigned a specific sprint

class NewWebUITest(AgiloTestCase):
    def setUp(self):
        self.super()
        self.view = NewBacklogView(self.env)
        self.teh.grant_permission(Usernames.team_member, Action.BACKLOG_VIEW)
    
    def req(self, username=Usernames.team_member, **kwargs):
        return self.teh.mock_request(username=username, args=kwargs)
    
    def request_backlog(self, a_backlog):
        returned_values = ValueObject(self.view.do_get(self.req(name=a_backlog.name, scope=a_backlog.scope)))
        returned_values.backlog_info = ValueObject(json.loads(returned_values.backlog_info))
        return returned_values
    
    def test_raises_permission_error_if_you_are_not_allowed_to_view_the_backlog(self):
        self.assert_raises(PermissionError, self.view.do_get, self.req(username='anonymous'))
    
    def test_can_return_backlog_info(self):
        sprint_start = date_to_datetime(today() - timedelta(days=4))
        sprint_end = sprint_start + timedelta(days=1)
        sprint = self.teh.create_sprint(name='fnord', start=sprint_start, end=sprint_end)
        backlog = self.teh.create_backlog(scope=sprint.name, b_type=BacklogType.SPRINT)
        info = self.request_backlog(backlog).backlog_info
        self.assert_not_none(info.content['configured_columns'])


class NewBacklogStoresScopeInSessionTest(AgiloTestCase):
    
    def setUp(self):
        self.super()
        self.view = NewBacklogView(self.env)
        self.teh.grant_permission(Usernames.anonymous, Action.BACKLOG_VIEW)
    
    def req(self, a_backlog):
        args = dict(name=a_backlog.name, scope=a_backlog.scope)
        return self.teh.mock_request(args=args)
    
    def test_module_stores_sprint_in_session(self):
        sprint = self.teh.create_sprint(name='fnord')
        backlog = self.teh.create_backlog(scope=sprint.name, b_type=BacklogType.SPRINT)
        req = self.req(backlog)
        
        self.assert_none(SessionScope(req).sprint_name())
        self.view.do_get(req)
        self.assert_equals(sprint.name, SessionScope(req).sprint_name())

