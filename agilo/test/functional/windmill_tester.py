# -*- coding: utf-8 -*-
#   Copyright 2010 Agile42 GmbH
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

from trac.web import Href
from trac.util.text import unicode_quote

from agilo.api import ValueObject
from agilo.test.pythonic_testcase import assert_true
from agilo.utils import Key
from agilo.utils.simple_super import SuperProxy

from agilo.test.pythonic_testcase import *

__all__ = ['WindmillPageObject', 'WindmillTester']

def assert_equals(expected, actual, msg=''):
    if hasattr(actual, 'strip'): actual = actual.strip()
    if hasattr(expected, 'strip'): expected = expected.strip()
    assert expected == actual, "%s != %s : %s" % (repr(expected), repr(actual), msg)


def assert_not_equals(expected, actual, msg=''):
    if hasattr(actual, 'strip'): actual = actual.strip()
    if hasattr(expected, 'strip'): expected = expected.strip()
    assert expected != actual, "%s == %s : %s" % (repr(expected), repr(actual), msg)


class WindmillPageObject(object):
    
    super = SuperProxy()
    
    def __init__(self, tester):
        self.tester = tester
        self.windmill = self.tester.windmill
    
    def output_for_js(self, js):
        return self.tester.output_for_js(js)
    
    def url(self):
        raise NotImplementedError()
    
    def go(self):
        self.windmill.open(url=self.url())
        self.windmill.waits.forPageLoad()
        return self
    
    def _assert(self, expected, actual):
        assert expected != actual, "should '%s' != '%s'" % (expected, actual)
    


