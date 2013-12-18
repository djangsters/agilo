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
#       - Martin Häcker <martin.haecker__at__agile42.com>

from pkg_resources import resource_filename

from agilo.test import AgiloTestCase
from agilo.utils.compatibility_warner import PathNameChecker

class WarnAboutBadUnicodePathsTest(AgiloTestCase):
    
    def test_do_not_warn_for_ascii_pathnames(self):
        checker = PathNameChecker('/foo/bar/baz')
        self.assert_false(checker.is_bad_path())
    
    def test_knows_if_path_contains_non_ascii_characters(self):
        # (AT) this test looks to be wrong, the PathNameChecker tests
        # the convertability of the path to a unicode string and in the test the
        # string is unicode encoded in utf-8 so the test shouldn't fail. If the
        # problem is that the path should be unicode only, than the 
        # PathNameChecker is wrong.
        
        # fs: The test is correct - the os module does not always return unicode
        # strings, sometimes it returns whatever comes from the filesystem - this
        # is a well-known Python-quirk. So here we test that the PathNameChecker
        # can detect bad paths even it gets a byte-string.
        checker = PathNameChecker(u'/föö/bar/baz'.encode('utf-8'))
        self.assert_true(checker.is_bad_path())
    
    def test_path_name_checker_automatically_uses_an_existing_file_to_test_if_none_is_provided(self):
        checker = PathNameChecker()
        expected_path = resource_filename('agilo', 'ticket')
        self.assert_equals(expected_path, checker.path())
    


