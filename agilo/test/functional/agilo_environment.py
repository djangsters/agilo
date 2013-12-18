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
import sys

from pkg_resources import resource_filename
from trac.tests.functional import tc
import windmill
from windmill.bin.admin_lib import configure_global_settings, setup, teardown

from agilo.test.test_util import Usernames
from agilo.test.functional.agilo_tester import AgiloTester
from agilo.test.functional.trac_environment import TracFunctionalTestEnvironment
from agilo.utils import Role

__all__ = ['AgiloFunctionalTestEnvironment']




class AgiloFunctionalTestEnvironment(TracFunctionalTestEnvironment):
    
    # TODO: this should ideally cycle through all available browsers on the platform.
    windmill_browser = 'firefox'
    
    # -------------------------------------------------------------------------
    # Overwritten methods
    def __init__(self, config):
        self.super()
        self._add_agilo_to_pythonpath()
        self._windmill_initialized = False
    
    def build_tester(self):
        trac_env = self.get_trac_environment()
        tester = AgiloTester(self.url, self.repo_url, trac_env)
        return tester
    
    def create(self):
        # We need to disable the validation before any request is made
        self._disable_xhtml_validation()
        if not self.super():
            return False
        
        self._print_system_information()
        return True
    
    def stop(self):
        # fs: even though windmill's teardown also removes some files I put it 
        # here because we want to kill Firefox if a test failed - but the 
        # environment is not destroyed when the test failed...
        # For the long run we should ask the windmill guys to split start/stop
        # from teardown so we can reuse that code.
        self.stop_windmill()
        return self.super()
    
    def get_enabled_components(self):
        components = self.super()
        from agilo.ticket import AgiloTicketSystem
        if AgiloTicketSystem.is_trac_1_0():
            components += ['agilo.*', 'webadmin.*', 'acct_mgr.*', 'tracopt.versioncontrol.svn.*']
        else:
            components += ['agilo.*', 'webadmin.*', 'acct_mgr.*']
        return components
    
    def get_disabled_components(self):
        components = self.super()
        components += ['trac.ticket.web_ui.ticketmodule',
                       'trac.ticket.roadmap.roadmapmodule',
                       'trac.ticket.api.ticketsystem',
                       # If registration is enabled, this might affect our tests
                       # because users will be limited to anonymous.
                       'acct_mgr.web_ui.EmailVerificationModule',
                      ]
        return components
    
    def get_config_options(self):
        options = self.super()
        options += [
            ('trac', 'permission_policies', 'AgiloPolicy, DefaultPermissionPolicy, LegacyAttachmentPolicy'),
            ('account-manager', 'password_file', self.htpasswd),
            # compatible with TracAccountManager >= 0.4
            ('account-manager', 'htpasswd_file', self.htpasswd),
            ('account-manager', 'generated_password_length', '8'),
            ('account-manager', 'hash_method', 'HtDigestHashMethod'),
            ('account-manager', 'password_store', 'HtPasswdStore'),
            
            ('logging', 'log_type', 'None'),
            # usually logging only slows down the tests and no one will look
            # at the logs anyway.
            # However we need to find out why we're seeing 'Connection reset by
            # peer' test failures on our build machines.
            # ('logging', 'log_type', 'file'),
            # ('logging', 'log_level', 'DEBUG'),
            # ('logging', 'log_file', 'trac.log'),
        ]
        return options
    
    def get_users_and_permissions(self):
        userinfo = self.super()
        userinfo += [(Usernames.scrum_master, [Role.SCRUM_MASTER]),
                     (Usernames.product_owner, [Role.PRODUCT_OWNER]),
                     (Usernames.team_member, [Role.TEAM_MEMBER]),
                     (Usernames.second_team_member, [Role.TEAM_MEMBER]),]
        return userinfo
    
    @classmethod
    def get_key(cls):
        return 'agilo'
    # -------------------------------------------------------------------------
    # New methods for Agilo
    
    def _add_agilo_to_pythonpath(self):
        # Export in the environment the PYTHONPATH including the current
        # Agilo root dir, this is needed because trac will be launched as
        # an external process via Popen, and the sys.path with not be propagated
        agilo_root = os.path.abspath(resource_filename('agilo', '..'))
        # msg = "Exporting PYTHONPATH with current Agilo for Trac standalone:%s" % agilo_root
        # print msg
        new_pythonpath = os.getenv('PYTHONPATH', '') + os.pathsep + agilo_root
        os.environ['PYTHONPATH'] = new_pythonpath
    
    def _disable_xhtml_validation(self):
        # We need to disable trac's validation of the returned HTML pages 
        # because we generate invalid xhtml sometimes (e.g. custom attributes
        # in the search input field, ul elements without li).
        # In the old suite this worked implicitely because we reset the browser
        # in the beginning.
        b = tc.get_browser()
        # TODO: This is a bit brutal right now but actually there are no other
        # post load hooks used right now. Refine if necessary.
        b._post_load_hooks = []
    
    def _print_system_information(self):
        """Prints the system information for better debugging"""
        sys_info = ['============= System Information =============']
        for prop, value in self.get_trac_environment().systeminfo:
            sys_info.append("  %s: '%s'" % (prop.ljust(10), value))
        sys_info.append('==============================================')
        self.logfile.write(''.join(sys_info))
    
    # -------------------------------------------------------------------------
    # methods for windmill support
    
    def is_windmill_initialized(self):
        return self._windmill_initialized
    
    def initialize_windmill(self):
        if self.is_windmill_initialized():
            return
        self._windmill_initialized = True
        # global windmill setup
        # Code adapted from http://trac.getwindmill.com/browser/trunk/windmill/authoring/unit.py
        windmill.stdout = self.logfile
        windmill.stderr = self.logfile
        windmill.stdin = sys.stdin
        
        configure_global_settings(logging_on=False)
        windmill.settings['TEST_URL'] = self.url
        self.disable_windmill_console_log_spam()
        #windmill.settings['INSTALL_FIREBUG'] = 'firebug'
        
        # Then start windmill and the browser
        self.windmill_shell = setup()
        self.windmill_shell['start_'+self.windmill_browser]()
    
    def stop_windmill(self):
        # The Firefox test wrapper currently can't kill the browser (on OS X)
        # after a testrun -- see http://trac.getwindmill.com/ticket/313
        if self.is_windmill_initialized():
            try:
                teardown(self.windmill_shell)
            except (ValueError, AssertionError), exception:
                # Mozrunner mac has a bug in the teardown code that will spit this out quite regulary
                # I swallow this exception here because the global exception handler throws away the test 
                # output if this exception gets through which can easily make the entire test run unusable
                # This should be solved by mozrunner v2 in windmill 1.4 or 1.5
                # TODO: log the exception
                pass
            self._windmill_initialized = False
    
    def disable_windmill_console_log_spam(self):
        # Windmill overwrites the root loggers level if present - so we feed it whatever was configured before
        # See http://trac.getwindmill.com/ticket/314
        # See <windmill>/bin/admin_lib.py
        windmill.settings['CONSOLE_LOG_LEVEL'] = 'ERROR'





# Register this module with the EnvironmentBuilder
from agilo.test.functional.api import EnvironmentBuilder
EnvironmentBuilder.register_environment(AgiloFunctionalTestEnvironment.get_key(),
                                        AgiloFunctionalTestEnvironment)

