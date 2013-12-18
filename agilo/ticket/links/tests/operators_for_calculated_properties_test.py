#!/usr/bin/env python
# -*- coding: utf-8 -*-
#   Copyright 2008 Agile42 GmbH - Andrea Tomasini
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
# Authors:
#     - Felix Schwarz

from agilo.test import AgiloTestCase
from agilo.ticket.links.configuration_parser import parse_calculated_field, \
    parse_calculated_fields_definition


class FakeTicket(object):
    def __init__(self, **kwargs):
        self.data = dict(foo=21, bar=42, baz=[], quux=5, quuux=None, 
                         type='lime', priority='low')
        for key in kwargs:
            self.data[key] = kwargs[key]
    
    def __getattr__(self, name):
        if name.startswith('get_'):
            return self[name[4:]]
        raise AttributeError(name)
    
    def __getitem__(self, attr):
        return self.data.get(attr, None)
    
    def __setitem__(self, attr, value):
        self.data[attr] = value
    
    def get_baz(self):
        return self.data['baz']
    
    def is_readable_field(self, field_name):
        return field_name in ['foo', 'bar', 'baz', 'quux', 'quuux', 'type', 'priority']


class TestConfigParsingOfCalculatedProperties(AgiloTestCase):
    
    def setUp(self):
        self.super()
        self.parse = parse_calculated_field
        self.ticket = FakeTicket()
    
    def test_empty_option_string(self):
        self.assert_none(self.parse(None))
        self.assert_none(self.parse(''))
        self.assert_none(self.parse('  '))
    
    def test_sum_with_only_one_value(self):
        operator_def = dict([self.parse('value=sum:foo')])
        operator = operator_def['value']
        self.assert_equals(21, operator(self.ticket))
    
    def test_sum_with_two_fields(self):
        operator_def = self.parse('value=sum:foo;bar')
        self.assert_not_none(operator_def)
        self.assert_equals(2, len(operator_def))
        name, operator = operator_def
        self.assert_equals('value', name)
        self.assert_equals(63, operator(self.ticket))
    
    def test_sum_with_two_fields_ignore_invalid_separator(self):
        operator_def = self.parse('value=sum:;foo;bar')
        self.assert_not_none(operator_def)
        operator = operator_def[1]
        self.assert_equals(63, operator(self.ticket))
    
    def test_sum_with_three_fields(self):
        operator_def = self.parse('value=sum:foo;bar;quux')
        self.assert_not_none(operator_def)
        operator = operator_def[1]
        self.assert_equals(68, operator(self.ticket))
    
    def test_sum_without_any_values(self):
        operator_def = self.parse('value=sum:')
        self.assert_none(operator_def)
    
    def test_sum_without_values_only_separator(self):
        operator_def = self.parse('value=sum:;')
        self.assert_none(operator_def)
    
    def test_sum_with_list_value(self):
        self.ticket['baz'] = [1, 2]
        operator_def = self.parse('value=sum:baz')
        self.assert_not_none(operator_def)
        operator = operator_def[1]
        self.assert_equals(3, operator(self.ticket))
    
    def test_sum_with_callable(self):
        operator_def = self.parse('value=sum:get_foo;bar')
        self.assert_not_none(operator_def)
        operator = operator_def[1]
        self.assert_equals(63, operator(self.ticket))
    
    def test_sum_with_callable_that_returns_list(self):
        self.ticket['baz'] = [45, 54]
        operator_def = self.parse('value=sum:get_baz')
        self.assert_not_none(operator_def)
        operator = operator_def[1]
        self.assert_equals(99, operator(self.ticket))
    
    def test_sum_with_namespace(self):
        self.ticket['quuux'] = FakeTicket()
        self.ticket['quuux']['foo'] = 22
        operator_def = self.parse('value=sum:quuux.foo;foo')
        self.assert_not_none(operator_def)
        operator = operator_def[1]
        self.assert_equals(43, operator(self.ticket))
    
    def test_sum_with_namespace_but_no_attribute_name(self):
        operator_def = self.parse('value=sum:quuux.;')
        self.assert_none(operator_def)
    
    def test_sum_with_missing_namespace(self):
        operator_def = self.parse('value=sum:.foo;')
        self.assert_none(operator_def)
    
    def test_namespaced_sum_with_double_dot(self):
        operator_def = self.parse('value=sum:quuux..foo;')
        self.assert_none(operator_def)
    
    def test_sum_with_multiple_namespaces(self):
        self.ticket['quuux'] = FakeTicket()
        self.ticket['quuux']['foo'] = 22
        self.ticket['quuux']['quuux'] = FakeTicket()
        operator_def = self.parse('value=sum:quuux.get_quuux.foo')
        self.assert_not_none(operator_def)
        operator = operator_def[1]
        self.assert_equals(21, operator(self.ticket))
    
    def test_sum_with_multiple_namespaces_and_callable(self):
        self.ticket['quuux'] = FakeTicket()
        self.ticket['quuux']['quuux'] = FakeTicket()
        self.ticket['quuux']['quuux']['quuux'] = FakeTicket()
        self.ticket['quuux']['quuux']['quuux']['bar'] = 4711
        operator_def = self.parse('value=sum:quuux.get_quuux.get_quuux.bar')
        self.assert_not_none(operator_def)
        operator = operator_def[1]
        self.assert_equals(4711, operator(self.ticket))
    
    def test_sum_with_namespaced_list(self):
        self.ticket['baz'] = [FakeTicket(), FakeTicket()]
        operator_def = self.parse('value=sum:baz.foo')
        self.assert_not_none(operator_def)
        operator = operator_def[1]
        self.assert_equals(42, operator(self.ticket))
    
    def test_sum_with_namespaced_callable_that_returns_list(self):
        self.ticket['quuux'] = FakeTicket()
        self.ticket['quuux']['baz'] = [3, 4]
        operator_def = self.parse('value=sum:quuux.get_baz')
        self.assert_not_none(operator_def)
        operator = operator_def[1]
        self.assert_equals(7, operator(self.ticket))
    
    def test_sum_with_list_value_and_condition(self):
        self.ticket['baz'] = [FakeTicket(), FakeTicket()]
        self.ticket['baz'][0]['type'] = 'lemon'
        self.ticket['baz'][1]['foo'] = 46
        
        operator_def = self.parse('value=sum:baz.foo|type=lime')
        self.assert_not_none(operator_def)
        operator = operator_def[1]
        self.assert_equals(46, operator(self.ticket))
    
    def test__sum_with_with_multiple_conditions(self):
        self.ticket['baz'] = [FakeTicket(), FakeTicket(), FakeTicket()]
        self.ticket['baz'][0]['type'] = 'lemon'
        self.ticket['baz'][2]['foo'] = 46
        self.ticket['baz'][2]['priority'] = 'high'
        
        operator_def = self.parse('value=sum:baz.foo|type=lime|priority=high')
        self.assert_not_none(operator_def)
        operator = operator_def[1]
        self.assert_equals(46, operator(self.ticket))
    
    def test_sum_with_float_values(self):
        self.ticket['foo'] = '21.5'
        self.ticket['bar'] = '12.4'
        operator_def = self.parse('value=sum:foo;bar')
        self.assert_not_none(operator_def)
        operator = operator_def[1]
        self.assert_equals(float('33.9'), operator(self.ticket))
    
    def test_sum_should_ignore_invalid_values(self):
        self.ticket['foo'] = '21.5'
        self.ticket['bar'] = None
        operator_def = self.parse('value=sum:foo;bar')
        self.assert_not_none(operator_def)
        operator = operator_def[1]
        self.assert_none(operator(self.ticket))
    
    
    def test_sum_with_nonexistent_properties(self):
        self.assert_false(hasattr(self.ticket, 'foobarquux'))
        operator_def = self.parse('value=sum:foo;doesnotexist')
        self.assert_not_none(operator_def)
        operator = operator_def[1]
        self.assert_none(operator(self.ticket))
    
    
    def test_invalid_operator(self):
        operator_def = self.parse('value=invalidoperator:foo;bar')
        self.assert_none(operator_def)
    
    
    def test_div_operator(self):
        operator_def = self.parse('value=div:foo;bar')
        self.assert_not_none(operator_def)
        operator = operator_def[1]
        self.assert_equals(float('0.5'), operator(self.ticket))
    
    
    def test_div_guard_against_division_by_zero(self):
        self.ticket['bar'] = '0'
        operator_def = self.parse('value=div:foo;bar')
        self.assert_not_none(operator_def)
        operator = operator_def[1]
        self.assert_none(operator(self.ticket))
    
    
    def test_div_guard_against_invalid_numbers(self):
        self.ticket['foo'] = 'invalid'
        operator_def = self.parse('value=div:foo;bar')
        self.assert_not_none(operator_def)
        operator = operator_def[1]
        self.assert_none(operator(self.ticket))
    
    
    def test_div_needs_exactly_two_values(self):
        operator_def = self.parse('value=div:foo;bar;quux')
        self.assert_not_none(operator_def)
        operator = operator_def[1]
        self.assert_none(operator(self.ticket))
    
    
    def test_div_operator_can_have_conditions(self):
        self.ticket['baz'] = [FakeTicket(), FakeTicket(), FakeTicket()]
        self.ticket['baz'][0]['type'] = 'lemon'
        self.ticket['baz'][0]['foo'] = 16
        self.ticket['baz'][1]['foo'] = 6
        self.ticket['baz'][2]['foo'] = 2
        
        operator_def = self.parse('value=div:baz.foo|type=lime')
        self.assert_not_none(operator_def)
        operator = operator_def[1]
        self.assert_equals(3, operator(self.ticket))
    
    
    def test_mul_operator(self):
        operator_def = self.parse('value=mul:foo;bar')
        self.assert_not_none(operator_def)
        operator = operator_def[1]
        self.assert_equals(21 * 42, operator(self.ticket))
    
    
    def test_mul_guard_against_invalid_numbers(self):
        self.ticket['foo'] = 'invalid'
        operator_def = self.parse('value=mul:foo')
        self.assert_not_none(operator_def)
        operator = operator_def[1]
        self.assert_none(operator(self.ticket))
    
    
    def test_no_calculation_if_one_part_is_missing(self):
        operator_def = self.parse('value=mul:foo;invalid')
        operator = operator_def[1]
        self.assert_none(operator(self.ticket))
    
    
    def test_no_calculation_if_method_returns_none(self):
        self.ticket['baz'] = None
        operator_def = self.parse('value=mul:foo;get_baz.something_unreachable')
        operator = operator_def[1]
        self.assert_none(operator(self.ticket))
    
    
    def test_no_calculation_if_not_all_property_parts_were_used(self):
        self.ticket['baz'] = list()
        operator_def = self.parse('value=mul:foo;get_baz.something_unreachable')
        operator = operator_def[1]
        self.assert_none(operator(self.ticket))
    
    
    def test_no_calculation_if_method(self):
        bar = FakeTicket(foo=None)
        bar.__iter__ = lambda: [i for i in bar.data]
        self.ticket.bar = bar
        
        operator_def = self.parse('value=mul:foo;bar.foo')
        operator = operator_def[1]
        self.assert_none(operator(self.ticket))
    
    
    def test_do_calculate_if_only_some_parts_missing(self):
        self.ticket['baz'] = [FakeTicket(foo=None), FakeTicket()]
        
        operator_def = self.parse('value=sum:get_baz.foo')
        operator = operator_def[1]
        self.assert_equals(21, operator(self.ticket))
    
    
    def test_dont_assume_all_referenced_objects_are_tickets(self):
        other_class = FakeTicket()
        other_class.my_custom_method = lambda: 42
        
        self.ticket['baz'] = [other_class]
        operator_def = self.parse('value=sum:foo;baz.my_custom_method')
        operator = operator_def[1]
        self.assert_equals(21 + 42, operator(self.ticket))



class TestConfigParsingOfMultipleCalculatedProperties(AgiloTestCase):
    
    def setUp(self):
        self.super()
        self.parse = parse_calculated_fields_definition
        self.ticket = FakeTicket()
    
    
    def test_multiple_calculated_properties(self):
        self.ticket['baz'] = [FakeTicket(), FakeTicket(), FakeTicket()]
        self.ticket['baz'][0]['type'] = 'lemon'
        operator_def = self.parse('value1=sum:baz.foo|type=lime, value2 = div:foo;bar')
        self.assert_not_none(operator_def)
        
        sum_operator = operator_def['value1']
        self.assert_equals(21 + 21, sum_operator(self.ticket))
        
        div_operator = operator_def['value2']
        self.assert_equals(float('0.5'), div_operator(self.ticket))


