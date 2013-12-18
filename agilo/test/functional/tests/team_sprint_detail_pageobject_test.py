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

from unittest import TestCase

from trac.util.compat import set

from agilo.test.functional.agilo_tester import TeamSprintDetailTester

fixture = '''<div class="contingents">
    <fieldset>
        <legend>Sprint Contingents</legend>
        <h2>Contingents planned for Sprint: Sprint with Team</h2>
        <form name="contingent_form" method="post" action="/agilo_pro/contingents">
            <div><input type="hidden" value="ef501492eba6bba510911a39" name="__FORM_TOKEN"/></div>
            <input type="hidden" value="Sprint with Team" name="sprint"/>
            <table id="complist" class="listing tickets backlog">
                <thead>
                    <tr>
                        <th>Remove</th>
                        <th>Contingent</th>
                        <th>Amount</th>
                        <th>Actual</th>
                        <th/>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>
                            <input type="checkbox" value="Support" name="sel"/>
                        </td>
                        <td>Support</td>
                        <td class="contingent_number">10.0</td>
                        <td class="contingent_number">
                            9.75
                                +<input type="text" size="2" name="col_add_time_Support"/>
                        </td>
                        <td>
                            <ul id="contingent_progressbar" class="roadmap">
                                <li class="milestone">
                                    <div class="info">
                                        <table class="progress">
                                              <tbody>
                                                  <tr>
                                                    <td style="width: 97%;" class="critical">
                                                      <a title="9.75 of 10.0 s used" href=""/>
                                                    </td>
                                                    <td style="width: 3%;">
                                                      <a title="0.25 of 10.0 s left" href=""/>
                                                    </td>
                                                  </tr>
                                              </tbody>
                                        </table>
                                        <p class="percent">97%</p>
                                    </div>
                                </li>
                            </ul>
                        </td>
                    </tr>
                    <tr>
                        <td>
                            <input type="checkbox" value="Bugs" name="sel"/>
                        </td>
                        <td>Bugs</td>
                        <td class="contingent_number">10.0</td>
                        <td class="contingent_number">
                            8.75
                                +<input type="text" size="2" name="col_add_time_Bugs"/>
                        </td>
                        <td>
                            <ul id="contingent_progressbar" class="roadmap">
                                <li class="milestone">
                                    <div class="info">
                                        <table class="progress">
                                          <tbody><tr>
                                            <td style="width: 87%;" class="warning">
                                              <a title="8.75 of 10.0 s used" href=""/>
                                            </td><td style="width: 13%;">
                                              <a title="1.25 of 10.0 s left" href=""/>
                                            </td>
                                          </tr>
                                        </tbody></table>
                                        <p class="percent">87%</p>
                                    </div>
                                </li>
                            </ul>
                        </td>
                    </tr>
                    <tr class="contingent_totals">
                        <td/>
                        <td>Totals:</td>
                        <td>20.0</td>
                        <td>18.5</td>
                        <td/>
                    </tr>
                </tbody>
            </table>
            <div class="buttons">
                <input type="submit" value="Add to actual time" name="add_time"/>
                <input type="submit" value="Remove selected items" name="remove"/>
            </div>
        </form>
        <form name="add_contingent_form" method="post" action="/agilo_pro/contingents">
            <div><input type="hidden" value="ef501492eba6bba510911a39" name="__FORM_TOKEN"/></div>
            <input type="hidden" value="Sprint with Team" name="sprint"/>
            <h3>Add new contingent</h3>
            <table>
                <tbody>
                    <tr>
                        <td>Name</td>
                        <td><input type="text" value="" name="cont_name"/></td>
                    </tr>
                    <tr>
                        <td>Reserved amount</td>
                        <td class="contingent_number"><input type="text" size="4" value="" name="cont_amount"/></td>
                    </tr>
                </tbody>
            </table>
            <div class="buttons"><input type="submit" value="Add" name="cont_add"/></div>
        </form>
    </fieldset>
</div>
'''

no_delete_fixture = '''
<form name="contingent_form" method="post" action="/contingents"><div><input type="hidden" value="51f9881f5cd774380a126526" name="__FORM_TOKEN"/></div>
    <input type="hidden" value="AddTimeToContingentSprint" name="sprint"/>
    <table id="complist" class="listing tickets backlog">
        <thead>
            <tr>
                <th>Contingent</th>
                <th>Amount</th>
                <th>Actual</th>
                <th/>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>foo</td>
                <td class="contingent_number">6.0</td>
                <td class="contingent_number">
                    2.0
                </td>
                <td>
                    (stripped progress bar)
                </td>
            </tr>
        </tbody>
    </table>
</form>
'''


class ContingentDataCanBeExtractedFromTeamSprintDetailPage(TestCase):
    
    def test_can_extract_contingent_names(self):
        page = TeamSprintDetailTester(None, 'Foo Team', 'Foo Sprint', html=fixture)
        self.assertEqual(set(['Support', 'Bugs']), page.contingent_names())
    
    def test_can_get_contingent_information_by_name(self):
        page = TeamSprintDetailTester(None, 'Foo Team', 'Foo Sprint', html=fixture)
        contingent = page.contingent_for_name('Bugs')
        self.assertEqual('Bugs', contingent.name)
        self.assertEqual('10.0', contingent.amount)
        self.assertEqual('8.75', contingent.used)
    
    def test_return_none_if_no_contingent_with_given_name(self):
        page = TeamSprintDetailTester(None, 'Foo Team', 'Foo Sprint', html=fixture)
        self.assertEqual(None, page.contingent_for_name('Invalid'))
    
    def test_can_extract_contingent_from_readonly_page(self):
        expected_contingent = dict(name='foo', amount='6.0', used='2.0')
        page = TeamSprintDetailTester(None, 'Foo Team', 'Foo Sprint', html=no_delete_fixture)
        self.assertEqual(set(['foo']), page.contingent_names())
        self.assertEqual(expected_contingent, page.contingent_for_name('foo'))
    
    def test_page_knows_if_user_can_delete_contingents(self):
        page = TeamSprintDetailTester(None, 'Foo Team', 'Foo Sprint', html=no_delete_fixture)
        self.assertEqual(False, page.can_delete_contingents())
        
        page = TeamSprintDetailTester(None, 'Foo Team', 'Foo Sprint', html=fixture)
        self.assertEqual(True, page.can_delete_contingents())


