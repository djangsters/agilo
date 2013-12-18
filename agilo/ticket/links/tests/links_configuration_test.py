# -*- encoding: utf-8 -*-
#   Copyright 2011 Agile42 GmbH, Berlin (Germany)
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
from agilo.test import AgiloTestCase
from agilo.ticket.links.model import LinksConfiguration
from agilo.utils.config import AgiloConfig
from agilo.ticket.api import AgiloTicketSystem
from trac.ticket.model import Type as TicketType

class LinksConfigurationCachingTest(AgiloTestCase):
    def setUp(self):
        self.super()
        self.links_configuration = LinksConfiguration(self.env)
    
    def test_initializes_at_init(self):
        self.assert_true(self.links_configuration.is_initialized())

    def test_handles_types_with_dashes(self):
        from_type = 'with-dashes'
        to_type = 'bug'
        custom_type = TicketType(self.env)
        custom_type.name = from_type
        custom_type.insert()

        config = AgiloConfig(self.env)
        config.change_option(from_type, "", section=AgiloConfig.AGILO_TYPES)
        config.reload()
        self.assert_true(from_type in config.get_available_types())

        section = config.get_section(AgiloConfig.AGILO_LINKS)
        allowed_links = section.get_list('allow')
        allowed_links.append('%s-%s' % (from_type, to_type))
        section.change_option('allow', ', '.join(allowed_links), save=True)
        self.links_configuration = LinksConfiguration(self.env)
        self.assert_equals(self.links_configuration.get_alloweds(from_type)[0].dest_type, to_type)

    def _requirement_links(self):
        return self.links_configuration.get_allowed_destination_types('requirement')
    
    def test_invalidating_the_cache_reloads_allowed_links_configuration(self):
        AgiloConfig(self.env).change_option('allow', 'requirement-task', section='agilo-links', save=True)
        self.links_configuration.reinitialize()
        self.assert_not_contains('story', self._requirement_links())
        self.assert_contains('task', self._requirement_links())

    def _bug_calculated_properties(self):
        return AgiloTicketSystem(self.env).get_agilo_properties('bug')[0].keys()

    def test_invalidating_the_cache_reloads_calculated_properties(self):
        self.assert_contains('total_remaining_time', self._bug_calculated_properties())
        AgiloConfig(self.env).change_option('bug.calculate', '', section='agilo-links', save=True)
        self.links_configuration.reinitialize()
        self.assert_not_contains('total_remaining_time', self._bug_calculated_properties())
