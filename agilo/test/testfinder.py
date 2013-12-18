# -*- encoding: utf-8 -*-
#   Copyright 2008. 2009 Agile42 GmbH, Berlin (Germany)
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
#       - Roberto Bettazzoni <roberto.bettazzoni__at__agile42.com>
#       - Felix Schwarz <felix.schwarz__at__agile42.com>

# This package is not located below /tests because otherwise nosetests would 
# pick up all the methods defined here as if they were tests too.

import glob
import inspect
import os
import re
import types
import unittest

import agilo.utils.filterwarnings

__all__ = ['build_functional_test_suite', 'build_test_suite', 'run_all_tests', 
           'run_unit_tests', 'TestFinder']

def my_import(name):
    """ see Python Library References cap. 2.1 """ 
    mod = __import__(name)
    components = name.split('.')
    for comp in components[1:]:
        mod = getattr(mod, comp)
    return mod

def get_project_path():
    """Returns the path name of the agilo root directory. This works because 
    the relative location of this file is hard coded here."""
    this_dir = os.path.dirname(__file__)
    path_offset = os.path.join('..', '..')
    path_prefix = os.path.realpath(os.path.join(this_dir, path_offset))
    return path_prefix


class TestFinder(object):
    def __init__(self, project_path, with_functional_tests=False):
        self._project_path = project_path
        self._with_functional_tests = with_functional_tests
    
    def find_tests(self, filename=None, root_dir=None):
        """Return the tests in the project. If filename was given, return only
        the tests in the specified file. If root_dir was given, just all tests 
        defined in files in the given directory. You must not use both 
        parameters at the same time.
        If with_functional_tests is True the result includes also the 
        functional tests."""
        # The user must not set both parameters at the same time
        assert None in [filename, root_dir]
        
        testcases = []
        if filename != None:
            path = os.path.abspath(filename)
            module = self._get_package_name_from_pathname(path)
            testcases = self._get_TestCase_classes(module)
        else:
            if (root_dir is not None):
                path = os.path.abspath(root_dir)
                if os.path.isfile(path):
                    path = os.path.dirname(path)
                root_dir = path
            test_directories = self._find_all_test_directories(root_dir)
            for dirname in test_directories:
                classes = self._get_TestCase_classes_in_package(dirname)
                testcases.extend(classes)
        tests = []
        for testcase in testcases:
            tests.extend(self._get_test_instances_from_testcase(testcase))
        return tests
    
    def _get_package_name_from_pathname(self, dirname):
        """Returns the package name given a directory name (or a filename that ends
        with .py, .pyc, .pyo)."""
        relative_path = dirname[len(self._project_path):]
        if relative_path.startswith(os.sep):
            relative_path = relative_path[1:]
        relative_path = re.sub('\.py(?:c|o)?$', '', relative_path)
        package_name = relative_path.replace(os.sep, '.')
        assert package_name != ''
        return package_name
    
    def _is_testcase_from_this_file(self, symbol, module):
        """Return True if the symbol is a test case class that was defined in 
        the specified module."""
        is_testcase = isinstance(symbol, (type, types.ClassType)) and \
                        issubclass(symbol, unittest.TestCase)
        if is_testcase:
            was_defined_in_the_module = (module.__file__ == inspect.getfile(symbol))
            return was_defined_in_the_module
        return False
    
    def _get_TestCase_classes(self, module = '__main__'):
        if not isinstance(module, types.ModuleType):
            module = my_import(module)
        obj_list = [getattr(module, name) for name in dir(module)]
        testcase_classes = []
        for item in obj_list:
            if self._is_testcase_from_this_file(item, module):
                if self._want_TestCase_class(item):
                    testcase_classes.append(item)
        return testcase_classes
    
    def _want_TestCase_class(self, cls):
        if self._is_excluded_by_nose(cls):
            return False
        if not hasattr(cls, 'runTest'):
            return True
        if self._with_functional_tests:
            return True
        return False
    
    def _is_excluded_by_nose(self, cls):
        # Here with gusto, so create_demo_data.py can import the testfinder from the
        # binary egg.
        from agilo.test.nose_testselector import NoseExcludeUnittestRunnerFunctions
        nose_exlude_filter = NoseExcludeUnittestRunnerFunctions()
        return False == nose_exlude_filter.wantClass(cls)
    
    def _get_testmodule_names_in_directory(self, dirname):
        """Return the names of all test modules in the given directory."""
        test_path_names = glob.glob(os.path.join(dirname, "*_test.py"))
        test_module_names = []
        for path_name in test_path_names:
            file_name = os.path.basename(path_name)
            module_name = os.path.splitext(file_name)[0]
            test_module_names.append(module_name)
        return test_module_names
    
    def _get_TestCase_classes_in_package(self, test_directory):
        """Return the test case classes contained in files in the given 
        directory."""
        testcase_classes = []
        package_name = self._get_package_name_from_pathname(test_directory)
        for module_name in self._get_testmodule_names_in_directory(test_directory):
            qualified_name = '%s.%s' % (package_name, module_name)
            testcases = self._get_TestCase_classes(qualified_name)
            testcase_classes.extend(testcases)
        return testcase_classes
    
    def _get_test_instances_from_testcase(self, testcase):
        testloader = unittest.TestLoader()
        dummy_suite = testloader.loadTestsFromTestCase(testcase)
        tests = []
        for test_instance in dummy_suite._tests:
            if hasattr(test_instance, 'should_be_skipped'):
                if test_instance.should_be_skipped():
                    continue
            tests.append(test_instance)
        return tests
    
    def _get_dir_exclusion_regex(self):
        exclude_patterns = ['.hg', '.svn', 'build']
        escaped_patterns = map(re.escape, exclude_patterns)
        exclusion_pattern = '|'.join(escaped_patterns)
        project_path = re.escape(self._project_path)
        sep = re.escape(os.sep)
        pattern = '%s.*%s(?:%s)%s' % (project_path, sep, exclusion_pattern, sep)
        regex = re.compile(pattern)
        return regex
    
    def _find_all_test_directories(self, root_dir=None):
        if root_dir is None:
            root_dir = self._project_path
        if root_dir.endswith('tests'):
            return [root_dir]
        
        test_directories = []
        regex = self._get_dir_exclusion_regex()
        for root, dirs, files in os.walk(root_dir):
            for name in dirs:
                if (not regex.search(root)) and ((name == 'tests') or \
                    (name == 'functional_tests' and self._with_functional_tests)):
                    test_directories.append(os.path.join(root, name))
        return test_directories
    

