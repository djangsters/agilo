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

from trac.web.api import RequestDone

from agilo.scrum.contingent import ContingentController, ContingentModelManager
from agilo.scrum.contingent.json_ui import ListContingentsJSONView
from agilo.test import AgiloTestCase
from agilo.utils import Action


class AddTimeToContingentWithJSONTest(AgiloTestCase):
    
    def setUp(self):
        self.super()
        self.req = self.teh.mock_request('foo')
        self.teh.grant_permission('foo', Action.CONTINGENT_ADD_TIME)
        self.teh.grant_permission('foo', Action.CONTINGENT_ADMIN)
        team = self.teh.create_team()
        self.sprint = self.teh.create_sprint('Contingent Sprint', team=team)
        self.support = 'Support'
    
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
    
    def _list_contingents(self, req, sprint_name=None):
        sprint_name = sprint_name or self.sprint.name
        data = dict(sprint=sprint_name)
        return ListContingentsJSONView(self.env).do_get(req, data)
    
    def test_handle_non_existent_sprint_gracefully(self):
        req = self.teh.mock_request('foo')
        self.assert_raises(RequestDone, self._list_contingents, req, 'doesnotexist')
    
    def test_can_list_contingents_for_a_sprint(self):
        self._create_contingent()
        contingent = dict(permissions=[Action.CONTINGENT_ADD_TIME],
                           content_type='contingent',
                           content=dict(name=self.support, sprint=self.sprint.name,
                                        amount=20, actual=0)
                          )
        expected = dict(permissions=[Action.CONTINGENT_ADMIN], content_type='contingent_list', 
                        content=[contingent])
        req = self.teh.mock_request('foo')
        self.assert_equals(expected, self._list_contingents(req, self.sprint))
    
    def test_contingent_list_includes_permissions(self):
        self._create_contingent()
        
        def permissions_for_first_contingent(req):
            contingent_json = self._list_contingents(req, self.sprint)['content']
            permissions = contingent_json[0]['permissions']
            return permissions
        
        req = self.teh.mock_request()
        self.assert_equals([], permissions_for_first_contingent(req))
        
        req = self.teh.mock_request('foo')
        self.assert_equals([Action.CONTINGENT_ADD_TIME], permissions_for_first_contingent(req))
    
    def test_contingent_list_includes_global_contingent_permission(self):
        self._create_contingent()
        contingent_json = self._list_contingents(self.req, self.sprint)
        permissions = contingent_json['permissions']
        self.assert_equals([Action.CONTINGENT_ADMIN], permissions)
    
    def test_contingent_list_only_includes_contingent_admin_permission_if_it_is_granted(self):
        self.teh.revoke_permission('foo', Action.CONTINGENT_ADMIN)
        self._create_contingent()
        contingent_json = self._list_contingents(self.req, self.sprint)
        permissions = contingent_json['permissions']
        self.assert_equals([], permissions)


if __name__ == '__main__':
    from agilo.test.testfinder import run_unit_tests
    run_unit_tests(__file__)

