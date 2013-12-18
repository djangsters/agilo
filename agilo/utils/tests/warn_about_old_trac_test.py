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
#   Authors:
#       - Felix Schwarz <felix.schwarz__at__agile42.com>

import sys

from agilo.test import AgiloTestCase
from agilo.utils.version_check import VersionChecker


class WarnAboutOldTracTest(AgiloTestCase):
    
    def is_trac_compatible(self, python=None, trac=None):
        checker = VersionChecker(python=python, trac=trac)
        return checker.is_trac_compatible_with_python()
    
    def is_too_old(self, python=None, trac=None):
        return not self.is_trac_compatible(python=python, trac=trac)
    
    def test_can_detect_if_trac_is_compatible_with_python_version(self):
        self.assert_true(self.is_trac_compatible(python='2.5', trac='0.11.2dev-r1234'))
        self.assert_true(self.is_trac_compatible(python='2.6', trac='0.11.4'))
        self.assert_true(self.is_trac_compatible(python='2.6', trac='0.11.6stable-r8519'))
        self.assert_false(self.is_trac_compatible(python='2.6', trac='0.11.2dev-r1234'))
    
    def test_current_platform_uses_only_compatible_versions(self):
        self.assert_true(self.is_trac_compatible())
    
    def test_can_detect_if_trac_is_too_old(self):
        self.assert_true(self.is_too_old(python='2.6', trac='0.11.3'))
        self.assert_false(self.is_too_old(python='2.6', trac='0.11.4'))
    
    def test_can_return_python_version(self):
        def python_version_tuple(python=None):
            return VersionChecker(python=python).python_version_tuple()
        
        self.assert_equals(sys.version_info[:3], python_version_tuple())
        self.assert_equals((2, 4, 6), python_version_tuple('2.4.6'))
        self.assert_equals((2, 5, 0), python_version_tuple('2.5'))



