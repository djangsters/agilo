# -*- encoding: utf-8 -*-
#   Copyright 2009 Agile42 GmbH, Berlin (Germany)
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

from agilo.utils import Key, Type
from agilo.utils.config import AgiloConfig, set_default_agilo_logo,\
    initialize_config
from agilo.test import AgiloTestCase
from agilo.ticket.links.model import LinksConfiguration


class AgiloConfigTest(AgiloTestCase):
    
    def setUp(self):
        self.super()
        self.trac_config = self.env.config
        self.config = AgiloConfig(self.env)
    
    # --------------------------------------------------------------------------
    # Agilo-specific configuration
    
    def test_days_are_fetched_correctly_from_config(self):
        """Regression test: Check that AgiloConfig uses the right configuration
        section and that use_days is really a bool, not a string."""
        self.trac_config.set('agilo-general', Key.USE_DAYS, False)
        self.assert_false(self.config.use_days)
        
        self.trac_config.set('agilo-general', Key.USE_DAYS, True)
        self.config.reload()
        self.assert_true(self.config.use_days)
    
    def test_can_enable_agilo_ui(self):
        self.config.enable_agilo_ui(save=True)
        self.assert_true(self.config.is_agilo_ui_enabled)
        self.config.disable_agilo_ui(save=True)
        self.assert_none(self.config.get('templates_dir', 'inherit'))
        self.assert_false(self.config.is_agilo_ui_enabled)
    
    def test_can_enable_agilo(self):
        self.config.enable_agilo()
        self.assert_true(self.config.is_agilo_enabled)
        self.config.disable_agilo()
        self.assert_false(self.config.is_agilo_enabled)
    
    def test_can_disable_agilo_ui(self):
        self.assert_true(self.config.is_agilo_ui_enabled)
        self.config.disable_agilo_ui(save=True)
        self.assert_false(self.config.is_agilo_ui_enabled)
    
    def _set_template_dir(self, config, dirname):
        config.change_option('templates_dir', dirname, 'inherit', save=True)
    
    def test_configuration_detects_outdated_template_path(self):
        self.assert_true(self.config.is_agilo_enabled)
        self.assert_true(self.config.is_agilo_ui_enabled)
        
        current_dir = '/usr/share/agilo-0.42-r12345.egg/templates'
        self._set_template_dir(self.config, '')
        self.assert_false(self.config.is_agilo_ui_enabled)
        self.assert_true(self.config._is_template_dir_outdated(current_dir))
        
        self._set_template_dir(self.config, '/my/user/configured/template')
        self.assert_false(self.config._is_template_dir_outdated(current_dir))
        
        self._set_template_dir(self.config, current_dir.replace('12345', '54321'))
        self.assert_true(self.config._is_template_dir_outdated(current_dir))
    
    def test_knows_when_filtered_burndown_is_enabled(self):
        self.assert_false(self.config.is_filtered_burndown_enabled())
        self.config.change_option('should_reload_burndown_on_filter_change_when_filtering_by_component', True, section=AgiloConfig.AGILO_GENERAL)
        self.assert_false(self.config.is_filtered_burndown_enabled())
        self.config.change_option('backlog_filter_attribute', 'component', section=AgiloConfig.AGILO_GENERAL)
        self.assert_true(self.config.is_filtered_burndown_enabled())
    
    # --------------------------------------------------------------------------
    # modify low-level configuration
    
    def test_can_remove_whole_sections(self):
        section = self.config.get_section('fnord')
        section.change_option('foo', 'bar')
        self.assert_true('fnord' in self.trac_config.sections())
        self.assert_equals('bar', section.get('foo'))
        section.remove()
        self.assert_not_equals('bar', section.get('foo'))
    
    def test_can_remove_sections_without_getting_it_first(self):
        section = self.config.get_section('fnord')
        section.change_option('foo', 'bar')
        self.assert_true('fnord' in self.trac_config.sections())
        self.assert_equals('bar', section.get('foo'))
        self.config.remove(section='fnord')
        self.assert_false(self.config.get_section('fnord').has_option('foo'))
        self.assert_not_equals('bar', section.get('foo'))
    
    def test_config_knows_if_an_option_is_set(self):
        self.assert_false(self.config.has_option('foo', section='fnord'))
        self.config.change_option('foo', 'bar', section='fnord')
        self.assert_true(self.config.has_option('foo', section='fnord'))
    
    def test_config_reloads_on_change(self):
        self.config.change_option('%s.%s' % (Type.BUG, Key.ALIAS),
                                  'Bugone', section=AgiloConfig.AGILO_TYPES,
                                  save=True)
        self.assert_equals('Bugone', self.config.ALIASES.get(Type.BUG))
    
    def test_config_reloads_links_configuration_on_change(self):
        self.assert_contains('story', LinksConfiguration(self.env).get_allowed_destination_types('requirement'))
        self.config.change_option('allow',
                                  '', section=AgiloConfig.AGILO_LINKS,
                                  save=True)
        self.assert_not_contains('story', LinksConfiguration(self.env).get_allowed_destination_types('requirement'))
    
    def test_config_writing_key_with_capitals(self):
        my_section = self.config.get_section('my-section')
        my_section.change_option('TestMe', 'This is a test', save=True)
        # Test that it is stored
        self.assert_equals('This is a test', 
                         self.env.config.get('my-section', 'TestMe'))
        # Test that is case insensitive
        self.assert_equals('This is a test', 
                         self.env.config.get('my-section', 'testme'))
        self.assert_equals('This is a test', 
                         self.env.config.get('my-section', 'TESTME'))
    
    def test_config_is_normalizing(self):
        my_section = self.config.get_section('my-section')
        my_section.change_option('TestMe', 'This is a test', save=True)
        # check that in reality only the lowecased version is saved in the
        # config file trac.ini
        options = self.config.get_options('my-section')
        self.assert_true('testme' in options,
                        "TestMe not found in: %s" % options)
        self.assert_false('TestMe' in options,
                        "TestMe found in: %s" % options)
    
    def test_config_not_updating_case_sensitive(self):
        my_section = self.config.get_section('my-section')
        my_section.change_option('TestMe', 'This is a test', save=True)
        # Test that it is asymmetric
        # Using set will not set the option as it is case insensitive and is
        # not stored because testme already exists in the trac.ini
        my_section.set_option('TESTME', 'This is another test', save=True)
        self.assert_not_equals('This is another test', 
                            self.env.config.get('my-section', 'TESTME'))
        self.assert_equals('This is a test', 
                         self.env.config.get('my-section', 'TESTME'))
        options = self.config.get_options('my-section')
        self.assert_true('testme' in options,
                         'TestMe not found in: %s' % options)
        self.assert_false('TestMe' in options,
                          'TestMe found in: %s' % options)
    
    def test_config_is_case_insensitive_and_overwrites(self):
        my_section = self.config.get_section('my-section')
        my_section.change_option('TestMe', 'This is a test', save=True)
        # Now change the option and check that also the old key, that is the
        # same actually changed
        my_section.change_option('TESTME', 'This is another test', save=True)
        self.assert_equals('This is another test', 
                         self.env.config.get('my-section', 'TESTME'))
        self.assert_not_equals('This is a test', 
                            self.env.config.get('my-section', 'testme'))
        # Now check what it is stored
        options = self.config.get_options('my-section')
        self.assert_true('testme' in options, 'testme not found in: %s' % options)
        self.assert_false('TESTME' in options, 'TESTME found in: %s' % options)
        # Test it is in the AgiloWrapper also after reload
        self.config.reload()
        self.assert_equals('This is another test', 
                         self.config.get('TestMe', 'my-section'))
    
    def test_config_stores_none_as_empty_string(self):
        my_section = self.config.get_section('my-section')
        my_section.set_option('test', 'This is a test', save=True)
        self.assert_equals('This is a test', 
                         self.env.config.get('my-section', 'test'))
        # Now change the option and check that also the old key, that is the
        # same actually changed
        my_section.change_option('test', None, save=True)
        self.assert_not_equals('This is a test', 
                               self.env.config.get('my-section', 'test'))
        self.assert_equals('', self.env.config.get('my-section', 'test'))
        # Check real config
        self.env.config.set('my-section', 'test', None)
        self.env.config.save()
        self.assert_equals('', self.env.config.get('my-section', 'test'))
    
    def test_dont_strip_non_string_values(self):
        self.assert_true(self.config.get('foo', default=True, section='trac'))
    
    def test_sets_default_agilo_logo_on_new_install(self):
        # should be set by the initialization so let's check it
        agilo_logo_src = 'agilo/images/default_logo.png'
        self.assert_equals(agilo_logo_src, self.env.config.get('header_logo', 'src'))
    
    def test_do_not_sets_default_logo_if_changed(self):
        test_src = 'my_logo'
        agilo_config = AgiloConfig(self.env)
        header_logo = agilo_config.get_section('header_logo')
        header_logo.change_option('src', test_src)
        self.assert_equals(test_src, header_logo.get('src'))
        set_default_agilo_logo(agilo_config)
        self.assert_equals(test_src, header_logo.get('src'))
    
    def test_sets_agilo_favicon_on_new_install(self):
        agilo_favicon = 'agilo/images/favicon.ico'
        self.assert_equals(agilo_favicon, self.env.config.get('project', 'icon'))
    
    def test_doesnt_overwrite_custom_favicons(self):
        custom_favicon = 'fnord'
        project_section = AgiloConfig(self.env).get_section('project')
        project_section.change_option('icon', custom_favicon)
        self.assert_equals(custom_favicon, project_section.get('icon'))
        
        initialize_config(self.env, {})
        project_section = AgiloConfig(self.env).get_section('project')
        self.assert_equals(custom_favicon, project_section.get('icon'))
    

if __name__ == '__main__':
    from agilo.test.testfinder import run_unit_tests
    run_unit_tests(__file__)
