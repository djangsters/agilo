# -*- encoding: utf-8 -*-
#   Copyright 2008 Agile42 GmbH, Berlin (Germany)
#   Copyright 2007 Andrea Tomasini <andrea.tomasini_at_agile42.com>
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

import os
import re
import threading
import time

from pkg_resources import resource_filename
from trac.config import BoolOption, Option
from trac.core import Component, ExtensionPoint, Interface
from trac.env import Environment
from trac.ticket import Type
from trac.util.compat import set
from trac.util.text import to_unicode
from trac.web.chrome import Chrome

from agilo.utils import MANDATORY_FIELDS, Key
from agilo.utils.compat import exception_to_unicode
from agilo.utils.log import debug

__all__ = ['AgiloConfig', 'get_label', 'IAgiloConfigChangeListener', 
           'IAgiloConfigContributor', 'initialize_config', 'normalize_ticket_type', 
           'populate_section',]


def get_label(attribute_name):
    """Return the label for the given ticket attribute name. Currently this just
    replaces '_' with spaces and capitalizes the first character but maybe we
    will have a more sophisticated mechanism later."""
    return attribute_name.replace('_', ' ').title()

#TODO: (AT) Refactor the type management to allow new type creation from Agilo
# disable Trac type creation and normalize the type from Agilo before saving a 
# new type to Trac
def normalize_ticket_type(t_type):
    """Returns a string representing the normalized ticket type, that is
    the trac type with underscore in place of spaces, that are not suitable 
    for configuration keys."""
    if t_type:
        return t_type.lower().replace(' ', '_')

def set_default_agilo_logo(config):
    """Sets the default agilo logo in case has not been explicitly set
    by the user"""
    header_logo = config.get_section('header_logo')
    if header_logo.get('src') == Chrome.logo_src.default:
        # has not been changed from the default
        header_logo.change_option('src', 'agilo/images/default_logo.png')

def set_agilo_favicon_as_default(config):
    project_section = config.get_section('project')
    if project_section.get('icon') == Environment.project_icon.default:
        project_section.change_option('icon', 'agilo/images/favicon.ico')


class IAgiloConfigChangeListener(Interface):
    """Listeners are notified as soon as the configuration is 
    changed."""
    def config_reloaded(self):
        """This method is called after the configuration was 
        reloaded."""


class IAgiloConfigContributor(Interface):
    """Additional components can participate in the configuration
    process of Agilo. The instance of the current AgiloConfig will 
    be passed through."""
    def initialize(self):
        """This method is called after the initialization of agilo
        config system, and allows external components to enrich the
        configuration with additional parameters."""


class NonMutableDict(dict):
    # just a quick hack for now, replace later if necessary
    
    def __setitem__(self, key, value):
        raise AttributeError()
    
    def __delitem__(self, key):
        raise AttributeError()


# REFACT: Rename to AgiloTicketConfiguration
class AgiloTicketTypeConfiguration(object):
    
    def __init__(self, agilo_config):
        self.agilo_config = agilo_config
        self.fieldnames_per_type = None
        self.aliases_per_trac_type_name = None
        self.initialize_from_configuration()
    
    # --- read configured settings -- -----------------------------------------
    
    def initialize_from_configuration(self):
        self._initialize_field_names_per_type()
        self._initialize_type_alias_names()
    
    def _initialize_field_names_per_type(self):
        type_to_fieldnames = {}
        agilo_types = self.agilo_config.get_available_types(strict=True, with_fields=True)
        for typename, fieldnames in agilo_types.items():
            fieldnames_for_type = set(fieldnames + MANDATORY_FIELDS)
            type_to_fieldnames[typename] = fieldnames_for_type
        self.fieldnames_per_type = NonMutableDict(type_to_fieldnames)
    
    def _trac_type_with_with_correct_casing(self, ticket_type):
        for trac_type_name in self.fieldnames_per_type:
            # AT: Only in config the types are lowercase, all 
            # around agilo we should use Trac types
            if normalize_ticket_type(trac_type_name) == ticket_type:
                return trac_type_name
        # Should never happen? Maybe we can raise an exception?
        return ticket_type
    
    def _initialize_type_alias_names(self):
        trac_type_to_alias = {}
        aliases_configurations = self.agilo_config.get_options_by_postfix(".alias", section=AgiloConfig.AGILO_TYPES)
        for configuration_type_name, l in aliases_configurations.items():
            trac_type_name = self._trac_type_with_with_correct_casing(configuration_type_name)
            alias_name = l[0]
            trac_type_to_alias[trac_type_name] = alias_name
        self.aliases_per_trac_type_name = NonMutableDict(trac_type_to_alias)
    
    # --- query parsed settings -- -- -----------------------------------------
    
    def trac_type_for_alias_or_type(self, alias_or_type, alias_mapping=None):
        if alias_mapping is None:
            alias_mapping = self.aliases_per_trac_type_name.items()
        for trac_type_name, alias_name in alias_mapping:
            if alias_or_type in (alias_name, trac_type_name):
                # Obviously you can confuse Agilo thoroughly if you create an 
                # alias which is the same as a trac type name but that's the 
                # price we're paying for our flexibility
                return trac_type_name
        return None