class BacklogPage(WindmillPageObject):
    def __init__(self, tester, is_product_backlog=True, sprint_name=None):
        self.super(tester)
        self.is_product_backlog = is_product_backlog
        self.sprint_name = sprint_name
    
    def url(self):
        if self.is_product_backlog:
            return self.tester.href().backlog(Key.PRODUCT_BACKLOG)
        else:
            return self.tester.href().backlog(Key.SPRINT_BACKLOG, self.sprint_name)
    
    def go(self):
        self.super()
        self.windmill.waits.forNotElement(jquery="('#loader')[0]")
        self.windmill.waits.forElement(jquery="('#backlog h1')[0]")
        # TODO: (fs) This needs to be extended to check release backlogs as well...
        backlog_title = self.output_for_js("$('#backlog h1').text().trim()")
        if self.is_product_backlog:
            assert_equals('Product Backlog', backlog_title)
        else:
            assert_contains('Sprint Backlog for %s' % self.sprint_name, backlog_title)
            self.assert_correct_sprint_is_selected_in_sprintbacklog_chooser()
        return self
    
    def assert_correct_sprint_is_selected_in_sprintbacklog_chooser(self):
        # This is also important because it tests as a side-effect that calling
        # the new backlog page will put the sprint in the user's session.
        
        # option:selected does not work because it also finds the implicitly
        # selected first option element in a select list.
        js = '$("*[name=\'sprint_view\'] option[selected]").text()'
        assert_equals(self.sprint_name, self.output_for_js(js))
    
    # Accessing Tickets ..............................................................
    
    def number_of_shown_tickets(self):
        number_of_containers = self.output_for_js("$('dt:not([id^=\\'ticketID--2\\']) > .id').length")
        number_of_children = self.output_for_js("$('dd > .id').length")
        return number_of_containers + number_of_children
    
    def information_for_ticket_id(self, ticket_id):
        "Take note, not all the values returned here are actually in the ticket"
        ticket_selector = '$("#ticketID-%s")' % ticket_id
        js = ticket_selector + ".children().map(function(){return [$(this).metadata().field, $(this).text()];}).get()"        
        output = self.output_for_js(js)
        keys, values = output[::2], output[1::2]
        result = dict(zip(keys, values))
        # Normalize a few values to ease comparison
        result['id'] = int(result['id'])
        return result
    
    def parse_int(self, a_string):
        if a_string in ('-1', '-2'):
            return int(a_string)
        return int(a_string.split('-')[0])
    
    def verify_single_item(self, actual_ticket_id, expected_ticket):
        # TODO: ensure that really every key present is compared
        parsed_actual_ticket_id = self.parse_int(actual_ticket_id)
        assert_equals(expected_ticket.id, parsed_actual_ticket_id)
        displayed_information = self.information_for_ticket_id(actual_ticket_id)
        for key, value in displayed_information.items():
            if key not in expected_ticket or 'n.a.' == expected_ticket[key]:
                continue
            expected, actual = expected_ticket[key], value
            
            # Normalizing the values to get less test failures
            if key in ['remaining_time', 'total_remaining_time']:
                # Get rid of the unit suffix and convert to floats
                expected, actual = float(expected[:-1]), float(actual)
            assert_equals(expected, actual, "failing key is: " + key)
    
    def extract_id_from_jquery(self, ticket_selector):
        js = ticket_selector + """.map(function(){
            return $(this).attr('id').substring('ticketID-'.length);
        }).get();"""
        return self.output_for_js(js)
    
    def top_level_item_ids(self):
        return self.extract_id_from_jquery("$('.backlog > dl > dt:not([id^=\\'ticketID--2\\'])')")
    
    def children_of_ticket_id(self, container_id):
        js = """
        function getSiblings(ticketID) {
            var container = $('#ticketID-' + ticketID);
            if (container.next().hasClass('childcontainer'))
                return container.next().find('dt:first');
            else
                return container.siblings();
        };
        getSiblings(%s)""" % container_id
        return self.extract_id_from_jquery(js)
    
    def assert_shows_only(self, ticket_tree):
        top_level_item_ids = self.top_level_item_ids()
        assert_equals(len(ticket_tree), len(top_level_item_ids))
        
        for expected_ticket, actual_ticket_id in zip(ticket_tree, top_level_item_ids):
            self.verify_single_item(actual_ticket_id, expected_ticket)
            if not hasattr(expected_ticket, 'children'):
                continue
            children_ids = self.children_of_ticket_id(actual_ticket_id)
            expected_children = expected_ticket.children
            assert_equals(len(expected_children), len(children_ids))
            for expected_child, actual_child_id in zip(expected_children, children_ids):
                self.verify_single_item(actual_child_id, expected_child)
    
    def count_renderings_of_ticket_with_id(self, a_ticket_id):
        return self.output_for_js("""$('[id^="ticketID-%d"]').length""" % a_ticket_id)
    
    def order_of_tickets(self):
        js = """$('.backlog').find('[id^="ticketID-"]:visible').not('[id="ticketID--2"]')"""
        return map(self.parse_int, self.extract_id_from_jquery(js))
    
    # --- backlog totals -------------------------------------------------------
    
    def totals(self):
        data = {}
        for field_name in self.shown_field_for_totals_row():
            data[field_name] = self.value_for_total_field(field_name)
        return ValueObject(data)
    
    
    # Interact with inline editor ..............................................................
    
    def update_inline_editor(self, locator_jquery, new_value):
        js = locator_jquery + ".click().find(':input').val(%s).blur()" % repr(new_value)
        self.output_for_js(js)
        # This assumes there is only one inPlaceEditor open at any time
        self.tester.windmill.waits.forNotElement(jquery="('.editInPlace-active')[0]")

    def selector_for_field_in_ticket(self, a_field_name, a_ticket_id):
        return "$('#ticketID-%s .%s')" % (a_ticket_id, a_field_name)

    def update_inline_editor_field_for_ticket(self, a_field_name, a_ticket_id, a_new_value, should_fail=False):
        selector = self.selector_for_field_in_ticket(a_field_name, a_ticket_id)
        self.update_inline_editor(selector, a_new_value)
        changed_task = self.tester.twill_tester.navigate_to_ticket_page(a_ticket_id).ticket()
        expected, actual = a_new_value, changed_task[a_field_name]
        if 'n.a.' == actual:
            actual = '' # rendered form of '' :)
        
        if a_field_name in ['remaining_time'] \
            and actual is not '':
            if actual.endswith('h') or actual.endswith('d'):
                actual = actual[:-1]
            actual = float(actual)
        
        if should_fail:
            assert_not_equals(expected, actual)
        else:
            assert_equals(expected, actual)
    
    # REFACT: switch argument order for more clarity
    # REFACT(fs): What about a sub class for the in-place-editor? All these 
    # methods get ticket ids for their first argument.
    def update_remaining_time_for_ticket(self, a_ticket_id, a_remaining_time, should_fail=False):
        self.update_inline_editor_field_for_ticket('remaining_time', a_ticket_id, a_remaining_time, should_fail)
    
    def update_sprint_for_ticket(self, a_ticket_id, a_sprint_name):
        self.update_inline_editor_field_for_ticket('sprint', a_ticket_id, a_sprint_name)
    
    def update_priority_for_ticket(self, a_ticket_id, new_value):
        assert new_value in ['', 'Mandatory', 'Linear', 'Exciter'], "Can't accept value '%s'" % new_value
        self.update_inline_editor_field_for_ticket('story_priority', a_ticket_id, new_value)
    
    def shown_field_for_ticket(self, ticket_id):
        fields_selector = "$('#ticketID-%s span')" % ticket_id
        contains_extractor = ".map(function(){ return $(this).metadata().field; }).get()"
        return self.output_for_js(fields_selector + contains_extractor)

    def shown_field_for_totals_row(self):
        fields_selector = "$('#ticketID--2 span')"
        contains_extractor = ".map(function(){ return $(this).metadata().field; }).get()"
        return self.output_for_js(fields_selector + contains_extractor)
    
    def error_notice(self):
        span_selector = "$('span#notice').text()"
        return self.output_for_js(span_selector)
    
    def value_for_ticket_field(self, ticket_id, field_name):
        return self.output_for_js("$('#ticketID-%s span.%s').text()" % (ticket_id, field_name))

    def value_for_total_field(self, field_name):
        return self.output_for_js("$('#ticketID--2 span.%s').text()" % field_name)
    
    def wait_for_field_to_have_content(self, ticket_id, field_name, field_content):
        xpath = '//*[@id="ticketID-%s"]//*[contains(@class, "%s") and contains(text(), "%s")]' \
                % (ticket_id, field_name, field_content)
        self.windmill.waits.forElement(xpath=xpath)

    def has_select_editor_for_field_in_ticket(self, a_field_name, a_ticket_id):
        selector = self.selector_for_field_in_ticket(a_field_name, a_ticket_id)
        js = selector + ".click().find(':input').is('select')"
        is_select = self.output_for_js(js)
        js = selector + ".click().find(':input').blur()"
        self.output_for_js(js)
        return is_select

    
    # --- Interaction with the burndown chart ----------------------------------
    
    def click_show_burndown_chart_toggle(self):
        self.windmill.click(jquery="('.buttons #burndown-button')[0]")
    
    def set_filter_value(self, filter_by):
        self.output_for_js("$('#filter-attribute-popup').val('" + filter_by + "').change()")
        # These commands should be able to simulate everything, but choke on the empty option
        # self.tester.windmill.click(id=u'filter-attribute-popup')
        # self.tester.windmill.select(option=filter_by, id=u'filter-attribute-popup')
        # self.tester.windmill.click(value=filter_by)
    
    def toggle_hide_closed_tickets(self):
        self.windmill.click(jquery="('#hide-closed-button')[0]")
    
    def toggle_show_only_my_tickets(self):
        self.windmill.click(jquery="('#show-onlymine-button')[0]")
    
    def can_click_confirm_commitment(self):
        # button must be always there as per UI guidelines
        self.windmill.asserts.assertJS(js="1 === $('#commit-button').length")
        
        is_button_clickable = self.output_for_js("0 === $('#commit-button.disabled').length")
        return is_button_clickable
    
    def click_confirm_commitment(self):
        assert_true(self.can_click_confirm_commitment())
        self.windmill.click(jquery="('#commit-button')[0]")
    
    # Interacting with contingents
    # Contingents are lists of dict(name='fnord', availableTime='23', spentTime='0', remainingTime='0')
    
    def toggle_contingents_display(self):
        self.windmill.click(jquery="('#contingents-toggle a')[0]")
    
    def assert_contingents(self, expected_contingents):
        # TODO: should also check via twill on the team_page
        js = """
        $('#contingent tbody tr').map(function() {
            var values = {};
            $('td', this).each(function() {
                return values[$(this).attr('class')] =$(this).text();
            });
            return values;
        }).get();
        """
        actual_contingents = self.output_for_js(js)
        assert_equals(len(expected_contingents), len(actual_contingents))
        for expected, actual in zip(expected_contingents, actual_contingents):
            assert_dict_contains(expected, actual)
    
    def add_contingents(self, name, amount):
        new_number_of_contingents = int(self.output_for_js("$('#contingent tbody tr').length")) + 1
        self.windmill.click(jquery=u"('#buttonBottomAdd a')[0]")
        self.windmill.type(id=u'name', text=name)
        self.windmill.type(id=u'amount', text=amount)
        self.windmill.click(jquery=u"('#exposed .buttons :submit')[0]")
        self.windmill.waits.forJS(js="%s === jQuery('#contingent tbody tr', windmill.testWindow.document).length" % new_number_of_contingents)
    
    def change_remaining_time_for_contingent(self, contingent_name, delta_amount):
        # that selector is not as good as it could be, but :has(.name:contains()) 
        # doesn't work due to jquery #6322 http://dev.jquery.com/ticket/6322
        # Should be specific enough for us though
        selector_js = "$(\"#contingent tbody tr:has(:contains(%s))\").find('.burnTime')" % repr(contingent_name)
        self.update_inline_editor(selector_js, delta_amount)
    
    def assert_and_change_remaining_time_for_contingent(self, delta_amount, expected_contingent):
        self.change_remaining_time_for_contingent(expected_contingent.name, delta_amount)
        self.assert_contingents([expected_contingent])
    

