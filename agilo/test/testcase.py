# -*- encoding: utf-8 -*-

__all__ = ['AgiloTestCase', 'JSONAgiloTestCase']

import agilo.utils.filterwarnings

from datetime import timedelta

from agilo.api import ValueObject
from agilo.test.pythonic_testcase import PythonicTestCase
from agilo.test.test_env_helper import TestEnvHelper
from agilo.ticket.api import AgiloTicketSystem

from trac.web.api import RequestDone

class AgiloTestCase(PythonicTestCase):
    
    testtype = 'unittest'
    is_abstract_test = True
    plugins = ()
    strict = False
    
    def __init__(self, methodName='run_test'):
        self.super()
        self.env = None
    
    def setUp(self, env_key='agilo'):
        from agilo.test.functional.api import EnvironmentBuilder
        self.env_key = env_key
        from agilo.test import test_env_helper
        test_env_helper.LAST_ENV_KEY = self.env_key
        self.super()
        testenv = EnvironmentBuilder.get_testenv(self.env_key)
        testenv.tester.set_testcase(self)
        self.teh = TestEnvHelper(enable=self.__class__.plugins, strict=self.__class__.strict, env=self.env, env_key=self.env_key)
        self.env = self.teh.get_env()
        self.teh.clear_ticket_system_field_cache()
    
    def sprint_name(self):
        return self.__class__.__name__ + 'Sprint'
    
    def assert_time_equals(self, expected, actual, max_delta=timedelta(seconds=2), msg=None):
        self.assert_almost_equals(expected, actual, max_delta=max_delta, msg=msg)
        
    def tearDown(self):
        from agilo.test.functional.api import EnvironmentBuilder
        testenv = EnvironmentBuilder.get_testenv(self.env_key)
        testenv.tester.set_testcase(None)
        self.super()
        

class JSONAgiloTestCase(AgiloTestCase):
    is_abstract_test = True

    def assert_method_returns_error_with_empty_data(self, *args, **kwargs):
        response = self.assert_method_returns_error(*args, **kwargs)
        self.assert_equals({}, response.current_data)
        return response
    
    def assert_method_returns_error(self, method, req, *args, **kwargs):
        self.assert_raises(RequestDone, method, req, *args, **kwargs)
        response = ValueObject(req.response.body_as_json())
        self.assert_equals(1, len(response.errors))
        return response

    