class AgiloConfig(Component):
    """Component to keep in memory the whole agilo configuration,
    avoiding the reading of the trac.ini file multiple times"""
    
    config_change_listeners = \
        ExtensionPoint(IAgiloConfigChangeListener)
    
    config_contributors = ExtensionPoint(IAgiloConfigContributor)
    
    backlog_filter_attribute = Option('agilo-general', 
        'backlog_filter_attribute', None,
        """Name of a ticket field that all backlogs can be filtered by (e.g., owner, sprint, component). Default: Disabled""")
    
    should_reload_burndown_on_filter_change_when_filtering_by_component = BoolOption('agilo-general',
        'should_reload_burndown_on_filter_change_when_filtering_by_component', False,
        """If set to True and when filtering by component, the burndown chart will show a
        filtered burndown and reload on filter change. Default: False""")
    
    sprints_can_start_or_end_on_weekends = BoolOption('agilo-general', 
        'sprints_can_start_or_end_on_weekends', False,
        """If set to True, sprints can start or end at any day. Otherwise their
        start/end date is shifted to the next Monday. Default: False.""")
    
    burndown_should_show_working_days_only = BoolOption('agilo-general', 
        'burndown_should_show_working_days_only', False,
        """If set to True, all days without capacity (non-working days) are
        hidden in the burndown. Default: False""")
    
    restrict_owner = BoolOption('ticket', 'restrict_owner', False,
        """If set to True, only existing users can be selected as owners of tickets. Default: False""")
    
    # we need to use a different name to have a method 'use_days()'
    use_days_for_estimation = BoolOption('agilo-general', Key.USE_DAYS, False,
      'If set to True, all remaining times are shown as days instead of hours. Default: False')
    
    def set_use_days(self, value):
        self.change_option(Key.USE_DAYS, value, section='agilo-general')
    use_days = property(lambda self: self.use_days_for_estimation, set_use_days)
    
    # Constant definition for Agilo Configuration
    AGILO_BACKLOGS = 'agilo-backlogs'
    AGILO_GENERAL = 'agilo-general'
    AGILO_LINKS = 'agilo-links'
    AGILO_TYPES = 'agilo-types'
    # This is a standard trac section but we use it in Agilo too
    TICKET_CUSTOM = 'ticket-custom'
    
    class ConfigWrapper(object):
        """Class to encapsulate utility method to read, and write into the
        trac config file: trac.ini."""
        def __init__(self, agilo_config, section=None, auto_save=False):
            assert isinstance(agilo_config.env, Environment), \
                "env parameter is not a trac.Environment object!"
            self.env = agilo_config.env
            self.agilo_config = agilo_config
            self._section = section
            self.auto_save = auto_save
            self._types_are_changed = False
        
        def section(self, section):
            if not section:
                section = self._section
            assert section, "Either give a section as argument, or pre-configure it via get_section"
            return section
        
        def get_bool(self, propname, section=None, default=False):
            section = self.section(section)
            return self.env.config.getbool(section, propname, default)
        
        def get_int(self, propname, section=None, default=None):
            section = self.section(section)
            return self.env.config.getint(section, propname, default)
        
        def get_list(self, propname, section=None, default=None):
            """
            Returns the given propname value as a list, default
            to an empty list
            """
            section = self.section(section)
            return self.env.config.getlist(section, propname, default=default)
        
        def get(self, propname, section=None, default=None):
            """Returns a value from the config as string"""
            section = self.section(section)
            value = self.env.config.get(section, propname, default)
            if not value or (hasattr(value, 'strip') and len(value.strip()) == 0):
                value = default
            return value
        
        def has_option(self, propname, section=None):
            section = self.section(section)
            return self.env.config.has_option(section, propname)
        
        def get_options(self, section=None):
            """Returns a dictionary of all the options: value pairs contained 
            into the given section of the config file."""
            section = self.section(section)
            options = dict()
            for opt in self.env.config.options(section):
                value = [p.strip() for p in opt[1].split(',')]
                options[opt[0]] = value
            return options
        
        def get_options_by_prefix(self, prefix, chop_prefix=True, section=None):
            """Returns a dictionary (name/value pairs) of all options
            in the given section that start with the given prefix.
            
            By default the prefix will be removed from all options'
            names. If chop_prefix is set to False the options'
            names will be left untouched."""
            section = self.section(section)
            options = dict()
            for name, value in self.get_options(section).items():
                if name.startswith(prefix):
                    if chop_prefix:
                        # FIXME: I think this is wrong, lot of copy&paste with get_options_by_postfix
                        options[name[:-len(prefix)]] = value
                    else:
                        options[name] = value
            return options
        
        def get_options_by_postfix(self, postfix, chop_postfix=True, section=None):
            """Returns a dictionary (name/value pairs) of all options
            in the given section that end with the given postfix.
            
            By default the postfix will be removed from all options'
            names. If chop_postfix is set to False the options'
            names will be left untouched."""
            section = self.section(section)
            options = dict()
            for name, value in self.get_options(section).items():
                if name.endswith(postfix):
                    key = name
                    if chop_postfix:
                        key = name[:-len(postfix)]
                    options[key] = value
            return options
        
        def get_options_matching_re(self, regexp, section=None):
            """Returns a dictionary (name/value pairs) of all options
            in the given section that match as a whole the given regular 
            expression."""
            section = self.section(section)
            options = dict()
            compiled_regexp = re.compile(regexp)
            for name, value in self.get_options(section).items():
                match_object = compiled_regexp.match(name)
                if match_object and len(match_object.group(0)) == len(name):
                    # only if the complete name matches not only a part of it
                    options[name] = value
            return options
        
        def _should_save(self, save):
            """Return true if the config should be saved"""
            return (save is None and self.auto_save) or save
        
        def _check_changed_types(self, section):
            """Checks if in the transaction parts of the config which are
            affecting the ticket typing have been changed"""
            if section in (AgiloConfig.AGILO_TYPES,
                           AgiloConfig.AGILO_LINKS,
                           AgiloConfig.TICKET_CUSTOM):
                self._types_are_changed = True
        
        def _clean_key_and_value(self, key, value):
            """Cleans the key and the value to suite trac needs in the config
            API, if the key can't be converted to a str and the value can't be
            converted to unicode, they are not valid, so None will be returned
            for both, otherwise the cleaned values."""
            try:
                # make sure that None will not be 'None'
                if value is not None:
                    value = to_unicode(value)
                if key is not None:
                    key = str(key)
            except:
                key = value = None
            return key, value
        
        def set_option(self, propname, value, section=None, save=None):
            """Adds an option to trac.ini unless the option has
            been already defined."""
            section = self.section(section)
            propname, value = self._clean_key_and_value(propname, value)
            if not propname:
                return
            if not self.env.config.get(section, propname):
                self.env.config.set(section, propname, value)
                self._check_changed_types(section)
            self.save_if_wanted(save)
            
        def change_option(self, propname, value, section=None, save=None):
            """Set or change an option in trac.ini."""
            section = self.section(section)
            propname, value = self._clean_key_and_value(propname, value)
            if not propname:
                return
            if self.env.config.get(section, propname) != value:
                self.env.config.set(section, propname, value)
                self._check_changed_types(section)
            self.save_if_wanted(save)
            
        def remove_option(self, propname, section=None, save=None):
            """Removes the propname option from section, or the default section"""
            section = self.section(section)
            try:
                propname = str(propname)
            except:
                return
            agilo_entries = self.get_options_by_prefix(propname, 
                                                       section=section, 
                                                       chop_prefix=False)
            for prop in agilo_entries.keys():
                self.env.config.remove(section, prop)
            self._check_changed_types(section)
            self.save_if_wanted(save)
        
        def remove(self, section=None, save=None):
            section = self.section(section)
            for option_name in self.get_options(section=section):
                self.remove_option(option_name, section=section, save=False)
            # Save only here
            self.save_if_wanted(save)
        
        def reload(self):
            """Reloads config from the disk, so use with care"""
            # We need to force trac's config to reparse the config without
            # touching to avoid endless reloads.
            self.env.config._lastmtime = 0
            self.env.config.parse_if_needed()
        
        def save_if_wanted(self, should_save):
            if self._should_save(should_save):
                self.save()
        
        def save(self):
            """Saves the config"""
            self.wait_until_writing_the_config_would_change_the_mtime()
            self.agilo_config._config_lock.acquire()
            try:
                self.env.config.save()
            finally:
                self.agilo_config._config_lock.release()
            
            # FIXME: (FS) we want to have some notification-like system
            # (AT) in which direction is not clear? Should we notify the ticket
            # system about a changed type? And if so how do we handle batches 
            # without reloading and clearing cache at every operation?
            if self._types_are_changed:
                # something in the type definition changed so we need to reset
                # also the ticket type system.
                from agilo.ticket.api import AgiloTicketSystem
                from agilo.ticket.links.model import LinksConfiguration
                AgiloTicketSystem(self.env).clear_cached_information()
                LinksConfiguration(self.env).reinitialize()
                self._types_are_changed = False
            
            # AT: We force a reload, if the type are changed the TicketSystem 
            # is forcing a reload of the config which will reload all of the
            # components.
            self.agilo_config.reload()
        
        def wait_until_writing_the_config_would_change_the_mtime(self):
            # only do this if we actually have a file backing
            if not self.env.config.filename:
                return
            
            # If we save the config two times in one second, trac will not 
            # notice it needs to reload it
            old_mtime = int(os.path.getmtime(self.env.config.filename))
            while old_mtime == int(time.time()):
                time.sleep(0.1)
        
    # AgiloConfig
    def __init__(self):
        # set a thread locking variable to avoid overlapping of read/write
        self._config_lock = threading.RLock()
        self._config = AgiloConfig.ConfigWrapper(self)
        self._is_agilo_enabled = None
        
        self.ticket_configuration = None
        self.LABELS = None
        # At the end of the reload process the contributors will be
        # called
        # Trac 1.0 compatibility hack - if we remove this we get an infinite recursion
        self.compmgr.components[self.__class__] = self
        self.reload(init=True)
        # Checks if the currently stored template_dir is matching the current
        # agilo installation path
        # fs: This will write the configuration so we *must* reload first
        #  - otherwise we could write outdated values to the filesystem
        # at: I really don't get this, in this way it will be reloaded twice,
        # cause as soon as the config gets saved is also reloaded. Here we are
        # creating the component for the first time, so the config is what has
        # been read from the environment right now... cause trac is starting, so
        # what possibly can be written as "outdated"?
        if self._is_template_dir_outdated():
            self.enable_agilo_ui(save=True)
    
    # exposes the whole api of ConfigWrapper as if it where from this class
    def __getattr__(self, name):
        return getattr(self._config, name)
    
    def get_section(self, name):
        """Returns the config wrapper related to the given section to the caller
        that can use the object as a subset of the config to make changes"""
        return AgiloConfig.ConfigWrapper(self, section=name)
    
    @property
    def ALIASES(self):
        # deprecated
        if self.ticket_configuration is None:
            return None
        return self.ticket_configuration.aliases_per_trac_type_name
    
    @property
    def TYPES(self):
        # deprecated
        if self.ticket_configuration is None:
            return None
        return self.ticket_configuration.fieldnames_per_type
    
    @property
    def is_agilo_enabled(self):
        """Returns True if the given environment has agilo 
        configured"""
        # Actually looking at the configuration to detect if Agilo is 
        # enabled eats quite a lot of CPU time. This small hack of 
        # adding a special attribute to the environment after checking 
        # the configuration once saved us 10 seconds on a 30 second 
        # backlog load in total (~100 items).
        # Please note that the time savings mentioned above will 
        # probably much less after we fixed some other stuff but it 
        # seemed worthwile to optimize this nevertheless.
        # Now we use this in AgiloTicket and AgiloTicketSystem quite 
        # often to provide multi-environment compatibility. Therefore 
        # it is really important to make this method as fast as 
        #possible.
        if self._is_agilo_enabled is None:
