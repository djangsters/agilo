# -*- encoding: utf-8 -*-
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
#   Author: 
#       - Felix Schwarz <felix.schwarz__at__agile42.com>


import os

from agilo.test import AgiloTestCase
from agilo.test.testfinder import TestFinder, get_project_path


class TestfinderTest(AgiloTestCase):
    
    def _get_package_name_from_pathname(self, path):
        finder = TestFinder(get_project_path(), False)
        return finder._get_package_name_from_pathname(path)
    
    def test_package_from_directory(self):
        path = os.path.join(get_project_path(), os.path.join('agilo', 'scrum'))
        package = self._get_package_name_from_pathname(path)
        self.assert_equals('agilo.scrum', package)
    
    def test_package_from_py_filename(self):
        c = [get_project_path(), os.path.join('agilo', 'scrum')]
        path = os.path.join(*(c + ['burndown.py']))
        package = self._get_package_name_from_pathname(path)
        self.assert_equals('agilo.scrum.burndown', package)
    
    def test_package_from_pyc_filename(self):
        c = [get_project_path(), os.path.join('agilo', 'scrum')]
        path = os.path.join(*(c + ['burndown.pyc']))
        package = self._get_package_name_from_pathname(path)
        self.assert_equals('agilo.scrum.burndown', package)
    
    def test_package_from_pyo_filename(self):
        c = [get_project_path(), os.path.join('agilo', 'scrum')]
        path = os.path.join(*(c + ['burndown.pyo']))
        package = self._get_package_name_from_pathname(path)
        self.assert_equals('agilo.scrum.burndown', package)
    
    def test_package_not_within_agilo_subtree(self):
        c = [get_project_path(), 'functional_tests']
        path = os.path.join(*(c + ['sprint_test.py']))
        package = self._get_package_name_from_pathname(path)
        self.assert_equals('functional_tests.sprint_test', package)
    
    def test_select_all_classes_when_running_with_functional_tests(self):
        class Foo(object):
            pass
        finder = TestFinder(get_project_path(), True)
        self.assert_true(finder._want_TestCase_class(Foo))
    
    def test_calls_nosetest_exlude_filter(self):
        class Foo(object):
            is_abstract_test = True
        finder = TestFinder(get_project_path(), False)
        self.assert_false(finder._want_TestCase_class(Foo))
    

if __name__ == '__main__':
    from agilo.test.testfinder import run_unit_tests
    run_unit_tests(__file__)
