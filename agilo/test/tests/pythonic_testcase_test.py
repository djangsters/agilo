# -*- encoding: utf-8 -*-
#   Copyright  Agile42 GmbH, Berlin (Germany)
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

from unittest import TestCase

from agilo.test.pythonic_testcase import (assert_almost_equals, assert_contains, 
      assert_dict_contains, assert_equals, assert_falsish, assert_is_empty, 
      assert_larger_than, assert_raises, assert_smaller_than, assert_true, 
      PythonicTestCase)


def exception_message(exception):
    return exception.args[0]

class FooError(Exception):
    pass


class AssertRaisesTest(TestCase):
    
    class BarError(Exception):
        pass
    
    class BazError(Exception):
        pass
    
    def foo_failer(self):
        raise FooError
    
    def test_can_detect_raise(self):
        assert_raises(FooError, self.foo_failer)
    
    def test_returns_catched_exception(self):
        exception = assert_raises(FooError, self.foo_failer)
        assert isinstance(exception, FooError)
    
    def test_unexpected_exceptions_are_not_catched(self):
        try:
            assert_raises(self.BarError, self.foo_failer)
        except FooError:
            pass
    
    def test_can_specify_exception_to_raise(self):
        try:
            assert_raises(self.BarError, lambda: None, failure_exception=self.BazError)
        except self.BazError:
            pass
    
    def test_can_specify_custom_message(self):
        try:
            assert_raises(self.BarError, lambda: None, message='fnord')
        except AssertionError, exception:
            assert_equals('fnord', exception_message(exception))
    
    def test_uses_sensible_default_error_message(self):
        try:
            assert_raises(self.BarError, lambda: None)
        except AssertionError, exception:
            assert_equals('BarError not raised', exception_message(exception))



class AssertEqualsTest(TestCase):
    def test_accepts_two_equal_values(self):
        assert_equals(None, None)
        assert_equals({}, {})
        assert_equals(42, 42)
    
    def test_raises_on_different_values(self):
        assert_raises(AssertionError, lambda: assert_equals(1, 2))
        assert_raises(AssertionError, lambda: assert_equals(None, 2))
    
    def test_can_specify_custom_message(self):
        failure = assert_raises(AssertionError, lambda: assert_equals(1, 2, message='fnord'))
        assert_equals('fnord', exception_message(failure))
    
    def test_uses_sensible_default_error_message(self):
        failure = assert_raises(AssertionError, lambda: assert_equals(1, 2))
        assert_equals('1 != 2', exception_message(failure))
    
    # check custom exception



class TestAlmostEquals(TestCase):
    
    # Testing the PythonicTestCase with compatibility API
    
    def testcase(self, failure_exception=AssertionError):
        class MyTestCase(PythonicTestCase):
            def runTest(self):
                pass
        
        instance = MyTestCase()
        instance.failureException = failure_exception
        return instance
    
    def test_assert_almost_equals_works_with_decimal_places(self):
        self.testcase().assert_almost_equals(5, 5, places=0)
        self.testcase().assert_almost_equals(5.02, 5, places=1)
        assert_raises(AssertionError, lambda: self.testcase().assert_almost_equals(5, 5.001, places=3))
    
    def test_assert_almost_equals_fail_if_places_and_max_delta_are_used_together(self):
        assert_raises(TypeError, lambda: self.testcase().assert_almost_equals(5, 5, places=3, max_delta=4))
    
    # --------------------------------------------------------------------------
    # Testing the standalone methods
    
    def test_assert_almost_equals_accepts_max_delta(self):
        assert_almost_equals(5, 5, 0)
        assert_almost_equals(6, 5, max_delta=2)
        assert_almost_equals(5, 5.01, max_delta=0.1)
        assert_raises(AssertionError, lambda: assert_almost_equals(5, 5.1, max_delta=0))
    
    def test_can_specify_custom_message(self):
        failer = lambda: assert_almost_equals(2, 4, max_delta=0, message='fnord')
        failure = assert_raises(AssertionError, failer)
        self.assertEqual('fnord', exception_message(failure))
    
    def test_assert_almost_equals_uses_sensible_error_message(self):
        failer = lambda: assert_almost_equals(2, 4, max_delta=1)
        failure = assert_raises(AssertionError, failer)
        self.assertEqual('2 != 4 with maximal difference of 1', exception_message(failure))
    
    def test_assert_almost_equals_uses_failure_exception(self):
        failer = lambda: assert_almost_equals(2, 4, max_delta=0, failure_exception=TypeError)
        assert_raises(TypeError, failer)