#            from agilo.ticket import AgiloTicketSystem
#            result = self.env.is_component_enabled(AgiloTicketSystem)
            agilo_entries = self.get_options_by_prefix('agilo', 
                                                       section='components')
            result = False
            for value in agilo_entries.values():
                if 'enabled' in value:
                    result = True
                    break
            self._is_agilo_enabled = result
        return self._is_agilo_enabled
    
    @property
    def is_agilo_ui_enabled(self):
        """Return True if the Agilo UI is enabled"""
        templates_dir = self.get('templates_dir', 'inherit')
        return templates_dir is not None
    
    def enable_agilo_ui(self, save=False):
        """Enables the Agilo UI by setting the appropriate template_dir in the
        inherit option of the trac.ini"""
        templates_dir = self.calculate_template_path()
        self.change_option('templates_dir', templates_dir, 'inherit',
                           save=save)
    
    def disable_agilo_ui(self, save=False):
        """Disables the Agilo UI by setting the appropriate template_dir in the
        inherit option of the trac.ini"""
        self.change_option('templates_dir', '', 'inherit', save=save)
    
    def is_filtered_burndown_enabled(self):
        is_filter_by_component = self.get('backlog_filter_attribute', section=self.AGILO_GENERAL) == Key.COMPONENT
        is_filtered_burndown = self.get_bool('should_reload_burndown_on_filter_change_when_filtering_by_component', section=self.AGILO_GENERAL)
        return is_filter_by_component and is_filtered_burndown
    
    def _is_template_dir_outdated(self, correct_templates_dir=None):
        """Returns True if the currently stored template_dir, explicitly points
        to an old egg or installation path.
        The correct_templates_dir is only used for testing."""
        # We can't cover cases in which the user explicitly re-mapped the path
        # with symlinks or other aliases.
        if not self.is_agilo_enabled:
            return False
        current_dir = self.get('templates_dir', 'inherit')
        if current_dir is None:
            return True
        if '.egg' not in current_dir:
            return False
        if not os.path.exists(current_dir):
            return True
        if correct_templates_dir is None:
            correct_templates_dir = self.calculate_template_path()
        if current_dir != correct_templates_dir:
            return True
        return False
    
    def enable_agilo(self):
        """Enables agilo for the current environment"""
        self.set_option('agilo.*', 'enabled', 'components')
        self.enable_agilo_ui(save=False)
        self._is_agilo_enabled = True
        self.save()
    
    def disable_agilo(self):
        """Disables agilo for the current environment"""
        self.remove_option('agilo', section='components')
        self.disable_agilo_ui(save=False)
        self._is_agilo_enabled = False
        self.save()
    
    def clear_trac_component_cache(self):
        # trac added a cache for component activation in r8644 - however that 
        # prevents us from dynamically changing components
        if hasattr(self.env, '_rules'):
            del self.env._rules
    
    def calculate_template_path(self):
        """Calculates the template path for the current running agilo"""
        template_path = ''
        try:
            template_path = resource_filename('agilo', 'templates')
        except Exception, e:
            self.env.log.error(exception_to_unicode(e))
        return template_path
    
    def get_available_types(self, strict=False, with_fields=False):
        """Returns a list containing all the defined ticket types for 
        the given environment. With the option strict is limiting the 
        type to the ones with specific type declaration as
        [agilo-types] and also configured into the trac database. With the
        option with_fields returns a dictionary with key the types and values
        the list of fields for that type"""
        ret = None
        if with_fields:
            ret = dict()
        else:
            ret = list()
        
        # Now extract the Agilo type from the property list and the aliases as
        # type might have no extra field beside the mandatory ones
        config = self.get_section(AgiloConfig.AGILO_TYPES)
        agilo_types = config.get_options_matching_re(r'(^[^\.]+$)')
        types_aliases = config.get_options_by_postfix('.alias')
        for type_name in types_aliases:
            if type_name not in agilo_types:
                agilo_types[type_name] = []
        
        agilo_type_names = agilo_types.keys()
        
        for t in Type.select(self.env):
            normalized_type = normalize_ticket_type(t.name)
            if strict and not normalized_type in agilo_type_names:
                continue
            if with_fields:
                ret[t.name] = agilo_types.get(normalized_type, [])
            else:
                ret.append(t.name)
        return ret
    
    def get_fields_for_type(self, exclude_mandatory_and_copy=False):
        """Returns a dictionary {type: fields} for all the types 
        configured. If exclude_mandatory_and_copy is set, than the 
        mandatory fields are removed, and a copy is created, otherwise 
        only a reference is returned"""
        fields_for_type = None
        if exclude_mandatory_and_copy:
            fields_for_type = dict()
            for t_type, fields in self.TYPES.items():
                fields_for_type[t_type] = [f for f in fields if f \
                                           not in MANDATORY_FIELDS]
        else:
            fields_for_type = self.TYPES
        return fields_for_type
    
    def label(self, field_name):
        return self.LABELS.get(field_name) or get_label(field_name)
    
    def notify_other_components_of_config_change(self):
        for listener in self.config_change_listeners:
            listener.config_reloaded()
    
    def reload(self, locked=False, init=False):
        """Load or reload the agilo related configuration parameters
        and recall also the initialize on the IAgiloConfigContributors
        components"""
        # reset also the agilo_enabled to make sure we reread the 
        # config
        self._is_agilo_enabled = None
        if self.is_agilo_enabled:
            if not locked:
                self._config_lock.acquire()
            try:
                from agilo.ticket.api import AgiloTicketSystem
                # patch the query module of trac to use our ticket system
                from trac.ticket import query
                query.TicketSystem = AgiloTicketSystem
                
                # Check if it has not been called from the __init__ in which 
                # case we reload also the configuration file as it might be an
                # explicit reload request
                if not init:
                    self._config.reload()
                self.ticket_configuration = AgiloTicketTypeConfiguration(self)
                self.ticket_configuration.initialize_from_configuration()
                
                # Checks if the advanced UI is enabled
                self.is_agilo_ui = self.get('templates_dir', 
                                            'inherit', None) != None
                # Build a dictionary containing the name: label values for 
                # each ticket field
                fields = AgiloTicketSystem(self.env).get_ticket_fields(new_aliases=self.ticket_configuration.aliases_per_trac_type_name)
                self.LABELS = dict([(f[Key.NAME], 
                                     f.get('label', get_label(f['name']))) \
                                     for f in fields])
                
                # Now loads the configuration contributors
                for contributor in self.config_contributors:
                    contributor.initialize()
            finally:
                if not locked:
                    self._config_lock.release()
            
            self.notify_other_components_of_config_change()
        else:
            # Reset everything in case agilo is not enabled.
            self.ticket_configuration = None
            self.LABELS = None


