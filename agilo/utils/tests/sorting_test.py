#   Copyright 2010 Agile42 GmbH, Berlin (Germany)
#   Copyright 2007 Andrea Tomasini <andrea.tomasini_at_agile42.com>
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

from agilo.test.testcase import AgiloTestCase

from agilo.api.controller import ValueObject
from agilo.utils.compat import exception_to_unicode
from agilo.utils.sorting import SortOrder, Attribute, By

def v(value):
    return ValueObject(foo=value)

class SortingTest(AgiloTestCase):

    def test_standard_sort_will_sort_none_at_start(self):
        actual = [1, 2, 4, None, 5, 3, None, None]
        actual.sort()
        self.assert_equals([None, None, None, 1, 2, 3, 4, 5], actual)

    def test_by_defaults_to_sorting_none_at_end(self):
        expected = [v(1), v(2), v(3), v(None), v(None)]
        actual = [v(1), v(2), v(None), v(None), v(3)]
        actual.sort(By(Attribute('foo'), SortOrder.ASCENDING))
        self.assert_equals(expected, actual)

    def test_can_sort_ascending(self):
        self.assert_equals([v(1), v(2), v(3)], sorted([v(3),v(2),v(1)], By(Attribute('foo'), SortOrder.ASCENDING)))

    def test_can_sort_descending(self):
        self.assert_equals([v(3), v(2), v(1)], sorted([v(1),v(2),v(3)], By(Attribute('foo'), SortOrder.DESCENDING)))

    def test_raises_on_sorting_non_comparable_elements(self):
        exception = self.assert_raises(ValueError, sorted, [v(1), v('foo')], By(Attribute('foo')))
        self.assert_true('Elements are not comparable' in exception_to_unicode(exception))