# -*- encoding: utf-8 -*-
#   Copyright 2007-2009 Agile42 GmbH, Berlin (Germany)
#   Copyright 2011 Agilo Software GmbH All rights reserved
#
#   Licensed under the Apache License, Version 2.0 (the 'License');
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an 'AS IS' BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import agilo.utils.filterwarnings

from trac.perm import PermissionError
from trac.web.api import RequestDone

from agilo.api import ValueObject
from agilo.scrum.contingent import ContingentController, ContingentModelManager
from agilo.scrum.contingent.json_ui import AddTimeToContingentJSONView
from agilo.test import AgiloTestCase
from agilo.utils import Action

class AddTimeToContingentWithJSONTest(AgiloTestCase):
    
    def setUp(self):
        self.super()
        self.req = self.teh.mock_request('foo')
        self.teh.grant_permission('foo', Action.CONTINGENT_ADD_TIME)
        self.teh.grant_permission('foo', Action.BACKLOG_VIEW)
        team = self.teh.create_team()
        self.sprint = self.teh.create_sprint('Contingent Sprint', team=team)
        self.support = 'Support/Live-Bugs'
        self._create_contingent()
    
    def manager(self):
        return ContingentModelManager(self.env)
    
    def _create_contingent(self):
        self._clear_model_cache()
        cmd = ContingentController.AddContingentCommand(self.env, name=self.support, sprint=self.sprint.name, amount='20')
        ContingentController(self.env).process_command(cmd)
        return self._contingent()
    
    def _contingent(self):
        self._clear_model_cache()
        return self.manager().get(name=self.support, sprint=self.sprint)
    
    def _clear_model_cache(self):
        self.manager().get_cache().invalidate()
    
    def _add_time(self, req, contingent_name=None, sprint_name=None, delta=None):
        contingent_name = contingent_name or self.support
        sprint_name = sprint_name or self.sprint.name
        
        args = dict(sprint=sprint_name, contingent=contingent_name, delta=delta)
        response = ValueObject(AddTimeToContingentJSONView(self.env).do_post(req, args))
        
        self.assert_equals('contingent', response.content_type)
        contingent = response.content
        
        self.assert_equals(contingent_name, contingent['name'])
        self.assert_equals(sprint_name, contingent['sprint'])
        return response
    
    def _assert_add_time_fails(self, req, **parameters):
        error = self.assert_raises((RequestDone, PermissionError), self._add_time, req, **parameters)
        if isinstance(error, RequestDone):
            response = ValueObject(req.response.body_as_json())
            self.assert_equals(1, len(response.errors))
            current_data = ValueObject(response.current_data)
            if 'content_type' in current_data:
                self.assert_equals('contingent', current_data.content_type)
                contingent = ValueObject(current_data.content)
                self.assert_equals(0, contingent.actual)
        return error
    
    def test_can_add_time_to_contingents_via_json(self):
        self.assert_equals(0, self._contingent().actual)
        expected = dict(permissions=[Action.CONTINGENT_ADD_TIME],
                        content_type='contingent',
                        content=dict(name=self.support, sprint=self.sprint.name,
                                     amount=20, actual=12)
                       )
        actual = self._add_time(self.req, delta=12)
        self.assert_equals(expected, actual)
        self.assert_equals(12, self._contingent().actual)
        
        # set the same value again - should not change the value
        self.assert_equals(expected, self._add_time(self.req, delta=0))
        self.assert_equals(12, self._contingent().actual)
        
        expected['content']['actual'] = 13
        self.assert_equals(expected, self._add_time(self.req, delta=1))
        self.assert_equals(13, self._contingent().actual)
    
    def test_handle_nonexisting_contingents_gracefully(self):
        self._assert_add_time_fails(self.req, delta=12, contingent_name='doesnotexist')
        json = ValueObject(self.req.response.body_as_json())
        self.assert_equals(len(json.errors), 1)
        self.assert_true("No contingent" in json.errors[0])
        self.assert_equals(json.current_data, dict()) # no contingent, no data...
    
    def test_handle_nonexisting_sprints_gracefully(self):
        self._assert_add_time_fails(self.req, delta=12, sprint_name='doesnotexist')
        json = ValueObject(self.req.response.body_as_json())
        self.assert_equals(len(json.errors), 1)
        self.assert_true("No sprint with name" in json.errors[0])
        self.assert_equals(json.current_data, dict()) # no sprint, no contingent...
    
    def test_return_error_if_contingent_was_exceeded(self):
        self._assert_add_time_fails(self.req, delta=123)
        json = ValueObject(self.req.response.body_as_json())
        self.assert_true("CommandError: Amount for contingent" in json.errors[0])
    
    def test_adding_time_to_contingent_requires_permission(self):
        self.teh.revoke_permission('foo', Action.CONTINGENT_ADD_TIME)
        self._assert_add_time_fails(self.req, delta=12)
    
    def test_returns_empty_old_value_if_backlog_view_permission_is_missing(self):
        self.teh.revoke_permission('foo', Action.BACKLOG_VIEW)
        self._assert_add_time_fails(self.req, delta=12)
        # Exception will be converted to json response from the view itself
    
    def test_returns_old_contingent_if_no_permission_to_add(self):
        self.teh.revoke_permission('foo', Action.CONTINGENT_ADD_TIME)
        self._assert_add_time_fails(self.req, delta=12)
        json = ValueObject(self.req.response.body_as_json())
        self.assert_equals(len(json.errors), 1)
        self.assert_true("Not enough permissions" in json.errors[0])
        self.assert_equals(json.current_data['content_type'], 'contingent')
    
    def test_can_always_increase_contingent_by_zero_hours(self):
        self._add_time(self.req, delta=20) # first fill it up
        self._add_time(self.req, delta=0)  # then don't change it
    


if __name__ == '__main__':
    from agilo.test.testfinder import run_unit_tests
    run_unit_tests(__file__)

