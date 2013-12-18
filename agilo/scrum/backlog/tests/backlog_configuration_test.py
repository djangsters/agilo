# -*- coding: utf-8 -*-
#   Copyright 2009 Agile42 GmbH
#   Copyright 2011 Agilo Software GmbH All rights reserved 
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.


import agilo.utils.filterwarnings

from agilo.scrum.backlog.backlog_config import BacklogConfiguration
from agilo.test import AgiloTestCase
from agilo.ticket import CustomFields
from agilo.utils import BacklogType, Key, Type
from agilo.utils.config import AgiloConfig


class BacklogConfigurationTest(AgiloTestCase):
    
    def _backlog_config(self, name):
        return BacklogConfiguration(self.env, name=name)
    
    def test_can_return_backlog_name(self):
        self.assert_equals('SomeName', self._backlog_config('SomeName').name)
    
    def test_backlog_knows_if_it_exists(self):
        self.assert_true(self._backlog_config(Key.PRODUCT_BACKLOG).exists)
        self.assert_false(self._backlog_config('SomeName').exists)
    
    def test_create_new_backlog_with_description(self):
        expected_description = 'Some random text'
        backlog_config = BacklogConfiguration(self.env, name='MyBacklog')
        backlog_config.description = expected_description
        self.assert_false(backlog_config.exists)
        backlog_config.save()
        self.assert_true(backlog_config.exists)
        
        fetched_backlog_config = self._backlog_config('MyBacklog')
        self.assert_equals(expected_description, 
                           fetched_backlog_config.description)
    
    def _create_backlog(self, name='ABacklog', description='Something', 
                        backlog_type=BacklogType.MILESTONE, 
                        ticket_types=()):
        backlog_config = self._backlog_config(name)
        backlog_config.type = backlog_type
        backlog_config.description = description
        backlog_config.ticket_types = ticket_types
        backlog_config.save()
        return self._backlog_config(name)
    
    def test_load_and_save_attributes(self):
        backlog_config = self._create_backlog(description='A backlog', backlog_type=BacklogType.SPRINT,
                                              ticket_types=(Type.BUG,))
        self.assert_equals(BacklogType.SPRINT, backlog_config.type)
        self.assert_equals('A backlog', backlog_config.description)
        self.assert_equals((Type.BUG,), backlog_config.ticket_types)
    
    def test_can_change_backlog_configuration(self):
        backlog_name = 'A Backlog'
        new_description = 'A different description'
        backlog_config = self._create_backlog(name=backlog_name)
        backlog_config.description = new_description
        backlog_config.save()
        
        fetched_config = self._backlog_config(backlog_name)
        self.assert_equals(new_description, fetched_config.description)
    
    def test_save_on_new_backlog_config_will_create_it(self):
        backlog_name = 'A Backlog'
        new_description = 'fnord'
        new_config = self._backlog_config(backlog_name)
        new_config.description = new_description
        new_config.save()
        
        self.assert_equals(new_description, self._backlog_config(backlog_name).description)
    
    def test_after_new_backlog_creation_all_attributes_have_default_values(self):
        new_config = self._backlog_config('A Backlog')
        new_config.save()
        self.assert_equals(BacklogType.GLOBAL, new_config.type)
        self.assert_equals((), new_config.ticket_types)
    
    def test_can_read_values_after_setting_them_even_if_backlog_hasnt_been_saved(self):
        new_config = self._backlog_config('A Backlog')
        new_config.ticket_types = ('foo',)
        self.assert_equals(('foo',), new_config.ticket_types)
    
    def test_will_encode_unicode_keys_in_ticket_types_on_set(self):
        new_config = self._backlog_config('A Backlog')
        new_config.ticket_types = (u'foo',)
        self.assert_equals(('foo',), new_config.ticket_types)
        new_config.save()
        
        loaded_config = self._backlog_config('A Backlog')
        self.assert_equals(('foo',), loaded_config.ticket_types)
    
    # Interacting with the config file ..........................................
    
    def test_knows_config_file_base_key(self):
        config = self._backlog_config('Product Backlog')
        self.assert_equals('product_backlog', config._name_for_configuration_file())
        config = self._backlog_config('A Backlog')
        self.assert_equals('a_backlog', config._name_for_configuration_file())
    
    def test_can_read_columns_from_config_file(self):
        config = self._backlog_config('Product Backlog')
        expected = [u'businessvalue:editable', u'roif', u'story_priority:editable', 
            u'rd_points:editable|total_story_points']
        self.assert_equals(expected, config.backlog_columns)
    
    def test_can_set_and_save_columns_to_config(self):
        config = self._backlog_config('A Backlog')
        expected = ['bar', 'baz']
        config.backlog_columns = expected
        self.assert_equals(expected, config.backlog_columns)
        config.save()
        
        config = self._backlog_config('A Backlog')
        self.assert_equals(expected, config.backlog_columns)
    
    def test_can_return_names_of_configured_columns(self):
        config = self._backlog_config('Backlog')
        config.backlog_columns = ['foo', 'bar:editable', 'baz|foo', 'bar:editable|baz']
        self.assert_equals(['id', 'summary', 'foo', 'bar', ['baz', 'foo'], ['bar', 'baz']], config.backlog_column_names())
    
    def test_always_has_id_and_summary_column_prepended(self):
        config = self._backlog_config('Backlog')
        self.assert_equals(['id', 'summary'], config.backlog_column_names())
    
    def test_can_return_human_readable_configuration_names_for_custom_fields(self):
        fields = CustomFields(self.env)
        fields.update_custom_field(dict(
            name='foo',
            type='text',
            label='FOO',
        ))
        config = self._backlog_config('Backlog')
        config.backlog_columns = ['foo', 'bar']
        config.save() # actually create the backlog in the config object so it can be read back 
        # Clear caches so the custom field is actually used
        AgiloConfig(self.env).reload()
                
        names = config.backlog_human_readable_column_labels()
        expected = dict(id='ID', summary='Summary', # defaults
            foo='FOO', # Custom label
            bar='Bar') # Auto generated label
        self.assert_equals(expected, names)
    
    def test_will_remove_column_from_config_if_set_to_none_or_empty_list(self):
        config = self._backlog_config('Sprint Backlog')
        self.assertNotEquals([], config.backlog_columns)
        config.backlog_columns = None
        self.assert_false(config._backlog_config().has_option('sprint_backlog.columns'))
        self.assert_equals([], config.backlog_columns)
        
        config.save()
        config = self._backlog_config('Sprint Backlog')
        self.assert_equals([], config.backlog_columns)
    
    def test_do_not_loose_options_if_new_instance_is_saved_without_changes(self):
        config = self._backlog_config(Key.PRODUCT_BACKLOG)
        config.save()
        
        config = self._backlog_config(Key.PRODUCT_BACKLOG)
        self.assert_equals([Type.REQUIREMENT, Type.USER_STORY], config.ticket_types)
    
    def test_does_not_delete_options_that_are_not_touched(self):
        config = self._backlog_config(Key.PRODUCT_BACKLOG)
        backup = config.description
        config.ticket_types = [Type.USER_STORY]
        config.save()
        
        config = self._backlog_config(Key.PRODUCT_BACKLOG)
        self.assert_equals(backup, config.description)
        
    def test_can_delete_backlog_configuration(self):
        config = self._create_backlog()
        self.assert_true(config.exists)
        config.delete()
        non_existing = self._backlog_config(config.name)
        self.assert_false(non_existing.exists)
    
    def _create_release_backlog(self):
        config = BacklogConfiguration(self.env, 'Release Backlog', BacklogType.MILESTONE, [Type.USER_STORY])
        config.save()
        return config
    
    def test_can_tell_if_planned_items_should_be_displayed(self):
        config = self._create_release_backlog()
        self.assert_false(config.include_planned_items)
        
        config.include_planned_items = True
        self.assert_true(config.include_planned_items)
    
    def test_can_save_option_to_include_planned_items_to_config_file(self):
        config = self._create_release_backlog()
        config.include_planned_items = True
        config.save()
        
        config = self._backlog_config('Release Backlog')
        self.assert_true(config.include_planned_items)
    
    # TODO: consider to make sure the config file is not saved more often than neccessary
    
    # --- Column Information as fields -----------------------------------------
    
    def _field_or_none(self, field_name, fields):
        for field in fields:
            if field[Key.NAME] == field_name:
                return field
        return None
    
    def _field_with_name(self, field_name, fields):
        field = self._field_or_none(field_name, fields)
        if field is not None:
            return field
        self.fail('No field with key %s' % repr(field_name))
    
    def _contains_field(self, field_name, fields):
        return (self._field_or_none(field_name, fields) is not None)
    
    def _fields_with_names(self, fields, field_names):
        selected_fields = []
        for field_name in field_names:
            if self._contains_field(field_name, fields):
                selected_fields.append(self._field_with_name(field_name, fields))
        return selected_fields
    
    def _field_names(self, fields):
        return [field[Key.NAME] for field in fields]
    
    def assert_contains_field(self, field_name, fields):
        if self._contains_field(field_name, fields):
            return
        self.fail('No field %s in %s' % (field_name, self._field_names(fields)))
    
    def assert_not_contains_field(self, field_name, fields):
        if not self._contains_field(field_name, fields):
            return
        self.fail('Field %s found in %s' % (field_name, self._field_names(fields)))
    
    def test_can_return_configured_columns_as_fields(self):
        config = self._backlog_config('Backlog')
        config.backlog_columns = ['sprint', 'status', 'owner']
        
        # sorted by label
        expected = [
            {'name': 'owner', 'label': 'Owner', 'order': 2, 'show': True},
            {'name': 'sprint', 'label': 'Sprint', 'order': 0, 'show': True}, 
            {'name': 'status', 'label': 'Status', 'order': 1, 'show': True}, 
        ]
        fields = config.columns_as_fields()
        selected_fields = self._fields_with_names(fields, (Key.OWNER, Key.SPRINT, Key.STATUS))
        self.assert_equals(expected, selected_fields)
    
    def test_column_fields_exclude_id_summary_and_type(self):
        config = self._backlog_config('Backlog')
        config.backlog_columns = ['sprint', 'status', 'owner']
        
        fields = config.columns_as_fields()
        self.assert_not_contains_field(Key.ID, fields)
        self.assert_not_contains_field(Key.SUMMARY, fields)
        self.assert_not_contains_field(Key.TYPE, fields)
    
    def test_column_fields_contain_alternative_fields(self):
        config = self._backlog_config('Backlog')
        config.backlog_columns = ['rd_points|total_story_points']
        
        story_points_field = {
            'name': 'rd_points', 
            'label': 'Story Points', 
            'order': 0, 
            'show': True, 
            'alternative': 'total_story_points',
        }
        actual_field = self._field_with_name(Key.STORY_POINTS, config.columns_as_fields())
        self.assert_equals(story_points_field, actual_field)
    
    def _all_field_names(self):
        all_field_names = set()
        ticket_configuration = AgiloConfig(self.env).ticket_configuration
        for field_names in ticket_configuration.fieldnames_per_type.values():
            for field_name in field_names:
                all_field_names.add(field_name)
        return all_field_names
    
    def test_column_fields_can_contain_all_possible_ticket_fields(self):
        config = self._backlog_config('Backlog')
        config.backlog_columns = ['sprint', 'status', 'owner']
        config.ticket_types = [Type.USER_STORY]
        
        fields = config.columns_as_fields(all_fields=True)
        for field_name in self._all_field_names():
            if field_name in ('summary', 'type', 'id', 'changetime'):
                continue
            self.assert_contains_field(field_name, fields)
    
    def test_column_fields_only_contain_fields_for_configured_ticket_types(self):
        config = self._backlog_config('Backlog')
        config.ticket_types = [Type.USER_STORY]
        fields = config.columns_as_fields(all_fields=False)
        self.assert_contains_field(Key.STORY_POINTS, fields)
        self.assert_not_contains_field(Key.REMAINING_TIME, fields)
    
    def test_does_not_contain_duplicates_in_column_fields(self):
        config = self._backlog_config('Backlog')
        config.backlog_columns = ['sprint', 'status', 'owner']
        
        fields = config.columns_as_fields()
        sprint_field = self._field_with_name('sprint', fields)
        fields.remove(sprint_field)
        self.assert_not_contains_field('sprint', fields)
    
    def test_all_column_fields_have_labels(self):
        config = self._backlog_config('Backlog')
        config.backlog_columns = ['sprint', 'status', 'owner']
        
        for field in config.columns_as_fields():
            if Key.LABEL in field:
                continue
            self.fail('field %s has no label' % field[Key.NAME])
    
    def test_column_fields_contain_calculated_fields(self):
        config = self._backlog_config('Backlog')
        self.assert_contains_field(Key.TOTAL_REMAINING_TIME, config.columns_as_fields())
    
    def test_column_fields_are_disabled_if_they_are_not_applicable_for_a_configured_ticket_type(self):
        config = self._backlog_config('Requirement Backlog')
        config.ticket_types = [Type.REQUIREMENT]
        
        milestone_field = self._field_with_name(Key.REMAINING_TIME, config.columns_as_fields(all_fields=True))
        self.assert_true(milestone_field['disabled'])


