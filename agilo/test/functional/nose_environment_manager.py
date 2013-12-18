# -*- encoding: utf-8 -*-
#   Copyright 2008-2010 Agile42 GmbH, Berlin (Germany)
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
This nose plugin manages destruction of functional test environments after a
test run.
"""
# Be careful not to import symbols from this module in the rest of Agilo 
# - otherwise nose will become a dependency for all Agilo installations!

from nose.plugins import Plugin

from agilo.test.functional import EnvironmentBuilder
from agilo.utils.simple_super import SuperProxy


__all__ = ['NoseEnvironmentManager']


class NoseEnvironmentManager(Plugin):
    
    super = SuperProxy()
    
    def __init__(self):
        self.super()
        self._config_filename = None
    
    # ------------------------------------------------------------------------
    # Implementations of nose plugin API
    
    def options(self, parser, env=None):
        parser.add_option('--share-environments-between-tests', dest='share_environments', 
                          default=None,
                          help='Keep agilo functional test environment between tests')
        parser.add_option("--testconfig", dest="config_filename", default=None,
                          help="file with test-specific configurations")
    
    def configure(self, options, config):
        if options.share_environments:
            self.enabled = True
            if options.config_filename:
                self._config_filename = options.config_filename
    
    def begin(self):
        EnvironmentBuilder.set_config_from_file(self._config_filename)
        EnvironmentBuilder.use_external_cleanup_handler()
    
    def finalize(self, result):
        EnvironmentBuilder.stop_all_environments()
        self._destroy_created_environments(result)
    
    # ------------------------------------------------------------------------
    # internal convenience functionality
    
    def _destroy_created_environments(self, result):
        if not result.wasSuccessful():
            print EnvironmentBuilder.environment_information_as_string()
            return
        EnvironmentBuilder.destroy_all_environments()

