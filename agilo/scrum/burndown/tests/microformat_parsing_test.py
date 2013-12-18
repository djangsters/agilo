# -*- encoding: utf-8 -*-
#   Copyright 2010 Agile42 GmbH, Berlin (Germany)
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

from datetime import timedelta

from agilo.core import PersistentObjectManager
from agilo.scrum.burndown import BurndownDataChange, BurndownDataConstants
from agilo.test import AgiloTestCase
from agilo.utils import AgiloConfig, Key
from agilo.utils.compat import exception_to_unicode, json
from agilo.utils.days_time import now


class BurndownDataChangeTest(AgiloTestCase):
    
    def setUp(self):
        self.super()
        PersistentObjectManager(self.env).create_table(BurndownDataChange)
        self.change = BurndownDataChange(self.env)
        self.sprint = self.teh.create_sprint(self.sprint_name())
    
    def create_change(self, **kwargs):
        change = BurndownDataChange(self.env)
        change.type = 'fnord'
        change.scope = self.sprint.name
        change.when = now()
        for key, value in kwargs.items():
            setattr(change, key, value)
        return change
    
    
    def test_return_empty_values_if_no_delta_set(self):
        self.assert_equals(0, self.change.delta())
        self.assert_equals(dict(), self.change.markers())
    
    def test_can_parse_single_number_in_microformat(self):
        self.change.value = '3'
        self.assert_equals(3, self.change.delta())
    
    def test_can_parse_markers_in_microformat(self):
        self.change.value = json.dumps([3, dict(component='foo')])
        self.assert_equals(3, self.change.delta())
        self.assert_equals(dict(component='foo'), self.change.markers())
    
    def test_raises_if_neither_number_nor_array_is_used_asmicroformat(self):
        self.change.value = json.dumps('fnord')
        self.assert_raises(ValueError, self.change.delta)
        self.assert_raises(ValueError, self.change.markers)
    
    def test_can_set_delta(self):
        self.change.set_delta(3)
        self.assert_equals(3, self.change.delta())
    
    def test_can_set_markers(self):
        self.change.set_markers(dict(fnord=23))
        self.assert_equals(dict(fnord=23), self.change.markers())
    
    def test_can_set_component_markers(self):
        self.teh.enable_burndown_filter()
        self.change.set_component_marker('fnord')
        self.assert_equals('fnord', self.change.marker_value(Key.COMPONENT))
    
    def test_raises_on_component_set_if_filter_by_component_is_not_enabled(self):
        error = self.assert_raises(AssertionError, self.change.set_component_marker, 'fnord')
        self.assert_true("should_reload_burndown_on_filter_change_when_filtering_by_component" in exception_to_unicode(error))
        self.assert_true("backlog_filter_attribute" in exception_to_unicode(error))
        self.teh.enable_burndown_filter()
        self.change.set_component_marker('fnord')
    
    def test_can_save_and_load_delta_from_database(self):
        change = self.create_change()
        change.set_delta(3)
        self.assert_equals(3, change.delta())
        change.save()
        loaded_again = BurndownDataChange(self.env, id=change.id)
        self.assert_equals(3, loaded_again.delta())
    
    def test_save_raises_if_any_value_is_missing(self):
        def change_with_value(**kwargs):
            kwargs.setdefault('value', '')
            return self.create_change(**kwargs)
        
        change_with_value().save()
        self.assert_raises(ValueError, change_with_value(type=None).save)
        self.assert_raises(ValueError, change_with_value(scope=None).save)
        self.assert_raises(ValueError, change_with_value(when=None).save)
        self.assert_raises(ValueError, change_with_value(value=None).save)
    
    def test_saves_easy_microformat_if_possible(self):
        change = self.create_change()
        change.set_delta(23)
        self.assert_equals(23, change.delta())
        self.assert_equals('23', change.value)
        
    
    def test_easy_generation_of_burndown_entries(self):
        actual = BurndownDataChange(self.env).update_values(type='fnord', scope=self.sprint.name, when=now(), delta=3)
        expected = self.create_change(type='fnord', scope=self.sprint.name, when=now())
        expected.set_delta(3)
        self.assert_equals(expected.type, actual.type)
        self.assert_equals(expected.scope, actual.scope)
        self.assert_almost_equals(expected.when, actual.when, max_delta=timedelta(seconds=2))
        self.assert_equals(expected.delta(), actual.delta())
        self.assert_equals(expected.markers(), actual.markers())
    
    def test_can_create_aggregation_skip_fake_entry(self):
        starter = BurndownDataChange.create_aggregation_skip_marker(self.env, 'Fnord')
        self.assert_true(starter.has_marker(BurndownDataConstants.SKIP_AGGREGATION))
    
