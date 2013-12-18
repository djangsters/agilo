# encoding: utf8
#   Copyright 2009 agile42 GmbH All rights reserved
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
#        - Felix Schwarz <felix.schwarz__at__agile42.com>
#        - Martin Häcker <martin.haecker__at__agile42.com>

from agilo.test import AgiloTestCase


class FilteredExtensionPointsAcrossModulesTest(AgiloTestCase):
    def test_can_import_interfaces_from_other_modules(self):
        from agilo.api.tests.automatic_request_filter_creation_test import IFirstTestViewRequestFilter


