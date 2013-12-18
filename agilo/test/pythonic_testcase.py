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
#   Author: 
#       - Felix Schwarz <felix.schwarz__at__agile42.com>
#       - Martin Häcker <martin.haecker__at__agile42.com>
"""The idea is to improve Python's unittest.TestCase class with a more pythonic
API and some convenience functionality."""

from unittest import TestCase

from agilo.utils.simple_super import SuperProxy

# REFACT: is this actually a good idea? I like it that it's immediately clear when reading the code if a function/class is in __all__ or not. However the name is way too overloaded. --dwt
__all__ = ['PythonicTestCase']
def public(function):
    global __all__
    __all__.append(function.__name__)
    return function

@public
def assert_true(actual, message=None, failure_exception=AssertionError):
    assert_equals(True, actual, message=message, failure_exception=failure_exception)

@public
def assert_falsish(actual, message=None, failure_exception=AssertionError):
    if not actual:
        return
    raise failure_exception(message)
#    assert_equals(False, actual, message=message, failure_exception=failure_exception)

@public
def assert_almost_equals(expected, actual, max_delta=0, message=None, failure_exception=AssertionError):
    abs_difference = abs(expected - actual)
    if abs_difference > max_delta:
        default_msg = '%s != %s with maximal difference of %s' % (repr(expected), repr(actual), repr(max_delta))
        raise failure_exception, (message or default_msg)

@public
def assert_equals(expected, actual, message=None, failure_exception=AssertionError):
    if expected == actual:
        return
    default_message = '%s != %s' % (repr(expected), repr(actual))
    raise failure_exception, (message or default_message)

@public
def assert_raises(exception_type, callable, message=None, failure_exception=AssertionError):
    try:
        callable()
    except exception_type, exception:
        return exception
    message = message or '%s not raised' % exception_type.__name__
    raise failure_exception, message

@public
def assert_contains(expected_value, actual_iterable, message=None, failure_exception=AssertionError):
    if expected_value in actual_iterable:
        return
    
    message = message or '%s not in %s' % (repr(expected_value), repr(actual_iterable))
    raise failure_exception(message)

@public
def assert_dict_contains(expected_sub_dict, actual_super_dict, message=None, failure_exception=AssertionError):
    if message is not None:
        raise NotImplementedError, 'patches welcome'
    
    if failure_exception is not AssertionError:
        raise NotImplementedError, 'patches welcome'
    
    for key, value in expected_sub_dict.items():
        message = "%s:%s not in %s" % (repr(key), repr(value), repr(actual_super_dict))
        assert_contains(key, actual_super_dict, message=message)
        assert_equals(value, actual_super_dict[key], message=message)

@public
def assert_smaller_than(smaller, larger, message=None, failure_exception=AssertionError):
    if smaller < larger:
        return
    default_message = '%s is not smaller than %s' % (repr(smaller), repr(larger))
    raise failure_exception(message or default_message)

@public
def assert_larger_than(larger, smaller, message=None, failure_exception=AssertionError):
    if larger > smaller:
        return
    default_message = '%s is not larger than %s' % (repr(larger), repr(smaller))
    raise failure_exception(message or default_message)

@public
def assert_is_empty(a_value, message=None, failure_exception=AssertionError):
    if len(a_value) == 0:
        return
    
    default_message = "%s is not empty" % repr(a_value)
    raise failure_exception(message or default_message)


class PythonicTestCase(TestCase):
    
    super = SuperProxy()
    is_abstract_test = True
    
    def failure_exception(self):
        return self.failureException
    
    def assert_raises(self, exception_type, callable, *args, **kwargs):
        curried_callable = lambda: callable(*args, **kwargs)
        return assert_raises(exception_type, curried_callable, failure_exception=self.failure_exception())
    
    def assert_false(self, actual, msg=None):
        assert_equals(False, actual, message=msg, failure_exception=self.failure_exception())
    
    def assert_falsish(self, actual, msg=None):
        self.assertFalse(actual, msg=msg)
    
    def assert_true(self, actual, msg=None):
        assert_true(actual, message=msg, failure_exception=self.failure_exception())
    
    def assert_trueish(self, actual, msg=None):
        self.assertTrue(actual, msg=msg)
    
    def assert_none(self, actual, msg=None):
        assert_equals(None, actual, message=msg, failure_exception=self.failure_exception())
    
    def assert_not_none(self, actual, msg=None):
        self.assert_not_equals(None, actual, msg=msg)
    
    def assert_equals(self, expected, actual, msg=None):
        assert_equals(expected, actual, message=msg, failure_exception=self.failure_exception())
    
    def assert_not_equals(self, expected, actual, msg=None):
        self.assertNotEquals(expected, actual, msg=msg)
    
    def assert_almost_equals(self, expected, actual, places=None, msg=None, max_delta=None):
        if (places is not None) and (max_delta is not None):
            raise TypeError('Please use either places or max_delta!')
        if max_delta is not None:
            assert_almost_equals(expected, actual, max_delta, msg, failure_exception=self.failure_exception())
        else:
            self.assertAlmostEqual(expected, actual, places=places, msg=msg)
    
    def assert_isinstance(self, value, klass, msg=None):
        if isinstance(value, klass):
            return
        if msg is None:
            class_name = lambda klass: klass.__name__
            msg = '%s is not an instance of %s' % (class_name(value.__class__), class_name(klass))
        raise AssertionError(msg)
    
    def assert_not_contains(self, expected_value, actual_iterable):
        if expected_value not in actual_iterable:
            return
        raise AssertionError('%s in %s' % (repr(expected_value), repr(list(actual_iterable))))
    
    def assert_contains(self, expected_value, actual_iterable):
        assert_contains(expected_value, actual_iterable, failure_exception=self.failure_exception())
    
    def assert_dict_contains(self, subdict, a_dict):
        assert_dict_contains(subdict, a_dict, failure_exception=self.failure_exception())
    
    def assert_smaller_than(self, smaller, larger):
        assert_smaller_than(smaller, larger, failure_exception=self.failure_exception())
    
    def assert_larger_than(self, larger, smaller):
        assert_larger_than(larger, smaller, failure_exception=self.failure_exception())
    
    def assert_length(self, expected_length, iterable):
        self.assert_equals(expected_length, len(iterable))

    def assert_minimum_length(self, minimum_length, iterable):
        self.assert_larger_than(len(iterable), minimum_length-1)
    
    def assert_is_callable(self, a_callable):
        self.assert_true(callable(a_callable), '%s is not callable' % repr(a_callable))
    
    def assert_is_empty(self, a_value):
        assert_is_empty(a_value, failure_exception=self.failure_exception())

# FIXME: do not raise AssertionErrors explictely
# REFACT: pass a callable to assert_* methods to get more flexibility? (to discuss)
# better error messages for assert False/True
# REFACT: Can we raise exception instances?
