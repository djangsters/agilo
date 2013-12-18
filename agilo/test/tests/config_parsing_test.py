# -*- encoding: utf-8 -*-
#   Copyright 2010 Agile42 GmbH, Berlin (Germany)
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

from agilo.test import AgiloTestCase, TestConfiguration

class IniParsingTest(AgiloTestCase):
    def test_can_parse_ini(self):
        config = TestConfiguration.from_configstring('[db]\nfoo=bar')
        self.assert_not_none(config)
        self.assert_equals(dict(host='localhost', user=None, password=None, 
                                scheme='sqlite'), 
                           config.db())
    
    def test_raise_exception_for_bad_inistring(self):
        self.assert_raises(Exception, TestConfiguration.from_configstring, '\x00\x00\x00\x00\x00')
    
    def test_can_fill_db_setting_from_config(self):
        config = TestConfiguration.from_configstring('[db]\nscheme=postgresql\nhost=localhost\nuser=root\npasword=fnord')
        self.assert_not_none(config)
        db = config.db()
        self.assert_equals('postgresql', db.scheme)
        self.assert_equals('localhost', db.host)
        self.assert_equals('root', db.user)
        self.assert_equals(None, db.password)


