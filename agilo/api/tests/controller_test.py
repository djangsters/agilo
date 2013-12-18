# -*- encoding: utf-8 -*-
#   Copyright 2010 Agile42 GmbH, Berlin (Germany)
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

from agilo.test import AgiloTestCase
from agilo.api.controller import ValuePerTime


class ValuePerTimeTest(AgiloTestCase):
    class FnordPerTime(ValuePerTime):
        fnord = property(ValuePerTime._value, ValuePerTime._set_value)
    
    def test_can_get_values(self):
        value = ValuePerTime('foo', 'bar')
        self.assert_equals('foo', value.value)
        self.assert_equals('bar', value.when)
    
    def test_can_set_values(self):
        value = ValuePerTime(None, None)
        value.value = 'foo'
        value.when = 'bar'
        self.assert_equals('foo', value.value)
        self.assert_equals('bar', value.when)
    
    def test_can_get_and_set_values_in_subclass(self):
        value = ValuePerTimeTest.FnordPerTime('foo', 'bar')
        self.assert_equals('foo', value.fnord)
        value.fnord = 'bar'
        self.assert_equals('bar', value.fnord)
        self.assert_equals('bar', value.value)
    
    def test_can_compare_two_equal_values(self):
        first_value = ValuePerTimeTest.FnordPerTime('foo', 'bar')
        second_value = ValuePerTimeTest.FnordPerTime('foo', 'bar')
        self.assert_equals(first_value, second_value)
    
    def test_can_compare_two_different_values(self):
        first_value = ValuePerTimeTest.FnordPerTime('foo', 'bar')
        second_value = ValuePerTimeTest.FnordPerTime('foo', 'fnord')
        self.assert_not_equals(first_value, second_value)
    
    def test_can_compare_with_none(self):
        first_value = ValuePerTimeTest.FnordPerTime('foo', 'bar')
        self.assert_not_equals(first_value, None)
    
