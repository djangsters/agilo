# -*- coding: utf-8 -*-
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
#   
from agilo.ticket.api import AgiloTicketSystem
"""
This module contains the basic functional test infrastructure. It doesn't know
anything about trac because the idea is to provide a very generic framework 
which can be reused for any project.

Functional tests are often quite different from unit tests because they interact
with external components and resources (e.g. hard disk, daemons, network 
services). Often you need to do some setup work to prepare the environment, 
configure external services etc.
All the setup work can be quite costly so you may want to reuse the environment
between test runs. This test infrastructure provides some hooks to facilitate
that use case.
"""

from unittest import TestSuite

from agilo_lib.argparse import ArgumentParser

from agilo.test.testcase import AgiloTestCase
from agilo.test.testconfig import TestConfiguration
from agilo.utils.simple_super import SuperProxy

__all__ = ['EnvironmentBuilder', 'FunctionalTestSuite', 
           'SingleEnvironmentTestCase', 'TestEnvironment']

class TestEnvironment(object):
    """
    Test environments can set up a well-defined environment for testing. This 
    may include everything from creating some files and folders to starting 
    specific services.
    
    Sometimes creating a test environment can come with a significant cost so
    the environment provides an API to preserve the environment between test
    runs.
    """
    
    super = SuperProxy()
    
    # TODO: Implement a packed cache to isolate test runs without compromising
    # speed too much. See mock/yum root cache
    
    def __init__(self, config):
        self._external_cleanup_handler = False
        self._created = False
        self._started = False
        self._config = config
    
    def create(self):
        """Create all necessary resources for this TestEnvironment. Return True
        if the environment was not existing before."""
        if self.was_created:
            return False
        self._created = True
        return True
    
    def destroy(self):
        """Remove all resources which were created by this TestEnvironment 
        unconditionally (no check for an external cleanup handler). Return True
        if the environment was created before calling destroy()."""
        if self.was_started:
            self.stop()
        if self.was_created:
            self._created = False
            return True
        return False
    
    def remove(self):
        """Remove all resources if there is no external cleanup handler. Return
        True if the environment was created before this method call (and if it 
        should be )."""
        if not self._external_cleanup_handler:
            return self.destroy()
        return False
    
    def start(self):
        """Start any services needed. Return True if the environment was 
        stopped before."""
        if self.was_started:
            return False
        self._started = True
        return True
    
    def stop(self):
        """Stop all services which were started by start(). When the environment
        was stopped, it should be possible to start() it afterwards without 
        calling create again. Return True if the environment was started before 
        calling stop."""
        if self.was_started:
            self._started = False
            return True
        return False
    
    def use_external_cleanup_handler(self):
        """Notify the environment that there is an external cleanup handler 
        watching so that the resources are only removed when remove() is called
        with force=True.
        This is useful for TestSuites so that you can re-use TestEnvironments
        between test cases (creating a TestEnvironment can take quite some time,
        maybe you like to have more test data in your database)."""
        self._external_cleanup_handler = True
    
    def environment_information(self):
        return None
    
    def get_key(self):
        "Return the key which identifies this specific environment."
        raise NotImplementedError
    
    def config(self):
        return self._config
    
    @property
    def was_created(self):
        return self._created
    
    @property
    def was_started(self):
        return self._started


