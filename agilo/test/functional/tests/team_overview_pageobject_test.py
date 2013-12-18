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
#   Author: 
#       - Felix Schwarz <felix.schwarz__at__agile42.com>


from agilo.test import AgiloTestCase
from agilo.test.functional.agilo_tester import TeamOverviewPageTester
from agilo.utils import Key

fixture = '''<table class="tickets listing metrics backlog" id="metrics">
    <thead>
        <tr>
            <th>Sprint</th>
            <th>Start date</th>
            <th>End date</th>
            <th>Velocity</th><th>Capacity</th><th>Commitment</th><th>Estimated Velocity</th><th>Rt Usp Ratio</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td class="sprint"><a href="/agilo/team/A-Team/First_Sprint">First_Sprint</a></td>
            <td>07.10.2008 00:00:00</td>
            <td>15.10.2008 00:00:00</td>
            <td>n.a.</td><td>n.a.</td><td>n.a.</td><td>n.a.</td><td>n.a.</td>
        </tr><tr>
            <td class="sprint"><a href="/agilo/team/A-Team/Second_Sprint">Second_Sprint</a></td>
            <td>17.10.2008 09:00:00</td>
            <td>03.11.2008 18:00:00</td>
            <td>n.a.</td><td>240.0h</td><td>4.0h</td><td>26.0</td><td>n.a.</td>
        </tr><tr>
            <td class="sprint"><a href="/agilo/team/A-Team/Third_Sprint">Third_Sprint</a></td>
            <td>24.11.2008 09:00:00</td>
            <td>05.12.2008 18:00:00</td>
            <td>27.0</td><td>143.0h</td><td>123.5h</td><td>51.0</td><td>2.79</td>
        </tr>
    </tbody>
</table>
'''

fixture2 = '''
<p/>
<table id="metrics" class="tickets listing metrics backlog">
    <thead>
        <tr>
            <th>Sprint</th>
            <th>Start date</th>
            <th>End date</th>
            <th>Capacity</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td class="sprint"><a href="/team/A-Team/First Sprint">First Sprint</a></td>
            <td>21.08.2009 00:00:00</td>
            <td>02.09.2009 20:00:00</td>
            <td>0.0h</td>
        </tr>
    </tbody>
</table>
<p/>
'''

class TestMetricsValuesCanBeExtractedFromTeamPage(AgiloTestCase):
    def test_can_extract_stored_value_for_sprint(self):
        tester = TeamOverviewPageTester(None, 'Foo', html=fixture)
        self.assert_equals('4.0h', tester.value_for_sprint(Key.COMMITMENT, 'Second_Sprint'))
        self.assert_equals('51.0', tester.value_for_sprint(Key.ESTIMATED_VELOCITY, 'Third_Sprint'))
    
    def test_raise_exception_if_sprint_is_unknown(self):
        tester = TeamOverviewPageTester(None, 'Foo', html=fixture)
        self.assert_raises(Exception, tester.value_for_sprint, Key.COMMITMENT, 'Does Not Exist')
    
    def test_raise_exception_if_metric_name_is_unknown(self):
        tester = TeamOverviewPageTester(None, 'Foo', html=fixture)
        self.assert_raises(Exception, tester.value_for_sprint, 'Does Not Exist', 'Second_Sprint')
    
    def test_can_tolerate_table_id_not_at_end_of_tag(self):
        tester = TeamOverviewPageTester(None, 'Foo', html=fixture2)
        self.assert_equals('0.0h', tester.value_for_sprint(Key.CAPACITY, 'First Sprint'))