class WindmillTester(object):
    
    super = SuperProxy()
    
    def __init__(self, testcase):
        self.testcase = testcase
        self.twill_tester = testcase.tester
        self.url = testcase.tester.url
        self.env = testcase.testenv.get_trac_environment()
        self.windmill = testcase.windmill
    
    # Navigation ..............................................................
    
    def login_as(self, username, password=None):
        if not password:
            password = username
        
        assert 'http://' == self.url[:7]
        unused, protocol, host_and_rest = self.url.partition('http://')
        new_url = "%s%s:%s@%s/login" % (protocol, unicode_quote(username), unicode_quote(password), host_and_rest)
        self.windmill.open(url=new_url)
        self.windmill.waits.forPageLoad()
        self.windmill.waits.forElement(jquery="('ul.metanav li:contains(Logged in as %s)')[0]" % username)
        
        self.windmill.asserts.assertText(
            xpath="//*[contains(@class, 'metanav')]/li[1]", 
            validator='Logged in as %s' % username)

    def logout(self):
        self.windmill.open(url="/logout")

    def go_to_frontpage(self):
        self.windmill.open(url=self.url)
        self.windmill.waits.forPageLoad()
    
    # REFACT: Get rid of that method
    def go_to_sprint_backlog(self, sprint_name=None):
        if not sprint_name:
            sprint_name = self.testcase.sprint_name()
        
        page_url = self.href().backlog(Key.SPRINT_BACKLOG, sprint_name)
        self.windmill.open(url=page_url)
        self.windmill.waits.forPageLoad()
        self.windmill.waits.forNotElement(jquery="('#loader')[0]")
        
        self.windmill.asserts.assertTextIn(xpath='*', validator='Sprint Backlog for %s' % sprint_name)
    
    def go_to_new_sprint_backlog(self, sprint_name=None):
        if not sprint_name:
            sprint_name = self.testcase.sprint_name()
        return BacklogPage(self, False, sprint_name).go()
    
    def go_to_new_product_backlog(self):
        return BacklogPage(self, True).go()


    def go_to_view_tickets(self):
        self.windmill.waits.forElement(link=u'View Tickets', timeout=u'8000')
        self.windmill.click(link=u'View Tickets')
        self.windmill.waits.forPageLoad(timeout=u'20000')


    # REFACT: Get rid of that method
    def go_to_product_backlog(self):
        page_url = self.href().backlog(Key.PRODUCT_BACKLOG)
        self.windmill.open(url=page_url)
        self.windmill.waits.forPageLoad()
        
        self.windmill.asserts.assertTextIn(xpath='*', validator='Product Backlog')
    
    # Configuration .............................................................
    def set_default_timeout(self, seconds):
        milliseconds = int(seconds * 1000)
        self.windmill.execIDEJS(js=u'windmill.timeout=%s'%milliseconds)
    
    # Convenience .............................................................
    
    def current_url(self):
        return self.output_for_js('window.location.href')
    
    def href(self):
        return Href(self.url)
    
    def output_for_js(self, js):
        return self.windmill.execJS(js=js)['output']
    

