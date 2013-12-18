#!/usr/bin/env python
# -*- coding: utf-8 -*-
#   Copyright 2008 Agile42 GmbH - Andrea Tomasini
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
# 
# Authors:
#     - Andrea Tomasini <andrea.tomasini_at_agile42.com>
#     - Felix Schwarz <felix.schwarz_at_agile42.com>


from agilo.test import AgiloTestCase
from agilo.utils.config import AgiloConfig

def is_email_verification_enabled(env):
    AgiloConfig(env).clear_trac_component_cache()
    try:
        from acct_mgr.web_ui import EmailVerificationModule
        return env.is_component_enabled(EmailVerificationModule)
    except ImportError:
        return None

def assert_status_of_email_verification_module(self, env, expected):
    is_enabled = is_email_verification_enabled(env)
    if is_enabled is None:
        return
    self.assert_equals(expected, is_enabled)


class EmailNonVerificationTest(AgiloTestCase):
    plugins = ['acct_mgr.*']
        
    def test_email_verification_module_is_disabled_after_initialization(self):
        assert_status_of_email_verification_module(self, self.teh.env, False)

class EmailVerificationTest(AgiloTestCase):
    plugins = ['acct_mgr.*', 'acct_mgr.web_ui.emailverificationmodule']

    def test_email_verification_stays_enabled_if_enabled_explicitely_before(self):
        assert_status_of_email_verification_module(self, self.teh.env, True)

class InstallationTest(AgiloTestCase):
    """Tests agilo installation process, calling the main init method"""
    
    def setUp(self):
        self.super()
        self.config = AgiloConfig(self.env)
    
    def test_initialization_adds_agilo_policy(self):
        self.assert_equals(self.config.get('permission_policies', section='trac'),
                          u'AgiloPolicy, DefaultPermissionPolicy, LegacyAttachmentPolicy')
    
    def test_initialization_set_templates_dir(self):
        template_path = self.config.get('templates_dir', section='inherit')
        self.assert_true(template_path.find('templates') > -1)
    

if __name__ == '__main__':
    from agilo.test.testfinder import run_unit_tests
    run_unit_tests(__file__)