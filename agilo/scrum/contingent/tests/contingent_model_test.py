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


from agilo.scrum.contingent import Contingent, ContingentModelManager
from agilo.test import AgiloTestCase


class TestContingent(AgiloTestCase):
    
    def setUp(self):
        self.super()
        self.team = self.teh.create_team(name='Team1')
        self.member1 = self.teh.create_member(name='Member 1', team=self.team)
        self.sprint = self.teh.create_sprint('Test Sprint', team=self.team)
        self.manager = ContingentModelManager(self.teh.get_env())
        self.contingent = self.manager.create(name='Bugfixing', amount=10, sprint=self.sprint)
    
    def test_can_add_time_to_contingent(self):
        self.contingent.add_time(5)
        self.assert_equals(5, self.contingent.actual)
    
    def test_can_remove_time_from_contingents(self):
        self.contingent.add_time(4)
        self.contingent.add_time(-1)
        self.assert_equals(3, self.contingent.actual)
    
    def test_can_not_reduce_used_time_below_zero(self):
        self.assert_raises(Contingent.UnderflowException, lambda: self.contingent.add_time(-1))
        self.assert_equals(0, self.contingent.actual)
    
    def test_adding_time_must_not_exceed_contingent_amount(self):
        self.contingent.add_time(5)
        e = self.assert_raises(Contingent.ExceededException, self.contingent.add_time, 6)
        self.assert_equals(1, e.amount)
    
    def test_can_create_contingent_with_percentage_of_capacity(self):
        contingent = self.manager.create(name='Support', percent=17, sprint=self.sprint)
        ten_percent_of_total_capacity = self.sprint.get_capacity_hours() * 0.17
        self.assert_not_equals(0, contingent.amount)
        self.assert_almost_equals(ten_percent_of_total_capacity, contingent.amount, places=2)


if __name__ == '__main__':
    from agilo.test.testfinder import run_unit_tests
    run_unit_tests(__file__)


