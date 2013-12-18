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


from trac.util.compat import set

from agilo.test import AgiloTestCase
from agilo.test.functional.agilo_tester import TicketViewPageTester
from agilo.utils import Key

fixture = '''<div id="content" class="ticket">
    <ul id="tabbed_pane">
        <li id="view" class="selected"><a href="/ticket/5">View</a></li>
        <li id="edit">
            <a href="/ticket/5?pane=edit">Edit</a>
        </li>
    </ul>
    <h1>Task #5 <span class="status">(new)</span></h1>
    <div id="ticket">
        <div class="date">
            <p>Opened <a class="timeline" href="/timeline?from=2009-09-24T11%3A58%3A22%2B0200&amp;precision=second" title="2009-09-24T11:58:22+0200 in Timeline">2 seconds</a> ago</p>
        </div>
        <!-- use a placeholder if it's a new ticket -->
        <h2 class="summary searchable">Some forgotten task</h2>
        <!-- Trac 1.0 uses spans here -->
        <span class="summary">Some forgotten task</span>
        <table class="properties">
            <tr>
                <th id="h_reporter">Reported by:</th>
                <td headers="h_reporter" class="searchable">a_reporter</td>
                <th id="h_owner">Owned by:</th> 
                <td headers="h_owner"> 
                  <a href="/tracenv/query?status=%21closed&amp;owner=an_owner">an_owner</a> 
                </td> 
            </tr>
            <tr>
                <th id="h_remaining_time">
                    Remaining Time:
                </th>
                <td headers="h_remaining_time">
                    7.0h
                </td>
                <th id="h_sprint">
                    Sprint:
                </th>
                <td headers="h_sprint">
                    In the middle of nowhere
                </td>
            </tr>
            <tr>
                <th id="h_drp_resources">
                    Resources:
                </th>
                <td headers="h_drp_resources">
                    n.a.
                </td>
                <th>
                </th>
                <td>
                </td>
            </tr>
        </table>
        
        <h3 id="comment:description">
            Description
        </h3>
        
        <form id="addreply" method="get" action="#comment">
            <div class="inlinebuttons">
                <input type="hidden" name="replyto" value="description" />
                <input type="submit" name="reply" value="Reply" title="Reply, quoting this description" />
            </div>
        </form>
        <div class="searchable">
            <p>
                A random description<br />
            </p>
        </div>
        
        <div class="description">
            <h3>References</h3>
            <table class="links">
                <tr>
                    <th colspan="4" style="text-align: left;">Referenced by:</th>
                </tr>
                <tr>
                    <td colspan="4">
                        <ul class="references">
                            <li class="reference">
                                &larr; <strong>User Story</strong> (<a class=" ticket" href="/ticket/2">#2</a>): A Story
                            </li>
                        </ul>
                    </td>
                </tr>
            </table>
        </div>
    </div>
    
    <form action="/ticket/5" method="post" id="propertyform">
        <div><input type="hidden" name="__FORM_TOKEN" value="2e366dc160ef33ddd6d5d584" /></div>
        <input type="hidden" name="action" value="leave" />
        <h3><a id="edit" onfocus="$('#comment').get(0).focus()">Add/Change #5 (Some forgotten task)</a></h3>
        <div class="field">
            <fieldset class="iefix">
                <label for="comment">Comment (you may use <a tabindex="42" href="/wiki/WikiFormatting">WikiFormatting</a> here):
                </label><br />
                <p>
                    <textarea id="comment" name="comment" class="wikitext" rows="10" cols="78">
                    </textarea>
                </p>
            </fieldset>
        </div>
        <div class="buttons">
            <input type="hidden" name="ts" value="2009-09-24 09:58:22+00:00" />
            <input type="hidden" name="replyto" />
            <input type="hidden" name="cnum" value="1" />
            <input type="submit" name="preview" value="Preview" /> 
            <input type="submit" name="submit" value="Submit changes" />
        </div>
    </form>
</div>
'''