def populate_section(env, section_name, values, config):
    config_section = config.get_section(section_name)
    
    for option, value in values.items():
        if value.startswith('+'):
            # value starts with "+", we're prepending to existing
            # values
            env.log.debug("[Utils]: Inserting config value: " + \
                          "[%s] => %s += %s" % \
                          (section_name, option, value))
            val = config_section.get(option)
            # strip leading +
            value = value[1:]
            if val and val.strip():
                # the current value is set...
                if val.find(value) == -1:
                    # ... and does not already contain the
                    # value we're trying to prepend
                    val = "%s, %s" % (value, val)
            else:
                # option is currently not set, simply set the new 
                # value
                val = value
            config_section.change_option(option, val, save=False)
        else:
            env.log.debug("[Utils]: Setting config: " + \
                          "[%s] => %s = %s" % \
                          (section_name, option, value))
            config_section.set_option(option, value, save=False)

def initialize_config(env, config_properties):
    """Initialize the trac.ini with the values given in the
    config_properties dictionary, which contains itself
    dictionaries where as keys are set the sections, and as
    values dictionaries composed by the couples option:value."""
    assert isinstance(env, Environment), \
        "env should be an instance of trac.env.Environment, " + \
        "not a %s" % str(env)
    assert type(config_properties) == dict, \
        "config_properties should be of type dict, got a %s" % \
        type(config_properties)
    env.log.debug("[Utils]: Initializing config...")
    
    config = AgiloConfig(env)
    for section_name, values in config_properties.items():
        populate_section(env, section_name, values, config)
    # Make sure to enable Agilo, this also saves the config
    config.clear_trac_component_cache()
    # Replace default logo with Agilo logo if not explicitly changed
    set_default_agilo_logo(config)
    set_agilo_favicon_as_default(config)
    # enabling agilo is also saving the config so we do not need to do
    # that explicitly
    config.enable_agilo()
    debug(env, "[Utils]: Config successfully updated!")
