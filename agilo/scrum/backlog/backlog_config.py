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

from trac.util.compat import set

from agilo.core.model import PersistentObject, Field, PersistentObjectModelManager
from agilo.scrum import BACKLOG_TABLE
from agilo.ticket.links import LinksConfiguration
from agilo.utils import BacklogType, Key
from agilo.utils.config import AgiloConfig
from agilo.utils.sorting import By, Column, SortOrder

__all__ = ['BacklogConfiguration']


# REFACT: remove 'backlog_' prefix - we're in the backlog config object
# FIXME (AT): with the separation of the configuration from the object
# we created a break in the Backlog structure as for what is a Backlog
# instance and what is a BacklogType, without a configuration???
class BacklogConfiguration(PersistentObject):
    """
    Encapsulates a backlog configuration.
    Historically this information is scattered in the DB+trac.ini. This object
    provides a unified interface to the internal implementation.
    
    name (db)
    description (db)
    backlog_type (db)
    
    ticket_types (db)
    displayed_fields (file)
    show_planned_items (file)  – added in trac.ini so we don't need another db upgrade
    
    sorting_rules aka sorting_keys (db) – unused, only for historic reasons.
    """
    class Meta(object):
        table_name = BACKLOG_TABLE
        name = Field(primary_key=True)
        description = Field()
        type = Field(type='integer', db_name='b_type')
        ticket_types = Field(type='serialized')
        sorting_rules = Field(type='serialized', db_name='sorting_keys')
    
    def __init__(self, env, name=None, type=None, ticket_types=None,
                 load=True, db=None):
        # OVERRIDE: sets sensible default for the properties
        super(BacklogConfiguration, self).__init__(env, name=name,
                                                   type=type or BacklogType.GLOBAL,
                                                   ticket_types=ticket_types or (),
                                                   sorting_rules={},
                                                   load=load, db=db)
    
    # --- public API -----------------------------------------------------------
    
    def _get_backlog_columns(self):
        return self._config_get_list('columns')
    
    def _set_backlog_columns(self, list_of_column_names_with_options):
        self._config_set_list('columns', list_of_column_names_with_options)
    
    backlog_columns = property(_get_backlog_columns, _set_backlog_columns)
    
    
    def _include_planned_items(self):
        return self._config_get_bool('include_planned_items')
    
    def _set_include_planned_items(self, value):
        self._config_set('include_planned_items', value)
    
    include_planned_items = property(_include_planned_items, _set_include_planned_items)
    
    
    def backlog_column_names(self):
        """Returns the column names ready to be used as json for the gui"""
        def parser(column_string):
            if '|' in column_string:
                return map(parser, column_string.split('|'))
            return column_string.split(':')[0]
        # Not sure why id and summary where hardcoded and not saved to the config
        return ['id', 'summary'] + map(parser, self.backlog_columns)
    
    def backlog_human_readable_column_labels(self):
        names = dict()
        for field_name in self.backlog_column_names():
            if isinstance(field_name, (tuple, list)):
                field_name = field_name[0]
            names[field_name] = self._agilo_config().label(field_name)
        # Not sure why id and summary where hardcoded and not saved to the config
        names.update({
            'id' : 'ID',
            'summary' : 'Summary'
        })
        return names
    
    # --- fields for all possible backlog columns (backlog admin) --------------
    
    def _all_configured_ticket_fields(self):
        field_names = set()
        ticket_config = AgiloConfig(self.env).ticket_configuration
        for field_names_for_type in ticket_config.fieldnames_per_type.values():
            for field_name in field_names_for_type:
                field_names.add(field_name)
        return list(field_names)
    
    def _field_names_for_backlog_types(self):
        field_names = set()
        ticket_config = AgiloConfig(self.env).ticket_configuration
        for type_name in self.ticket_types:
            # don't trust the type_name in self.ticket_types, backlog admin page
            # does not do validation on that
            if type_name not in ticket_config.fieldnames_per_type:
                continue
            fields_for_this_type = ticket_config.fieldnames_per_type[type_name]
            field_names.update(set(fields_for_this_type))
        return field_names
    
    def _create_field_for(self, field_name, order=None, show=False, disabled=None):
        preferred_field_name = field_name
        if isinstance(field_name, (tuple, list)):
            preferred_field_name = field_name[0]
        label =  self._agilo_config().label(preferred_field_name)
        field = {
            Key.NAME: preferred_field_name, 
            Key.LABEL: label,
            Key.SHOW: show,
        }
        if order is not None:
            field[Key.ORDER] = order
        if disabled is not None:
            field['disabled'] = disabled
        if preferred_field_name != field_name:
            field['alternative'] = field_name[-1]
        return field
    
    def _possible_field_names(self, fields, all_fields):
        calculated_field_names = LinksConfiguration(self.env).get_calculated() or []
        field_names_for_configured_types = self._field_names_for_backlog_types()
        possible_field_names = list(field_names_for_configured_types)
        if all_fields:
            possible_field_names = self._all_configured_ticket_fields()
        return possible_field_names + calculated_field_names
    
    def _add_fields_for_nonconfigured_columns(self, fields, all_fields=False):
        present_field_names = [field[Key.NAME] for field in fields]
        field_names_to_skip = present_field_names + ['id', 'summary', 'type', 'changetime']
        field_names_for_configured_types = self._field_names_for_backlog_types()
        for field_name in self._possible_field_names(fields, all_fields):
            if field_name in field_names_to_skip:
                continue
            disabled = (field_name not in field_names_for_configured_types)
            fields.append(self._create_field_for(field_name, disabled=disabled))
    
    def _fields_for_configured_columns(self):
        fields = []
        for field_name in self.backlog_column_names():
            if field_name in ('id', 'summary', 'type'):
                continue
            field = self._create_field_for(field_name, order=len(fields), show=True)
            fields.append(field)
        return fields
    
    def columns_as_fields(self, all_fields=False):
        fields = self._fields_for_configured_columns()
        self._add_fields_for_nonconfigured_columns(fields, all_fields=all_fields)
        fields.sort(cmp=By(Column(Key.LABEL), SortOrder.ASCENDING))
        return fields
    
    # other convenience stuff...................................................
    
    def save(self, db=None):
        """Saves the changes of configuration to the DB and the config file
        alike"""
        super(BacklogConfiguration, self).save(db=db)
        self._save_to_config()
    
    # --- helpers --------------------------------------------------------------
    
    def _agilo_config(self):
        return AgiloConfig(self.env)
    
    def _backlog_config(self):
        return self._agilo_config().get_section(AgiloConfig.AGILO_BACKLOGS)
    
    def _set_default_values(self):
        defaults = (('type', BacklogType.GLOBAL), ('ticket_types', ()),
                    ('planned_items', False))
        for (key, default) in defaults:
            if getattr(self, key) is None:
                setattr(self, key, default)
    
    # --- config file manipulation ---------------------------------------------
    
    def _name_for_configuration_file(self):
        return self.name.lower().replace(' ', '_')
    
    def _config_key(self, a_key):
        return '%s.%s' % (self._name_for_configuration_file(), a_key)
    
    def _config_get_list(self, a_key):
        return self._backlog_config().get_list(self._config_key(a_key))
    
    def _config_set_list(self, a_key, a_list):
        if not a_list:
            return self._backlog_config().remove_option(self._config_key(a_key))
        
        joined_list = ', '.join(a_list)
        self._backlog_config().change_option(self._config_key(a_key), joined_list)
    
    def _config_get_bool(self, a_key):
        return self._backlog_config().get_bool(self._config_key(a_key))
    
    def _config_set(self, a_key, a_value):
        self._backlog_config().change_option(self._config_key(a_key), a_value, save=False)
    
    def _save_to_config(self):
        config = self._backlog_config()
        config.change_option(self._config_key('name'), self.name, save=False)
        config.change_option(self._config_key('include_planned_items'), 
                             self.include_planned_items, save=False)
        config.save()


class BacklogConfigurationModelManager(PersistentObjectModelManager):
    """Model Manager for Backlog Configuration objects"""
    model = BacklogConfiguration