linkified_attribute_fixture = '''
<tr>
    <th id="h_milestone">
      Milestone:
    </th>
    <td headers="h_milestone">
          <a class="milestone" href="/milestone/MyMilestone">MyMilestone</a>
    </td>
    <th id="h_keywords">
      Keywords:
    </th>
    <td headers="h_keywords" class="searchable">
          n.a.
    </td>
</tr>'''


class TestTicketAttributesCanBeExtractedFromViewTicketPage(AgiloTestCase):
    
    def setUp(self):
        self.super()
        self.tester = TicketViewPageTester(None, None, html=fixture)
    
    def test_can_extract_id(self):
        self.assert_equals(5, self.tester.id())
    
    def test_can_extract_summary(self):
        self.assert_equals('Some forgotten task', self.tester.summary())
    
    def test_can_extract_description(self):
        self.assert_equals('A random description', self.tester.description())
    
    def test_can_extract_reporter(self):
        self.assert_equals('a_reporter', self.tester.reporter())
    
    def test_can_extract_owner(self):
        self.assert_equals('an_owner', self.tester.owner())
    
    def test_can_extract_status(self):
        self.assert_equals('new', self.tester.status())
    
    def test_can_extract_sprint(self):
        self.assert_equals('In the middle of nowhere', self.tester.sprint())
    
    def test_can_extract_remaining_time(self):
        self.assert_equals('7.0h', self.tester.remaining_time())
    
    def test_can_extract_resources(self):
        self.assert_equals('n.a.', self.tester.resources())
    
    def test_can_extract_story_points(self):
        story_html = fixture.replace('remaining_time', 'rd_points').replace('Remaining Time', 'User Story Points')
        tester = TicketViewPageTester(None, None, html=story_html.replace('7.0h', '12'))
        self.assert_equals(12, tester.story_points())
        tester = TicketViewPageTester(None, None, html=story_html.replace('7.0h', 'n.a.'))
        self.assert_equals('n.a.', tester.story_points())
    
    def test_can_extract_linkified_attributes(self):
        self.tester = TicketViewPageTester(None, None, html=linkified_attribute_fixture)
        self.assert_equals('MyMilestone', self.tester.milestone())
    
    def test_can_provide_value_object_with_all_values(self):
        expected_dict = dict(
            id=self.tester.id(),
            summary=self.tester.summary(),
            description=self.tester.description(),
            reporter=self.tester.reporter(),
            owner=self.tester.owner(),
            status=self.tester.status(),
            sprint=self.tester.sprint(),
            remaining_time=self.tester.remaining_time(),
            resources=self.tester.resources())
        self.assert_equals(expected_dict, self.tester.ticket())
    
    def test_knows_all_fiels_that_are_present_on_page(self):
        expected_fields = [Key.ID, Key.SUMMARY, Key.DESCRIPTION, Key.REPORTER,
                           Key.OWNER, Key.STATUS, Key.SPRINT, Key.REMAINING_TIME,
                           'resources']
        self.assert_equals(set(expected_fields), self.tester.fields())
    
    def test_missing_fields_are_not_returned(self):
        html = fixture.replace('remaining_time', '').replace('Remaining Time', '')
        tester = TicketViewPageTester(None, None, html=html)
        self.assert_false(Key.REMAINING_TIME in tester.fields())
        self.assert_false(Key.REMAINING_TIME in tester.ticket())


trac_012_fixture = '''<div class="ticket" id="content">
    <ul id="tabbed_pane">
        <li class="selected" id="view"><a href="/agilo/ticket/2">View</a></li>
        <li id="edit">
            <a href="/agilo/ticket/2?pane=edit">Edit</a>
        </li>
    </ul>
    <h1 id="trac-ticket-title">Task #2 <span class="status">(new)</span></h1>
    <!-- snipped -->
</div>'''

class TestCanExtractTicketAttributesInTrac012(AgiloTestCase):
    
    def setUp(self):
        self.super()
        self.tester = TicketViewPageTester(None, None, html=trac_012_fixture)
    
    def test_can_extract_id(self):
        self.assert_equals(2, self.tester.id())


