# -*- encoding: utf-8 -*-
#   Copyright 2008-2009 Agile42 GmbH, Berlin (Germany)
#   Copyright 2007 Andrea Tomasini <andrea.tomasini_at_agile42.com>
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
#       - Jonas von Poser <jonas.vonposer__at__agile42.com>
#       - Felix Schwarz <felix.schwarz__at__agile42.com>

from trac.tests.functional import tc

from agilo.utils import Type, Key
from agilo.utils.config import AgiloConfig
from agilo.test import Usernames
from agilo.test.functional import AgiloFunctionalTestCase


class TestAdminCustomFields(AgiloFunctionalTestCase):
    
    def _assert_field_has_number(self, fieldname, number):
        tc.find(('<select name="order_%s">(</*option>|\s|\d)*' % fieldname) + \
                '<option selected="selected">\s*' + str(number), 'm')
    
    def _get_number_of_custom_fields(self):
        env = self._testenv.get_trac_environment()
        config = AgiloConfig(env).get_section(AgiloConfig.TICKET_CUSTOM)
        last = len(config.get_options_matching_re('^[^.]+$')) - 1
        return last
    
    def runTest(self):
        self._tester.login_as(Usernames.admin)
        
        self._tester.delete_custom_field('remaining_time', 'Remaining Time')
        
        # add the field again
        tc.formvalue('addcf', 'name', 'remaining_time')
        # don't put a value in label field, test empty value
        tc.submit('add')
        tc.code(200)
        tc.url(self._tester.url + '/admin/agilo/fields')
        
        # redirects to list page, now link with default label
        # should be found again
        tc.find('<td><a href="/admin/agilo/fields/remaining_time">remaining_time')
        tc.find('<td>Remaining_time</td>', 'm')
        last = self._get_number_of_custom_fields()
        self._assert_field_has_number('remaining_time', last)
        
        self._tester.modify_custom_field('remaining_time', label='Linking Source')
        # see if the new label is found        
        tc.find('<td>Linking Source</td>')
        
        # add another field
        tc.formvalue('addcf', 'name', 'testfield')
        tc.formvalue('addcf', 'label', 'Test Field')
        tc.submit('add')
        # see if the new label is found        
        tc.find('<td><a href="/admin/agilo/fields/testfield">testfield')
        tc.find('<td>Test Field</td>')
        tc.code(200)
        # set order of fields
        last = self._get_number_of_custom_fields()
        # There are 7 standard fields, so these new ones should be 7 and 8.
        ord1 = str(last - 1)
        ord2 = str(last)
        # check the actual position of the two custom fields
        self._assert_field_has_number('remaining_time', ord1)
        self._assert_field_has_number('testfield', ord2)
        
        # Change the order
        tc.formvalue('customfields', 'order_testfield', ord1)
        tc.formvalue('customfields', 'order_remaining_time', ord2)
        tc.submit('apply')
        
        # has the order been changed? This regex finds the order select field
        # for testfield and the selected option -> should be 8
        tc.find('<select name="order_remaining_time">(</*option>|\s|\d)*' \
                '<option selected="selected">\s*' + ord2, 'm')
        tc.find('<select name="order_testfield">(</*option>|\s|\d)*' \
                '<option selected="selected">\s*' + ord1, 'm')


class TestCanDeleteDefaultValueOfCustomField(AgiloFunctionalTestCase):
    
    def runTest(self):
        self._tester.login_as(Usernames.admin)
        fieldname = 'remaining_time'
        self._tester.modify_custom_field(fieldname, value='5')
        self._tester.modify_custom_field(fieldname, value='')
        
        url = '%s/admin/agilo/fields/%s' % (self._tester.url, fieldname)
        tc.go(url)
        tc.find('<input type="text" name="value" value=""')
        
        env = self._testenv.get_trac_environment()
        config = AgiloConfig(env).get_section(AgiloConfig.TICKET_CUSTOM)
        self.assertEqual(None, config.get('remaining_time.value'))


class TestAdminErrorHandlingWhenAddingCustomFields(AgiloFunctionalTestCase):
    
    def runTest(self):
        self._tester.login_as(Usernames.admin)
        page_url = self._tester.url + '/admin/agilo/fields'
        tc.go(page_url)
        tc.formvalue('addcf', 'name', 'ä')
        tc.submit('add')
        assert 'Only alphanumeric characters allowed for custom field' in tc.show()


class TestDisplayAdminCalculatedProperties(AgiloFunctionalTestCase):
    
    def runTest(self):
        self._tester.login_as(Usernames.admin)
        page_url = self._tester.url + '/admin/agilo/types/requirement'
        tc.go(page_url)
        
        html = tc.show()
        assert "sum:get_outgoing.rd_points|type=story|story_priority=Mandatory" in html


class TestIgnoreBrokenDefinitionsForCalculatedPropertiesInAdmin(AgiloFunctionalTestCase):
    
    def runTest(self):
        env = self._testenv.get_trac_environment()
        config = AgiloConfig(env).get_section(AgiloConfig.AGILO_LINKS)
        option_name = '%s.calculate' % Type.REQUIREMENT
        configured_properties = config.get_list(option_name)
        broken_definition = 'sum:get_outgoing.blubber'
        configured_properties.append(broken_definition)
        config.change_option(option_name, ', '.join(configured_properties))
        config.save()
        self._tester.login_as(Usernames.admin)
        page_url = self._tester.url + '/admin/agilo/types/%s' % Type.REQUIREMENT
        tc.go(page_url)
        tc.code(200)
        
        html = tc.show()
        assert "sum:get_outgoing.rd_points|type=story|story_priority=Mandatory" in html
        assert 'blubber' not in html


class TestSaveAdminCalculatedProperties(AgiloFunctionalTestCase):
    
    def runTest(self):
        self._tester.login_as(Usernames.admin)
        page_url = self._tester.url + '/admin/agilo/types/task'
        tc.go(page_url)
        assert ('sum:remaining_time;actual_time' not in tc.show())
        
        tc.formvalue('modcomp', 'result', 'summed_time')
        tc.formvalue('modcomp', 'function', 'sum:remaining_time=actual_time')
        tc.submit('save')
        
        assert "Wrong format for calculated property 'summed_time'" in tc.show()
        
        tc.go(page_url)
        # Add some spaces around the names to test stripping.
        tc.formvalue('modcomp', 'result', ' summed_time ')
        tc.formvalue('modcomp', 'function', ' sum:remaining_time;actual_time ')
        tc.submit('save')
        tc.code(200)
        
        tc.go(page_url)
        assert 'sum:remaining_time;actual_time' in tc.show()


if __name__ == '__main__':
    from agilo.test.testfinder import run_all_tests
    run_all_tests(__file__)

