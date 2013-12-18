# -*- coding: utf-8 -*-
#   Copyright 2009 Agile42 GmbH
#   Copyright 2011 Agilo Software GmbH All rights reserved
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
# 
# Authors:
#     - Felix Schwarz <felix.schwarz__at__agile42.com>

from agilo.core import Field, PersistentObject, PersistentObjectManager
from agilo.test import AgiloTestCase
from agilo.api import ICommand
from agilo.api.validator import StringValidator


class MyCommandPO(PersistentObject):
    class Meta(object):
        name = Field(primary_key=True)

class MyCommand(ICommand):
    parameters = {'name': StringValidator}


class TestCommand(AgiloTestCase):
    
    def test_return_items_in_lists_as_dict(self):
        PersistentObjectManager(self.env).create_table(MyCommandPO)
        input = [MyCommandPO(self.env, name='foo')]
        self.assert_equals([{'name': 'foo', 'exists': False}], 
                           MyCommand(self.env).return_as_value_object(input))