class AssertContainsTest(TestCase):
    def test_can_detect_values_in_iterables(self):
        assert_contains('fnord', ['fnord', 'foo'])
        assert_contains('fnord', ('fnord', 'foo'))
        assert_contains('fnord', set(('fnord', 'foo')))
        assert_contains('fnord', dict(fnord='foo'))
    
    def test_raises_if_item_is_not_in_iterable(self):
        assert_raises(AssertionError, lambda: assert_contains('fnord', []))
        assert_raises(AssertionError, lambda: assert_contains('fnord', ['foo']))
    
    def test_can_specify_custom_message(self):
        failure = assert_raises(AssertionError, lambda: assert_contains(1, [], message='fnord'))
        assert_equals('fnord', exception_message(failure))
    
    def test_uses_sensible_default_error_message(self):
        failure = assert_raises(AssertionError, lambda: assert_contains(1, []))
        assert_equals('1 not in []', exception_message(failure))
    
    def test_can_specify_exception_to_throw(self):
        assert_raises(TypeError, lambda: assert_contains(1, [], failure_exception=TypeError))


class AssertDictContainsTest(TestCase):
    def test_can_detect_contained_dict(self):
        sub_dict = dict(foo='bar')
        super_dict = dict(foo='bar', bar='baz')
        assert_dict_contains(sub_dict, super_dict)
    
    def test_throws_if_dict_is_not_contained(self):
        assertion = lambda: assert_dict_contains(dict(not_in='other dict'), dict())
        assert_raises(AssertionError, assertion)
    
    def test_has_sensible_default_error_message(self):
        assertion = lambda: assert_dict_contains(dict(definitely_missing='from other dict'), dict())
        exception = assert_raises(AssertionError, assertion)
        assert_equals("'definitely_missing':'from other dict' not in {}", exception_message(exception))
    
    def test_has_sensible_default_error_message_when_values_differ(self):
        assertion = lambda: assert_dict_contains(dict(foo='bar'), dict(foo='baz'))
        exception = assert_raises(AssertionError, assertion)
        assert_equals("'foo':'bar' not in {'foo': 'baz'}", exception_message(exception))
    
    def test_can_specify_custom_message(self):
        assertion = lambda: assert_dict_contains(dict(foo='bar'), dict(foo='baz'))
        exception = assert_raises(AssertionError, assertion)
        assert_equals("'foo':'bar' not in {'foo': 'baz'}", exception_message(exception))


class AssertSmallerThanTest(TestCase):
    
    def test_accepts_smaller_values(self):
        assert_smaller_than(1, 4)
        assert_smaller_than(-20, -5)
    
    def test_raises_if_value_is_not_smaller(self):
        assert_raises(AssertionError, lambda: assert_smaller_than(1, 1))
        assert_raises(AssertionError, lambda: assert_smaller_than(4, 1))
        assert_raises(AssertionError, lambda: assert_smaller_than(-4, -5))
    
    def test_has_sensible_default_error_message(self):
        exception = assert_raises(AssertionError, lambda: assert_smaller_than(4, 1))
        assert_equals('4 is not smaller than 1', exception_message(exception))
    
    def test_can_specify_custom_message(self):
        exception = assert_raises(AssertionError, lambda: assert_smaller_than(4, 1, message='fnord'))
        assert_equals('fnord', exception_message(exception))
    
    def test_can_specify_custom_failure_exception(self):
        assert_raises(FooError, lambda: assert_smaller_than(4, 1, failure_exception=FooError))



