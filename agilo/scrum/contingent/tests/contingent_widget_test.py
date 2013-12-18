# -*- encoding: utf-8 -*-
#   Copyright 2008 Agile42 GmbH, Berlin (Germany)
#   Copyright 2011 Agilo Software GmbH All rights reserved
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
#       - Felix Schwarz <felix.schwarz__at__agile42.com>

import agilo.utils.filterwarnings

from agilo.scrum.contingent import ContingentWidget, ContingentModelManager
from agilo.test import AgiloTestCase
from agilo.utils import Action


class ContingentWidgetTestCase(AgiloTestCase):
    
    def setUp(self):
        self.super()
        self.sprint = self.teh.create_sprint('FooSprint')
    
    def get_widget(self):
        widget = ContingentWidget(self.env, self.sprint)
        widget.prepare_rendering(self.teh.mock_request(username='foo'))
        return widget
    
    def test_smoke(self):
        widget = self.get_widget()
        html = self.render(widget)
        self.assert_equals(0, len(widget.data['contingents_with_stats']))
        self.assert_equals('', html)
    
    def create_contingent(self, name, amount=20, actual=0):
        model_manager = ContingentModelManager(self.env)
        return model_manager.create(name=name, sprint=self.sprint, amount=amount, 
                                    actual=actual)
    
    def render(self, widget):
        widget.prepare_rendering(self.teh.mock_request(username='foo'))
        html = str(widget.display())
        return html
    
    def test_can_also_use_only_sprint_name_for_widget(self):
        self.create_contingent('Lookahead')
        self.sprint = 'FooSprint'
        widget = self.get_widget()
        self.assert_equals('FooSprint', widget.data['sprint'])
        html = self.render(widget)
        self.assert_true('FooSprint' in html)
    
    def test_can_display_all_configured_contingents(self):
        self.create_contingent('bug fixing', amount=10)
        self.create_contingent('user support', amount=25)
        
        widget = self.get_widget()
        html = self.render(widget)
        self.assert_true('FooSprint' in html)
        self.assert_equals(self.sprint.name, widget.data['sprint'])
        self.assert_equals(2, len(widget.data['contingents_with_stats']))
        self.assert_equals({'amount': 10+25, 'actual': 0}, 
                         widget.data['contingent_totals'])
    
    def grant_permission(self, action):
        self.teh.grant_permission('foo', action)
    
    def test_only_users_with_appropriate_permission_can_modify_contingents(self):
        widget = self.get_widget()
        self.assert_false(widget.data['may_modify_contingents'])
        
        self.grant_permission(Action.CONTINGENT_ADMIN)
        widget = self.get_widget()
        self.assert_true(widget.data['may_modify_contingents'])
    
    def test_only_users_with_permission_can_add_time_to_contingent(self):
        widget = self.get_widget()
        self.assert_false(widget.data['may_add_actual_time'])
        
        self.grant_permission(Action.CONTINGENT_ADD_TIME)
        widget = self.get_widget()
        self.assert_true(widget.data['may_add_actual_time'])


if __name__ == '__main__':
    from agilo.test.testfinder import run_unit_tests
    run_unit_tests(__file__)