# -----------------------------------------------------------------------------

# Also these methods are defined here so that nosetests won't pick them up.
def build_test_suite(filename=None, root_dir=None, with_functional_tests=False,
                     project_path=None):
    """Return a test suite """
    # imported here so importing anything from the testfinder does not import the
    # FunctionalTestSuite and it's dependencies. Otherwise create_demo_data doesn't work
    from agilo.test.functional import FunctionalTestSuite
    if project_path is None:
        project_path = get_project_path()
    finder = TestFinder(project_path, with_functional_tests)
    testcases = finder.find_tests(filename, root_dir)
    if with_functional_tests:
        testsuite = FunctionalTestSuite()
    else:
        testsuite = unittest.TestSuite()
    assert len(testsuite._tests) == 0, testsuite._tests
    testsuite.addTests(testcases)
    return testsuite

def build_functional_test_suite():
    return build_test_suite(with_functional_tests=True)

def run_all_tests(filename=None, root_dir=None, with_functional_tests=True,
                  project_path=None):
    """Run all test cases (including functional tests). If filename was given,
    only the tests in the given file are run."""
    # The user must not set both parameters at the same time
    testsuite = build_test_suite(filename=filename, root_dir=root_dir, 
                                 with_functional_tests=with_functional_tests,
                                 project_path=project_path)
    try:
        unittest.TextTestRunner().run(testsuite)
    except KeyboardInterrupt:
        pass

def run_unit_tests(filename=None, root_dir=None, project_path=None):
    """Run all test cases in the file's directory with test TextTestRunner."""
    run_all_tests(filename=filename, root_dir=root_dir, 
                  with_functional_tests=False, project_path=project_path)

