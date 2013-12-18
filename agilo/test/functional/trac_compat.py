# -*- coding: utf-8 -*-
#   Copyright 2008-2009 Agile42 GmbH, Berlin (Germany)
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
"""
This module contains a test case stuff for compatibility with the old trac 
functional test cases.
"""

from agilo.test.functional.api import SingleEnvironmentTestCase
# Register the environment by importing it.
from agilo.test.functional.trac_environment import TracFunctionalTestEnvironment

__all__ = ['FunctionalTestCaseSetup']


class FunctionalTestCaseSetup(SingleEnvironmentTestCase):
    
    def setUp(self, env_key='agilo'):
        self.super()
        
        # Backwards compatibility
        self._testenv = self.env
        self._tester = self.env.tester
        self.testenv.tester.login('admin')


