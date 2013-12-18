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

from trac.test import Mock
from nose.config import Config

from agilo.test.testcase import AgiloTestCase
from agilo.test.nose_testselector import NoseClassAttributeSelector,\
    NoseExcludeUnittestRunnerFunctions


class NoseCanSelectTestsOnClassattr(AgiloTestCase):
    
    def _plugin(self):
        plugin = NoseClassAttributeSelector()
        fake_options = Mock(classattr='testtype=unittest', eval_attr=None)
        plugin.configure(fake_options, Config())
        self.assert_true(plugin.enabled)
        return plugin
    
    def test_ignore_classes_without_attribute(self):
        class Foo(object):
            pass
        self.assert_false(self._plugin().wantClass(Foo))
    
    def test_select_classes_with_correct_attribute_value(self):
        class Foo(object):
            testtype = 'unittest'
        self.assert_none(self._plugin().wantClass(Foo))
    
    def test_select_subclasses_with_correct_attribute_value(self):
        class Foo(object):
            testtype = 'unittest'
        class Bar(Foo):
            pass
        self.assert_none(self._plugin().wantClass(Bar))


class NoseCanExcludeTests(AgiloTestCase):
    
    def _plugin(self):
        plugin = NoseExcludeUnittestRunnerFunctions()
        plugin.configure(Mock(only_real_tests=True), Config())
        self.assert_true(plugin.enabled)
        return plugin
    
    def test_ignore_abstract_test_classes(self):
        class Foo(object):
            is_abstract_test = True
        self.assert_false(self._plugin().wantClass(Foo))
    
    def test_does_exclude_subclasses_of_abstract_testcase(self):
        class Abstract(object):
            is_abstract_test = True
        class Concrete(Abstract):
            pass
        self.assert_none(self._plugin().wantClass(Concrete))
    
    def test_does_care_if_no_attribute_is_set(self):
        class Concrete(object):
            pass
        self.assert_none(self._plugin().wantClass(Concrete))
    

