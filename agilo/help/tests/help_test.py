# -*- encoding: utf-8 -*-
#   Copyright 2008 Agile42 GmbH, Berlin (Germany)
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

from trac.mimeview import Context
from trac.wiki import Formatter

from agilo.help import AgiloLinks
from agilo.test import AgiloTestCase



class TestAgiloHelpSystem(AgiloTestCase):
    
    def setUp(self):
        self.super()
        req = self.teh.mock_request(path_info='/prefix/')
        self.context = Context.from_request(req)
    
    def _get_link_function(self):
        help_prefix = 'agilo-help'
        
        helplinks = AgiloLinks(self.env)
        resolvers = [r for r in helplinks.get_link_resolvers()]
        link_resolver = resolvers[0]
        self.assert_equals(help_prefix, link_resolver[0])
        link_fn = link_resolver[1]
        formatter = Formatter(self.env, self.context)
        return lambda target, label: link_fn(formatter, help_prefix, target, label)
    
    def get_html(self, element):
        return str(element.generate())
    
    def test_link_generation_to_existing_pages(self):
        link_fn = self._get_link_function()
        link_element = link_fn('index', 'Start Page')
        self.assert_equals('<a href="/prefix/agilo-help/index">Start Page</a>', 
                         self.get_html(link_element))
    
    def test_relative_link_must_not_encode_pound_character(self):
        link_fn = self._get_link_function()
        link_element = link_fn('index#Foo', 'Start Page')
        self.assert_equals('<a href="/prefix/agilo-help/index#Foo">Start Page</a>', 
                         self.get_html(link_element))

