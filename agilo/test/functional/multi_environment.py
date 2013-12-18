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

import os

from pkg_resources import resource_filename

from agilo.test.functional.agilo_tester import AgiloTester
from agilo.test.functional.agilo_environment import \
    AgiloFunctionalTestEnvironment, TracFunctionalTestEnvironment

__all__ = ['MultiEnvironmentFunctionalTestEnvironment']


class MultiEnvironmentFunctionalTestEnvironment(AgiloFunctionalTestEnvironment):
    """This environment creates actually two environments (one is Agilo-enabled
    while the other is just plain trac) but starts only one tracd which will 
    serve both projects.
    
    This can be used to test that our monkey-patching is not too intrusive."""
    
    # -------------------------------------------------------------------------
    # Overwritten methods
    def __init__(self, config):
        self.super()
        self.use_single_env = False
        self._trac_functional_test_environment = TracFunctionalTestEnvironment(config)
    
    def build_tester(self):
        trac_env = self.get_trac_environment()
        tester = AgiloTester(self.url, self.repo_url, trac_env)
        return tester
    
    def create(self):
        if not self.super():
            return False
        
        # We're in a multi-environment
        base_url = self.url
        self.url = self.url + '/' + os.path.basename(self.envdir)
        
        trac_env = self._trac_functional_test_environment
        assert trac_env.create()
        trac_env.url = base_url + '/' + os.path.basename(trac_env.envdir)
        return True
    
    def _get_process_arguments(self):
        args = self.super()
        trac_env_dir = self._trac_functional_test_environment.envdir
        assert trac_env_dir != None
        args.append(trac_env_dir)
        return args
    
    def start(self):
        if not self.super():
            return False
        trac_env = self._trac_functional_test_environment
        trac_env.tester = trac_env.build_tester()
        trac_env.tester.url = trac_env.url
        return True
    
    def destroy(self):
        self.super()
        self._trac_functional_test_environment.destroy()
    
    def environment_information(self):
        first_env_info = self.super()
        second_env_info = self._trac_functional_test_environment.environment_information()
        return ' -- '.join([first_env_info, second_env_info])
    
    def get_key(cls):
        return 'agilo_multi'
    get_key = classmethod(get_key)



# Register this module with the EnvironmentBuilder
from agilo.test.functional.api import EnvironmentBuilder
EnvironmentBuilder.register_environment(MultiEnvironmentFunctionalTestEnvironment.get_key(),
                                        MultiEnvironmentFunctionalTestEnvironment)