class AssertTrueTest(TestCase):
    
    def test_accepts_true(self):
        assert_true(True)
    
    def test_raises_if_value_is_not_smaller(self):
        assert_raises(AssertionError, lambda: assert_true(False))
        assert_raises(AssertionError, lambda: assert_true(None))
        assert_raises(AssertionError, lambda: assert_true(4))
    
    def test_has_sensible_default_error_message(self):
        exception = assert_raises(AssertionError, lambda: assert_true('fnord'))
        assert_equals("True != 'fnord'", exception_message(exception))
    
    def test_can_specify_custom_message(self):
        exception = assert_raises(AssertionError, lambda: assert_true(False, message='fnord'))
        assert_equals('fnord', exception_message(exception))
    
    def test_can_specify_custom_failure_exception(self):
        assert_raises(FooError, lambda: assert_true(False, failure_exception=FooError))



class AssertFalsishTest(TestCase):
    
    def test_accepts_falsish_values(self):
        assert_falsish(False)
        assert_falsish(None)
        assert_falsish('')
    
    def test_raises_if_value_is_trueish(self):
        assert_raises(AssertionError, lambda: assert_falsish(True))
        assert_raises(AssertionError, lambda: assert_falsish('foo'))
        assert_raises(AssertionError, lambda: assert_falsish(4))
    
    def test_can_specify_custom_message(self):
        exception = assert_raises(AssertionError, lambda: assert_falsish(True, message='fnord'))
        assert_equals('fnord', exception_message(exception))
    
    def test_can_specify_custom_failure_exception(self):
        assert_raises(FooError, lambda: assert_falsish(True, failure_exception=FooError))



class AssertLargerThanTest(TestCase):
    
    def test_accepts_smaller_values(self):
        assert_larger_than(4, 1)
        assert_larger_than(-5, -20)
    
    def test_raises_if_value_is_not_smaller(self):
        assert_raises(AssertionError, lambda: assert_larger_than(1, 1))
        assert_raises(AssertionError, lambda: assert_larger_than(1, 4))
        assert_raises(AssertionError, lambda: assert_larger_than(-5, -4))
    
    def test_has_sensible_default_error_message(self):
        exception = assert_raises(AssertionError, lambda: assert_larger_than(1, 4))
        assert_equals('1 is not larger than 4', exception_message(exception))
    
    def test_can_specify_custom_message(self):
        exception = assert_raises(AssertionError, lambda: assert_larger_than(1, 4, message='fnord'))
        assert_equals('fnord', exception_message(exception))
    
    def test_can_specify_custom_failure_exception(self):
        assert_raises(FooError, lambda: assert_larger_than(1, 4, failure_exception=FooError))

class AssertIsEmptyTest(TestCase):
    
    def test_accepts_empty_values(self):
        assert_is_empty('')
        assert_is_empty(list())
        assert_is_empty(dict())
        assert_is_empty(tuple())
        assert_is_empty(set())
    
    def test_rejects_non_empty_values(self):
        assert_raises(AssertionError, lambda: assert_is_empty('fnord'))
        assert_raises(AssertionError, lambda: assert_is_empty(['fnord']))
        assert_raises(AssertionError, lambda: assert_is_empty({'fnord':'fnord'}))
        assert_raises(AssertionError, lambda: assert_is_empty(('fnord',)))
        assert_raises(AssertionError, lambda: assert_is_empty(set(['fnord'])))
    
    def test_has_sensible_default_error_message(self):
        exception = assert_raises(AssertionError, lambda: assert_is_empty((1,)))
        assert_equals('(1,) is not empty', exception_message(exception))
    
    def test_can_specify_custom_message(self):
        exception = assert_raises(AssertionError, lambda: assert_is_empty((1,), message='fnord'))
        assert_equals('fnord', exception_message(exception))
    
    def test_can_specify_custom_failure_exception(self):
        assert_raises(FooError, lambda: assert_is_empty((1,), failure_exception=FooError))
    
