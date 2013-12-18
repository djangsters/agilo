# -*- coding: utf-8 -*-
#   Copyright 2009 Agile42 GmbH
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
#     - Felix Schwarz <felix.schwarz__at__agile42.com>
#     - Martin Häcker <martin.haecker__at__agile42.com>

import os
import time

from windmill.authoring import WindmillTestClient

from agilo.test.functional.api import SingleEnvironmentTestCase
from agilo.test.functional.windmill_tester import WindmillTester
from agilo.test.test_env_helper import TestEnvHelper
from agilo.test.test_util import Usernames
from agilo.utils.config import AgiloConfig


# Register
from agilo.test.functional.agilo_environment import AgiloFunctionalTestEnvironment

__all__ = ['AgiloFunctionalTestCase']


class AgiloFunctionalTestCase(SingleEnvironmentTestCase):
    
    is_abstract_test = True
    
    def __init__(self, *args, **kwargs):
        self.super()
        self.start = None
    
    def setUp(self, env_key='agilo'):
        self.super()
        self.teh = TestEnvHelper(self.env, env_key=self.env_key)
        self.save_configuration()
        self.tester = self.testenv.tester
        if self.is_windmill_test():
            self.testenv.initialize_windmill()
            self.start_new_windmill_testcase(self.classname())
        
        # Backwards compatibility
        self._testenv = self.testenv
        self._tester = self.tester
        
        # If the first test tries to access the contents before browsing a site,
        # this will fail. Therefore we ensure that we go to the front page 
        # before running the tests.
        self.tester.go_to_front()
    
    def tearDown(self):
        self.restore_configuration()
        self.super()
    
    def store_time(self):
        self.start = time.time()
    
    def ensure_min_one_second_passed(self):
        if self.start is None:
            self.store_time()
        passed_time = time.time() - self.start
        if passed_time < 1:
            time.sleep(1 - passed_time)
        self.start = None
    
    def classname(self):
        return self.__class__.__name__
    
    def classname_and_characters_that_should_be_quoted(self):
        return self.classname() + '#'
    
    def milestone_name(self):
        return 'MilestoneFor' + self.sprint_name()
    
    def sprint_name(self):
        return self.classname_and_characters_that_should_be_quoted() + 'Sprint'
    
    def team_name(self):
        return self.classname_and_characters_that_should_be_quoted() + 'Team'
    
    def first_team_member_name(self):
        return self.classname_and_characters_that_should_be_quoted() + 'FirstMember'
    
    def second_team_member_name(self):
        return self.classname_and_characters_that_should_be_quoted() + 'SecondMember'
    
    def product_owner_name(self):
        return Usernames.product_owner
    
    def is_windmill_test(self):
        testtype = getattr(self, 'testtype', None)
        return testtype == 'windmill'
    
    def should_be_skipped(self):
        return self.is_windmill_test() and 'SKIP_WINDMILL' in os.environ
    
    def windmill_tester_class(self):
        return WindmillTester
    
    def start_new_windmill_testcase(self, name):
        self.windmill = WindmillTestClient(name)
        self.windmill_tester = self.windmill_tester_class()(self)
        self.windmill_tester.set_default_timeout(45)
    
    def tracini_file(self, mode='rb'):
        return file(self.testenv.tracini_filename(), mode)
    
    def save_configuration(self):
        self.tracini_contents = self.tracini_file().read()
    
    def set_sprint_can_start_or_end_on_weekends(self):
        # The sprint must be running only for exactly one day, otherwise 
        # confirm commitment is not possible anymore (and the total capacity
        # might be different)
        env = self.testenv.get_trac_environment()
        config = AgiloConfig(env)
        config.change_option('sprints_can_start_or_end_on_weekends', True, section='agilo-general')
        config.save()

    def set_cascade_delete_story_task(self):
        env = self.testenv.get_trac_environment()
        config = AgiloConfig(env)
        config.change_option('delete', 'task-story', section='agilo-links')
        config.save()
    
    def restore_configuration(self):
        if hasattr(self, 'tracini_contents'):
            current_contents = self.tracini_file().read()
            if current_contents != self.tracini_contents:
                self.tracini_file(mode='wb').write(self.tracini_contents)
            self.tracini_contents = None
    
    def remove_all_account_manager_components_from_config(self):
        env = self._testenv.get_trac_environment()
        components = AgiloConfig(env).get_section('components')
        for name in components.get_options_by_prefix('acct_mgr', chop_prefix=False):
            components.remove_option(name, save=False)
        components.save()
    
    def restore_trac_login_module(self):
        self.remove_all_account_manager_components_from_config()
        config = self._testenv.get_trac_environment().config
        config.set('components', 'acct_mgr.*', 'disabled')
        config.set('components', 'trac.web.auth.loginmodule', 'enabled')
        config.save()