class EnvironmentBuilder(object):
    """With the environment builder you can get your TestEnvironment. The 
    builder will start the environment if necessary.
    
    This is a essentially singleton so that the builder can track which 
    environments were instantiated before."""
    
    _builder = None
    _known_environments = dict()
    _created_environments = dict()
    _use_cleanup_handler = False
    _testconfig = None
    
    def environment_information_as_string(cls):
        env_info = []
        for env in cls.get_all_initialized_environments():
            info = env.environment_information()
            if info is not None:
                env_info.append(info)
        return '\n'.join(env_info)
    environment_information_as_string = classmethod(environment_information_as_string)
    
    def get_testenv(cls, key, *args):
        """Return the test environment for that key. The EnvironmentBuilder will
        create and start the environment if necessary.
        
        If args were specified and a new environment is created, these args will
        be passed the constructor.
        """
        if key not in cls._created_environments:
            env_class = cls._known_environments[key]
            cls._created_environments[key] = env_class(cls._testconfig, *args)
        env = cls._created_environments[key]
        if cls._use_cleanup_handler:
            env.use_external_cleanup_handler()
        if not env.was_created:
            env.create()
        if not env.was_started:
            env.start()
        return env
    get_testenv = classmethod(get_testenv)
    
    def get_all_initialized_environments(cls):
        """Return all environments which were initialized before."""
        return cls._created_environments.values()
    get_all_initialized_environments = classmethod(get_all_initialized_environments)
    
    def register_environment(cls, key, env_class):
        """Register a new environment class so that it can be used by test cases
        later. You can register another env for the same key as long as the
        previous environment with that key was never created before."""
        assert (key not in cls._created_environments)
        cls._known_environments[key] = env_class
    register_environment = classmethod(register_environment)
    
    def set_config(cls, config):
        cls._testconfig = config
    set_config = classmethod(set_config)
    
    def set_config_from_file(cls, config_filename):
        if config_filename is None:
            config = TestConfiguration()
        else:
            config_file = file(config_filename).read()
            config = TestConfiguration.from_configstring(config_file)
        cls.set_config(config)
    set_config_from_file = classmethod(set_config_from_file)
    
    def use_external_cleanup_handler(cls):
        """Notifies the environment builder that there is an external cleanup
        handler. The builder will set this for all environments."""
        cls._use_cleanup_handler = True
    use_external_cleanup_handler = classmethod(use_external_cleanup_handler)
    
    def destroy_all_environments(cls):
        """Destroy all environments which were created."""
        for env in cls.get_all_initialized_environments():
            env.destroy()
    destroy_all_environments = classmethod(destroy_all_environments)
    
    def stop_all_environments(cls):
        """Destroy all environments which were started."""
        for env in cls.get_all_initialized_environments():
            if env.was_started:
                env.stop()
    stop_all_environments = classmethod(stop_all_environments)


class SingleEnvironmentTestCase(AgiloTestCase):
    """This test case sets up a single test environment (and cares about 
    removing the environment on tearDown). Additionally this test can be skipped
    if not all preconditions are met."""
    
    testtype = 'twill'
    is_abstract_test = True
    
    # support self.super as an equivalent of self(ClassName, self)
    # and self.super() for super(ClassName, self).currentMethod(arguments)
    super = SuperProxy()
    
    def __init__(self, methodName='run_test'):
        self.super()
    
    def setUp(self, env_key='agilo'):
        self.super()
        self.testenv = EnvironmentBuilder.get_testenv(env_key)
        self.env = self.testenv.get_trac_environment()
    
    def should_be_skipped(self):
        """Return True if the test should be skipped."""
        return False
    
    def run_test(self):
        # Execute the test if it should not be skipped.
        # TODO: Raise SkipTest (nose.plugins.skip) if we are running with nosests
        if self.should_be_skipped():
            return
        self.runTest()
    
    # put your own code in runTest
    # def runTest(self):
    #    pass
    
    def tearDown(self):
        if not AgiloTicketSystem(self.env).is_trac_012():
            self.env.shutdown()
        self.testenv.remove()
        self.super()


class FunctionalTestSuite(TestSuite):
    """Provide a TestSuite that knows about the EnvironmentBuilder - all created
    environments will be destroyed after the test run if all tests were 
    successful."""
    
    super = SuperProxy()
    
    def _config_filename(self):
        # We need to use argparse because OptionParser provides no means
        # to parse only known arguments and ignore all others.
        parser = ArgumentParser()
        parser.add_argument('--testconfig', dest='config_filename', default=None,
                            help='file with test-specific configurations')
        (options, args) = parser.parse_known_args()
        return options.config_filename
    
    def run(self, result):
        # Register our own cleanup handler because we can reap all created 
        # environments after the test.
        EnvironmentBuilder.use_external_cleanup_handler()
        EnvironmentBuilder.set_config_from_file(self._config_filename())
        run_result = self.super()
        EnvironmentBuilder.stop_all_environments()
        self._destroy_created_environments(result)
        return run_result
    
    def _destroy_created_environments(self, result):
        if not result.wasSuccessful():
            print EnvironmentBuilder.environment_information_as_string()
            return
        EnvironmentBuilder.destroy_all_environments()

