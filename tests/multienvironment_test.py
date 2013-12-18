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
#     - Andrea Tomasini <andrea.tomasini__at__agile42.com>

import trac.ticket.model

from agilo.test import AgiloTestCase, TestEnvHelper
from agilo.utils.config import AgiloConfig
import agilo.ticket.web_ui
from agilo.ticket.model import AgiloTicket
from agilo.utils import Key, Type


class MultiEnvironmentTest(AgiloTestCase):
    """
    Tests the support of agilo for multi environments, to make sure that
    agilo components are only instantiated if the environment is belonging to
    an agilo enabled Trac project
    """
    
    def setUp(self):
        self.super()
        self.agilo_config = AgiloConfig(self.env)
    
    def test_knows_if_agilo_is_enabled_or_not(self):
        self.agilo_config.enable_agilo()
        self.assert_true(self.agilo_config.is_agilo_enabled)
        
        self.agilo_config.disable_agilo()
        self.assert_false(self.agilo_config.is_agilo_enabled)
    
    def test_agilo_detection_method(self):
        self.agilo_config.disable_agilo()
        self.assert_false(self.agilo_config.is_agilo_enabled)
        self.env.config.set('components', 'agilo.scrum.web_ui.*', 'enabled')
        
        self.agilo_config.reload()
        self.assert_true(self.agilo_config.is_agilo_enabled)
        self.env.config.set('components', 'agilo.scrum.web_ui.*', 'disabled')
        
        self.agilo_config.reload()
        self.assert_false(self.agilo_config.is_agilo_enabled)
    
    def test_agilo_config_component_if_agilo_is_disabled(self):
        self.agilo_config.disable_agilo()
        
        self.assert_none(self.agilo_config.TYPES, 
                         "Types got initialized also with agilo disabled?")
        self.assert_none(self.agilo_config.ALIASES, 
                         "Aliases got initialized also with agilo disabled?")
        
    def test_agilo_with_parallel_environments(self):
        """
        Tests agilo in parallel with two different environment, one with and
        one without agilo
        """
        ac_agilo = AgiloConfig(self.env)
        ac_agilo.enable_agilo()
        env_no_agilo = TestEnvHelper(env_key=self.env_key)
        ac_no_agilo = AgiloConfig(env_no_agilo.get_env())
        ac_no_agilo.disable_agilo()
        # Now we have two environment in the same python VM
        agilo_ticket = self.teh.create_ticket(Type.TASK,
                                              props={Key.REMAINING_TIME: '2'})
        self.assert_true(isinstance(agilo_ticket, AgiloTicket), 
                        "Got the wrong type: %s" % type(agilo_ticket))
        non_agilo_ticket = env_no_agilo.create_ticket(Type.TASK,
                                                      props={Key.REMAINING_TIME: '2'})
        
        self.assert_true(hasattr(agilo_ticket, '_calculated'))
        self.assert_false(hasattr(non_agilo_ticket, '_calculated'))
        # I found no simple properties which can be checked for differences 
        # using an AgiloTicket and a trac Ticket without doing any more 
        # complicated stuff like linking. If you know some nice tests, please
        # add them here.
        # First I wanted to check if business rules are called for the trac
        # Ticket (must not) but we don't have to really different environments
        # here so that won't work either.


if __name__ == '__main__':
    from agilo.test.testfinder import run_unit_tests
    run_unit_tests(__file__)