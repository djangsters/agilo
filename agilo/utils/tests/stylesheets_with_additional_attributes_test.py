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
#       - Martin Häcker <martin.haecker_at_agile42.com>

from agilo.test import AgiloTestCase, TestEnvHelper
from agilo.utils.compat import add_stylesheet


class StylesheetsWithAdditionalAttributesTest(AgiloTestCase):
    def setUp(self):
        self.super()
        self.req = self.teh.mock_request()
        self.assert_false('links' in self.req.chrome)
    
    def _first_stylesheet(self):
        self.assert_equals(1, len(self.req.chrome['links']))
        return self.req.chrome['links']['stylesheet'][0]
    
    def test_can_specify_media_attribute_for_stylesheets(self):
        add_stylesheet(self.req, 'foo', media='print')
        stylesheet = self._first_stylesheet()
        self.assert_equals('print', stylesheet['media'])

