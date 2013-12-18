# -*- encoding: utf-8 -*-
#   Copyright 2008 Agile42 GmbH, Berlin (Germany)
#   Copyright 2007 Andrea Tomasini <andrea.tomasini_at_agile42.com>
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
#   
#   Author: 
#       - Andrea Tomasini <andrea.tomasini_at_agile42.com>
#       - Felix Schwarz <felix.schwarz__at__agile42.com>

from agilo.api.controller import ICommand
from agilo.scrum.contingent import ContingentController, ContingentModelManager
from agilo.test import AgiloTestCase


class TestContingent(AgiloTestCase):
    
    def setUp(self):
        self.super()
        self.team = self.teh.create_team(name='Team1')
        self.first_sprint = self.teh.create_sprint('Test Sprint', team=self.team)
        self.manager = ContingentModelManager(self.teh.get_env())
    
    def _add_time_to_contingent(self, contingent_name, sprint, nr_hours):
        self._clear_model_cache()
        cmd = ContingentController.AddTimeToContingentCommand(self.env, name=contingent_name, sprint=sprint.name, delta=str(nr_hours))
        return ContingentController(self.env).process_command(cmd)
    
    def _create_contingent(self, contingent_name, sprint, amount):
        self._clear_model_cache()
        cmd = ContingentController.AddContingentCommand(self.env, name=contingent_name, sprint=sprint.name, amount=str(amount))
        ContingentController(self.env).process_command(cmd)
        return self._get_contingent(contingent_name, sprint)
    
    def _clear_model_cache(self):
        ContingentModelManager(self.env).get_cache().invalidate()
    
    def _get_contingent(self, contingent_name, sprint):
        self._clear_model_cache()
        return ContingentController(self.env).get(name=contingent_name, sprint=sprint)
    
    def test_time_is_added_to_correct_contingent_even_if_two_contingents_with_the_same_name_exist(self):
        first_sprint = self.first_sprint
        second_sprint = self.teh.create_sprint('Second Sprint', team=self.team)
        self._create_contingent('Support', first_sprint, 10)
        self._create_contingent('Support', second_sprint, 5)
        
        self._add_time_to_contingent('Support', first_sprint, 4)
        # we need to load it from the db again...
        first_contingent = self._get_contingent('Support', first_sprint)
        second_contingent = self._get_contingent('Support', second_sprint)
        self.assert_equals(4, first_contingent.actual)
        self.assert_equals(0, second_contingent.actual)
    
    def _get_contingent_totals_for_sprint(self, sprint):
        cmd = ContingentController.GetSprintContingentTotalsCommand(self.env, sprint=sprint)
        return ContingentController(self.env).process_command(cmd)
    
    def test_contingent_model_manager_can_work_with_sprint_names(self):
        second_sprint = self.teh.create_sprint('Second Sprint', team=self.team)
        self.manager.create(name='Bugfixing', amount=4, sprint=self.first_sprint)
        self.manager.create(name='Support', amount=7, sprint=self.first_sprint)
        self.manager.create(name='Support', amount=20, sprint=second_sprint)
        self.manager.create(name='Bugfixing', amount=13, sprint=second_sprint)
        
        first_sprint_data = self._get_contingent_totals_for_sprint(self.first_sprint)
        self.assert_equals(4+7, first_sprint_data.amount)
        self.assert_equals(0, first_sprint_data.actual)
        
        second_sprint_data = self._get_contingent_totals_for_sprint(second_sprint)
        self.assert_equals(20+13, second_sprint_data.amount)
        self.assert_equals(0, second_sprint_data.actual)
    
    def test_can_get_contingents_with_command(self):
        self._create_contingent('fnord', self.first_sprint, 42)
        contingent = ContingentController(self.env).get(name='fnord', sprint=self.first_sprint)
        self.assert_equals('fnord', contingent.name)
        self.assert_equals(self.first_sprint.name, contingent.sprint.name)
        self.assert_equals(42, contingent.amount)
        self.assert_equals(0, contingent.actual)
    
    def test_cannot_create_two_contingents_with_same_name_in_a_sprint(self):
        self._create_contingent('Support', self.first_sprint, 10)
        self.assert_raises(ICommand.NotValidError, self._create_contingent, 'Support', self.first_sprint, 5)
    
    def test_raise_commanderror_if_new_total_is_negative(self):
        self._create_contingent('Support', self.first_sprint, 10)
        
        add_time = lambda: self._add_time_to_contingent('Support', self.first_sprint, -3)
        self.assertRaises(ICommand.CommandError, add_time)



if __name__ == '__main__':
    from agilo.test.testfinder import run_unit_tests
    run_unit_tests(__file__)

