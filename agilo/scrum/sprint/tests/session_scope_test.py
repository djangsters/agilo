# -*- encoding: utf-8 -*-
#   Copyright 2010 Agile42 GmbH, Berlin (Germany)
#   Copyright 2011 Agilo Software GmbH All rights reserved
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

from agilo.test import AgiloTestCase
from agilo.scrum.sprint.util import SessionScope

class SessionScopeTest(AgiloTestCase):
    
    def setUp(self):
        self.super()
        req = self.teh.mock_request()
        self.session_scope = SessionScope(req)
    
    def test_can_set_sprint(self):
        self.assert_none(self.session_scope.sprint_name())
        self.session_scope.set_sprint_name('fnord')
        self.assert_equals('fnord', self.session_scope.sprint_name())

