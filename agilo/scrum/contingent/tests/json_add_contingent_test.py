# -*- encoding: utf-8 -*-
#   Copyright 2007-2010 Agile42 GmbH, Berlin (Germany)
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

from agilo.api import ValueObject
from agilo.scrum.contingent import ContingentModelManager
from agilo.scrum.contingent.json_ui import AddContingentJSONView
from agilo.test import JSONAgiloTestCase
from agilo.utils import Action
from agilo.utils.compat import json

class AddContingentWithJSONTest(JSONAgiloTestCase):
    
    def setUp(self):
        self.super()
        self.req = self.teh.mock_request('foo')
        self.teh.grant_permission('foo', Action.CONTINGENT_ADMIN)
        self.teh.grant_permission('foo', Action.BACKLOG_VIEW)
        self.team = self.teh.create_team()
        self.sprint = self.teh.create_sprint('Contingent Sprint', team=self.team)
        self.parameters = {'amount': '20.0', 'sprint' : self.sprint.name, 'name' : 'Support/Live-Bugs'}
        self._clear_model_cache()
    
    def manager(self):
        return ContingentModelManager(self.env)
    
    def _contingent(self, name, sprint):
        self._clear_model_cache()
        return self.manager().get(name=name, sprint=sprint)
    
    def _clear_model_cache(self):
        self.manager().get_cache().invalidate()
    
    def _add_contingent(self, req, expected_amount=None, **client_json):
        response = ValueObject(AddContingentJSONView(self.env).do_put(req, client_json))
        
        self.assert_equals('contingent', response.content_type)
        server_json = response.content
        # we pass the client_json as a string because % values are allowed
        server_json.amount = str(server_json.amount)
        client_json['actual'] = client_json.has_key('actual') and client_json.actual or 0
        if expected_amount is not None:
            client_json['amount'] = expected_amount
        
        self.assert_equals(client_json, server_json)
    
    def _assert_add_contingent_returns_error(self):
        self.assert_method_returns_error_with_empty_data(self._add_contingent, self.req, **self.parameters)
    
    def test_can_add_contingent_via_json(self):
        self.assert_equals(None, self._contingent(self.parameters['name'], self.sprint))
        self._add_contingent(self.req, **self.parameters)
    
    def test_can_add_contingent_with_percent_value(self):
        self.teh.create_member('John Doe', self.team)
        self.parameters['amount'] = '29%'
        expected_amount = "%.1f" % (0.29 * self.sprint.get_capacity_hours())
        self._add_contingent(self.req, expected_amount, **self.parameters)
    
    def test_can_add_contingent_with_percent_value_but_no_capacity(self):
        expected_amount = "0.0"
        self.parameters['amount'] = '29%'
        self._add_contingent(self.req, expected_amount, **self.parameters)
    
    def test_adding_contingent_requires_modify_permission(self):
        self.teh.revoke_permission('foo', Action.CONTINGENT_ADMIN)
        self.assert_raises(PermissionError, self._add_contingent, self.req, **self.parameters)
    
    def test_adding_contingent_requires_view_permission(self):
        self.teh.revoke_permission('foo', Action.BACKLOG_VIEW)
        self.assert_raises(PermissionError, self._add_contingent, self.req, **self.parameters)
    
    def test_adding_contingent_without_name_returns_error(self):
        self.parameters['name'] = None
        self._assert_add_contingent_returns_error()
    
    def test_adding_contingent_with_unknown_sprint_returns_error(self):
        self.parameters['sprint'] = 'some_other'
        self._assert_add_contingent_returns_error()
    
    def test_adding_duplicate_contingent_returns_error(self):
        self._add_contingent(self.req, **self.parameters)
        self._assert_add_contingent_returns_error()
    
    def test_sending_bad_percent_values_returns_error(self):
        self.parameters['amount'] = '__%'
        path_info = '/json/sprint/%s/contingents/' % (self.sprint.name)
        request_body = json.dumps(self.parameters)
        
        req = self.teh.mock_request(path_info=path_info, request_body=request_body, method='PUT')
        self.assert_method_returns_error_with_empty_data(AddContingentJSONView(self.env).process_request, req)


if __name__ == '__main__':
    from agilo.test.testfinder import run_unit_tests
    run_unit_tests(__file__)

