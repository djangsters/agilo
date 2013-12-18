# -*- encoding: utf-8 -*-
#   Copyright 2010 Agile42 GmbH, Berlin (Germany)
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

import csv
import re
from StringIO import StringIO
from tempfile import NamedTemporaryFile

import twill
from twill.errors import TwillAssertionError, TwillException
from twill.utils import print_form

from trac.tests.contentgen import random_page, random_sentence, random_word
from trac.tests.functional import better_twill, tc
from trac.tests.functional.tester import FunctionalTester
from trac.tests.functional.better_twill import twill_write_html
from trac.util.compat import set
from trac.util.datefmt import format_date, format_datetime
from trac.util.text import unicode_quote, unicode_urlencode, to_unicode
try:
    from _mechanize_dist._mechanize import BrowserStateError
except ImportError:
    # in case you have 'sanitized' twill which does not has its own, private
    # mechanize (like Fedora's python-twill)
    from mechanize import BrowserStateError

from agilo.api import ValueObject
from agilo.csv_import import IMPORT_URL
from agilo.csv_import.csv_file import CSVFile
from agilo.csv_import.web_ui import ImportParameter
from agilo.scrum import BACKLOG_TICKET_TABLE, SPRINT_URL, TEAM_URL, BACKLOG_URL
from agilo.ticket.links import LINKS_TABLE
from agilo.test.test_util import Usernames
from agilo.utils import Key, Type
from agilo.utils.config import AgiloConfig
from agilo.utils.days_time import date_to_datetime, datetime_str_to_datetime, \
    now, today
from agilo.utils.db import get_db_type
from agilo.utils.simple_super import SuperProxy

__all__ = ["AgiloTester", 'Usernames']


class UnicodeCSVWriter(object):
    """A CSV writer which will write rows to CSV file "f", which is encoded in 
    the given encoding.
    Inspired by Python's example UnicodeWriter but heavily simplified."""
    
    def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
        self.encoding = encoding
        self.writer = csv.writer(f, dialect=dialect, **kwds)
    
    def _convert_to_unicode(self, row):
        unicode_row = []
        for item in row:
            if isinstance(item, unicode):
                item = item.encode(self.encoding)
            unicode_row.append(str(item))
        return unicode_row
    
    def writerow(self, row):
        self.writer.writerow(self._convert_to_unicode(row))
    
    def writerows(self, rows):
        for row in rows:
            self.writerow(row)


class PageObject(object):
    
    super = SuperProxy()
    
    def path_and_parameters(self):
        raise NotImplementedError
    
    def html(self):
        if getattr(self, '_html', None) is None:
            self.go()
        return self._html
    
    def set_html(self, html):
        self._html = html
    
    def save_html(self):
        # The naive version does not work because the highly useful delete 
        # parameter is 2.6 only
#        temp = NamedTemporaryFile(delete=False, suffix='.html')
#        filename = temp.name
#        temp.write(self.html())
        filename = NamedTemporaryFile(suffix='.html').name
        file(filename, 'wb').write(self.html())
        print 'saved html at:', filename
    
    def go(self):
        # REFACT: use Href
        path, parameters = self.path_and_parameters()
        url = self.tester.url + unicode_quote(path) + '?' + unicode_urlencode(parameters)
        tc.go(url)
        tc.code(200)
        self.set_html(tc.show())
        return self
    
    def submit(self, button_name=None):
        tc.submit(button_name)
        self.set_html(tc.show())
    
    def system_messages(self, message_label):
        regex = r'<div class="system-message[^"]*">\s*<strong>%s[^:]*:</strong>\s*(.*?)\s*</div>' % message_label
        return re.findall(regex, self.html(), re.DOTALL)
    
    def has_notice(self, message):
        for notice in self.system_messages('Notice'):
            if message in notice:
                return True
        return False
    
    def has_warning(self, message):
        for warning in self.system_messages('Warning'):
            if message in warning:
                return True
        return False
    
    def has_warnings(self):
        return len(self.system_messages('Warning')) > 0

    def remove_html_and_whitespace(self, html_with_whitespace):
        remove_html = re.compile(r"(<[^>]+>)")
        text_with_whitespace = remove_html.sub('', html_with_whitespace)
        text_without_whitespace = " ".join(text_with_whitespace.split())
        return text_without_whitespace

class TeamOverviewPageTester(PageObject):
    def __init__(self, tester, team_name, html=None):
        self.tester = tester
        self.team_name = team_name
        self.set_html(html)
    
    def path_and_parameters(self):
        path = TEAM_URL + '/%s' % self.team_name
        return path, {}
    
    def _extract_metrics_table(self):
        match = re.search('(<table[^>]*id="metrics"[^>]*>.+?</table>)', self.html(), re.DOTALL)
        return match.group(0)
    
    def _extract_displayed_metric_names(self, table_html):
        match = re.search('<thead>.*?<tr>(.*?)</tr>.*?</thead>', table_html, re.DOTALL)
        header_row_html = match.group(1)
        shown_captions = re.findall('<th>(.*?)</th>', header_row_html, re.DOTALL)
        displayed_keys = map(lambda x: x.lower().replace(' ', '_'), shown_captions)
        return displayed_keys
    
    def _extract_data_rows(self, table_html):
        raw_data_rows = []
        remove_html = re.compile(r"(<[^>]+>)")
        match = re.search('<tbody>(.*?)</tbody>', table_html, re.DOTALL)
        html_rows = re.findall('<tr>(.*?)</tr>', match.group(1), re.DOTALL)
        for row in html_rows:
            matches = re.findall('<td[^>]*?>(.*?)</td>', row, re.DOTALL)
            data = map(lambda x: remove_html.sub('', x), matches)
            raw_data_rows.append(data)
        return raw_data_rows
    
    def metrics(self):
        metrics_by_sprint = {}
        
        table_html = self._extract_metrics_table()
        metric_order = self._extract_displayed_metric_names(table_html)
        raw_data_rows = self._extract_data_rows(table_html)
        position_of_sprint_column = metric_order.index(Key.SPRINT)
        for row in raw_data_rows:
            sprint_name = row[position_of_sprint_column]
            metrics_data = {}
            for key, value in zip(metric_order, row):
                metrics_data[key] = value
            metrics_by_sprint[sprint_name] = metrics_data
        return metrics_by_sprint
    
    def _extract_metrics_for_sprint(self, sprint_name):
        return self.metrics()[sprint_name]
    
    def has_value_for_sprint(self, metrics_name, sprint_name):
        return metrics_name in self._extract_metrics_for_sprint(sprint_name)
    
    def value_for_sprint(self, metrics_name, sprint_name):
        return self._extract_metrics_for_sprint(sprint_name)[metrics_name]


class SprintEditPageTester(PageObject):
    def __init__(self, tester, sprint_name, html=None):
        self.tester = tester
        self.sprint_name = sprint_name
        self.set_html(html)
    
    def path_and_parameters(self):
        path = '/sprint/%s/edit' % self.sprint_name
        return path, {}
    
    def go(self):
        value = super(SprintEditPageTester, self).go()
        tc.find('Edit Sprint %s' % self.sprint_name)
        return value
    
    def set_name(self, name):
        tc.formvalue('editform', 'sprint_name', str(name))
    
    def set_start(self, start):
        if not isinstance(start, basestring):
            start = format_datetime(start)
        tc.formvalue('editform', 'start', str(start))
    
    def set_end(self, end):
        tc.formvalue('editform', 'duration', '')
        if not isinstance(end, basestring):
            end = format_datetime(end)
        tc.formvalue('editform', 'end', str(end))
    
    def set_duration(self, duration):
        tc.formvalue('editform', 'end', '')
        tc.formvalue('editform', 'duration', str(duration))



class TeamMemberAdminPageTester(PageObject):
    def __init__(self, tester, team_member_name, team_name, html=None):
        self.tester = tester
        self.team_member_name = team_member_name
        self.team_name = team_name
        self.set_html(html)
    
    def path_and_parameters(self):
        path = '/admin/agilo/teams/%s/' % self.team_name
        parameters = {'team_member': self.team_member_name}
        return path, parameters
    
    def set_default_capacity(self, capacity_list):
        for i, capacity in enumerate(capacity_list):
            tc.formvalue('modcomp', 'ts_%d' % i, str(capacity))


class TicketViewPageTester(PageObject):
    def __init__(self, tester, ticket_id, html=None):
        self.tester = tester
        self.ticket_id = ticket_id
        self.set_html(html)
    
    def path_and_parameters(self):
        path = '/ticket/%s' % self.ticket_id
        return path, {}
    
    def _result_for_regex(self, pattern):
        regex = re.compile(pattern, re.DOTALL)
        match = regex.search(self.html())
        assert match is not None #, self.html()
        matched_text = match.group(1)
        return self.remove_html_and_whitespace(matched_text)
    
    def _get_attribute_from_columns(self, field_name):
        pattern = '<th\s+id="h_%s"(?:\s+class="missing")?>.+?</th>\s*<td.*?>\s*(.*?)\s*</td>' % field_name
        return self._result_for_regex(pattern)
    
    def map_to_friendly_field_names(self, fields):
        # remember when you add a new mapping, you need to define method with 
        # the friendly name - otherwise we need to have two methods:
        #     fields() + human_readable_fields()
        translator = {Key.RESOURCES: 'resources', Key.STORY_POINTS: 'story_points',}
        friendly_names = []
        for ugly_name in fields:
            friendly_names.append(translator.get(ugly_name, ugly_name))
        return friendly_names
    
    def fields(self):
        labels = re.findall('<th\s+id="h_(\S+)"(?:\s+class="missing")?>.+?</th>', self.html(), re.DOTALL)
        
        return set([Key.ID, Key.SUMMARY, Key.DESCRIPTION, Key.REPORTER, Key.OWNER,
                    Key.STATUS] + self.map_to_friendly_field_names(labels))
    
    def value_for_field(self, fieldname):
        if hasattr(self, fieldname):
            return getattr(self, fieldname)()
        return self._get_attribute_from_columns(fieldname)
    
    def ticket(self):
        data = ValueObject(id=self.id(),
            summary=self.summary(),
            description=self.description(),
            status=self.status())
        
        for field in self.fields():
            data[field] = self.value_for_field(field)
        return data
    
    # generic attributes  ......................................................
    
    def id(self):
        id_pattern = r'<h1[^>]*>[^#]+ #(\d+).*?</h1>'
        return int(self._result_for_regex(id_pattern))
    
    def summary(self):
        summary_pattern = '<(?:span|h2) class="summary(?:\s+searchable)?">(.*?)</(?:span|h2)>'
        return self._result_for_regex(summary_pattern)
    
    def description(self):
        pattern = '<div class="searchable">\s*<p>\s*(.*?)\s*</p>\s*</div>'
        html_description = self._result_for_regex(pattern)
        return '\n'.join(html_description.split('<br />')).strip()
    
    def reporter(self):
        return self._get_attribute_from_columns(Key.REPORTER)
    
    def owner(self):
        return self._get_attribute_from_columns(Key.OWNER)
    
    def status(self):
        status_pattern = '<span class="status">\(([\w\s]+)\)</span>'
        return self._result_for_regex(status_pattern)
    
    # Optional/type-specific attributes ........................................
    
    def milestone(self):
        return self._get_attribute_from_columns(Key.MILESTONE)
    
    def sprint(self):
        return self._get_attribute_from_columns(Key.SPRINT)
    
    def remaining_time(self):
        return self._get_attribute_from_columns(Key.REMAINING_TIME)
    
    def resources(self):
        return self._get_attribute_from_columns(Key.RESOURCES)
    
    def story_points(self):
        story_points_string = self._get_attribute_from_columns(Key.STORY_POINTS)
        if story_points_string != 'n.a.':
            return int(story_points_string)
        return story_points_string
    


class TeamSprintDetailTester(PageObject):
    def __init__(self, tester, team_name, sprint_name, html=None):
        self.tester = tester
        self.team_name = team_name
        self.sprint_name = sprint_name
        self.set_html(html)
    
    def path_and_parameters(self):
        path = '/team/%s/%s' % (self.team_name, self.sprint_name)
        return path, {}
    
    def _extract_contingent_rows(self):
        match = re.search('<form[^>]*?name="contingent_form"[^>]*?>(.*?)</form>', self.html(), re.DOTALL)
        assert match is not None
        contingent_form = match.group(1)
        contingent_without_progressbar_tables = re.compile('<table class="progress">.*?</table>', re.DOTALL).sub('', contingent_form)
        assert '<table class="progress">' not in contingent_without_progressbar_tables
        contingent_html = re.search('<tbody>(.*?)</tbody>', contingent_without_progressbar_tables, re.DOTALL).group(1)
        contingent_rows = re.findall('<tr>(.*?)</tr>', contingent_html, re.DOTALL)
        return contingent_rows
    
    def _split_cells(self, row_html):
        return re.findall('<td[^>]*?>(.*?)</td>', row_html, re.DOTALL)
    
    def _contingent_from_html(self, row_html):
        cells = self._split_cells(row_html)
        can_delete_contingents = '<input ' in cells[0]
        if can_delete_contingents:
            cells = cells[1:]
        used_time = re.search('\s*(\d+\.\d+)\s*', cells[2], re.DOTALL).group(1)
        return ValueObject(dict(name=cells[0], amount=cells[1], used=used_time))
    
    def _contingents(self):
        return map(lambda row: self._contingent_from_html(row), self._extract_contingent_rows())
    
    def contingent_names(self):
        return set(map(lambda contingent: contingent.name, self._contingents()))
    
    def contingent_for_name(self, name):
        contingents = filter(lambda contingent: contingent.name == name, self._contingents())
        if len(contingents) == 0:
            return None
        assert len(contingents) == 1
        return contingents[0]
    
    def can_delete_contingents(self):
        if len(self.contingent_names()) == 0:
            return None
        row_html = self._extract_contingent_rows()[0]
        first_cell = self._split_cells(row_html)[0]
        return '<input ' in first_cell



class AgiloTester(FunctionalTester):
    """A special tester for Agilo, adds some functionalities to the 
    FunctionalTester
    
    1. go_to_* methods should return a page object that lets you interact with that page
    2. we use the suffix _admin_page for admin and just _page for normal pages.
    """
    
    # copied from trac because we don't want automatic login
    def __init__(self, url, repo_url, env=None):
        """Create a FunctionalTester for the given Trac URL and Subversion
        URL"""
        # do not call super - it does the auto login
        self.url = url
        self.repo_url = repo_url
        self.ticketcount = 0
        self.current_user = None
        
        if env:
            self.set_env(env)
        self.testcase = None
    # end of copy
    
    # -------------------------------------------------------------------------
    # copied from trac's FunctionalTester because we need to go to the ticket
    # edit page that trac does not (can not) know)
    def attach_file_to_ticket(self, ticketid, data=None):
        """Attaches a file to the given ticket id.  Assumes the ticket
        exists.
        """
        if data == None:
            data = random_page()
        self.go_to_view_ticket_page(ticketid)
        # set the value to what it already is, so that twill will know we
        # want this form.
        tc.formvalue('attachfile', 'action', 'new')
        tc.submit()
        tc.url(self.url + "/attachment/ticket/" \
               "%s/\\?action=new&attachfilebutton=Attach\\+file" % ticketid)
        tempfilename = random_word()
        fp = StringIO(data)
        tc.formfile('attachment', 'attachment', tempfilename, fp=fp)
        tc.formvalue('attachment', 'description', random_sentence())
        tc.submit()
        tc.url(self.url + '/attachment/ticket/%s/$' % ticketid)
    # -------------------------------------------------------------------------
    
    def set_env(self, env):
        """Sets the Trac Environment, of the currently tested project"""
        self.env = env
    
    def set_testcase(self, testcase):
        self.testcase = testcase
    
    # -------------------------------------------------------------------------
    
    def create_team_member(self, team_name, member_name):
        # REFACT: Proper API to create new users
        functional_testenv = self.testcase.testenv
        functional_testenv._setup_user(member_name)
        self.add_member_to_team(team_name, member_name);
    
    def create_team_with_two_members(self):
        team_name = self.testcase.team_name()
        self.create_new_team(team_name)
        self.create_team_member(team_name, self.testcase.first_team_member_name())
        self.create_team_member(team_name, self.testcase.second_team_member_name())
        return team_name
    
    def create_release_with_sprint(self, team_name=None):
        sprint_name = self.testcase.sprint_name()
        milestone_name = self.create_milestone('MilestoneFor' + sprint_name)
        self.create_sprint_for_milestone(milestone_name, sprint_name, 
                                         team=team_name)
    
    def create_userstory_with_tasks(self, sprint_name=None, requirement_id=None):
        if sprint_name is None:
            sprint_name = self.testcase.sprint_name()
        
        # REFACT? Same API for creating referenced ticket+non-referenced?
        if requirement_id is not None:
            story_id = self.create_referenced_ticket(requirement_id, Type.USER_STORY, 'A Story', sprint=sprint_name, rd_points='20')
        else:
            story_id = self.create_new_agilo_userstory('A Story', sprint=sprint_name, rd_points='20')
        task1_id = self.create_referenced_ticket(story_id, Type.TASK, 'First Task', sprint=sprint_name, remaining_time=3)
        task2_id = self.create_referenced_ticket(story_id, Type.TASK, 'Second Task', sprint=sprint_name, remaining_time=7)
        
        return (story_id, [task1_id, task2_id])
    
    def create_sprint_with_small_backlog(self):
        team_name = self.create_team_with_two_members()
        self.create_release_with_sprint(team_name=team_name)
        
        requirement_id = self.create_new_agilo_requirement('A Requirement')
        story_id, task_ids = self.create_userstory_with_tasks(requirement_id=requirement_id)
        return [requirement_id, story_id, task_ids]
    
    # -------------------------------------------------------------------------
    
#    def remove_member_from_team(self, member_name):
#        """Removes the member from his team (if set)"""
#        # fs: There is now way to remove a member from his team without knowing
#        # the team name or logging in as that member.
#        from agilo.scrum import TeamMemberModelManager
#        member = TeamMemberModelManager(self.env).get(name=member_name)
#        if member is not None:
#            member.team = None
#            member.save()
#        member = TeamMemberModelManager(self.env).get(name=member_name)
#        if member is not None:
#            assert (member.team is None)
#    
    def add_member_to_team(self, team_name, member_name):
        """Adds a member to a team. Currently very basic, no setting of default
        capacity possible."""
        team_admin_url = self.url + '/admin/agilo/teams/' + unicode_quote(team_name)
        tc.go(team_admin_url)
        tc.code(200)
        tc.formvalue('modcomp', 'team_member', member_name)
        tc.submit('add')
        tc.code(200)
        # check if there is the AccountManager plugin installed and the 
        # create use is there
        if 'name="createUser_ok"' in tc.show():
            tc.fv('modcomp', 'createUser_ok', 'click')
            tc.submit('createUser_ok')
            tc.code(200)
        # write the name
        tc.fv('modcomp', 'member_full_name', member_name.title())
        tc.submit('save')
        tc.code(200)
        tc.find('<td><a href="\?team_member=[^"]+">%s</a></td>' % member_name)
    
    def accept_ticket(self, ticket_id):
        self.go_to_view_ticket_page(ticket_id)
        tc.find('<label for="action_accept">accept</label>')
        tc.formvalue('propertyform', 'action', 'accept')
        tc.submit('submit')
        user_name = self.get_user_name_of_current_user()
        tc.find('owner</strong>\s+set\s+to\s+<em>%s</em>' % user_name, flags='i')
        tc.find('\(accepted\)')
        tc.notfind('Preview \(')
    
    def assign_ticket_to(self, ticket_id, user_name):
        self.go_to_view_ticket_page(ticket_id)
        tc.formvalue('propertyform', 'action', 'reassign')
        tc.formvalue('propertyform', 'action_reassign_reassign_owner', user_name)
        tc.submit('submit')
    
    def close_ticket(self, ticket_id, resolution='fixed'):
        self.go_to_view_ticket_page(ticket_id)
        tc.formvalue('propertyform', 'action', 'resolve')
        tc.formvalue('propertyform', 'action_resolve_resolve_resolution', resolution)
        tc.submit('submit')
    
    def reopen_ticket(self, ticket_id):
        self.go_to_view_ticket_page(ticket_id)
        tc.formvalue('propertyform', 'action', 'reopen')
        tc.submit('submit')
        # in Trac 0.12 the <h1> tag also contains some attributes
        tc.find('<h1[^>]*>.*#%s.*(reopened).*</h1>' % ticket_id)
    
    def create_new_agilo_requirement(self, summary, description=None, should_fail=False, **kwargs):
        return self.create_new_agilo_ticket(Type.REQUIREMENT, summary, 
                            description=description, should_fail=should_fail, 
                            **kwargs)
    
    # REFACT: rename to create_task to align with the TestEnvironmentHelpers method with the same purpose?
    def create_new_agilo_task(self, summary, description=None, should_fail=False, **kwargs):
        task_id = self.create_new_agilo_ticket(Type.TASK, summary, 
                           description=description, should_fail=should_fail, 
                           **kwargs)
        if not should_fail:
            # User Story Points should never be a field of a task so we use this
            # check to ensure that the task only has the fields it should have.
            # But we must not check if we expect a failure because then it may
            # be that the user has no permission to create a task which means
            # that some other type is (more or less randomly) preselected in the
            # new ticket form which means that the new type may have story 
            # points shown.
            tc.notfind('User Story Points')
        return task_id
    
    def create_new_agilo_userstory(self, summary, description=None, should_fail=False, **kwargs):
        return self.create_new_agilo_ticket(Type.USER_STORY, summary, 
                            description=description, should_fail=should_fail, 
                            **kwargs)
    
    def create_new_contingent(self, name, amount, team_name, sprint_name, should_fail=False):
        self.go_to_team_page(team_name, sprint_name)
        tc.formvalue('add_contingent_form', 'cont_name', name)
        tc.formvalue('add_contingent_form', 'cont_amount', amount)
        tc.submit()
        if not should_fail:
            tc.code(200)
            tc.find('Contingents planned for Sprint: %s' % sprint_name)
    
    def create_new_team(self, name):
        page_url = self.url + '/admin/agilo/teams'
        tc.go(page_url)
        tc.url(page_url)
        tc.code(200)
        
        utf8_team_name = to_unicode(name).encode('UTF-8')
        tc.fv('addteam', 'name', utf8_team_name)
        tc.submit('add')
         
        # we're at detail view, find the description we put in
        tc.url("%s/%s" % (page_url, unicode_quote(name)))
        tc.find(utf8_team_name)
        tc.code(200)
    
    def create_new_ticket_type(self, type_name, alias=None):
        """Adds a new ticket type through the Trac admin interface and checks 
        if it appears in the Agilo type admin page. Catches bug #264 as well.
        If an alias is specified, an alias for the new type will be created as
        well."""
        page_url = self.url + '/admin/ticket/type'
        tc.go(page_url)
        
        tc.fv('addenum', 'name', type_name)
        tc.submit('add')
        tc.find(type_name)
        
        if alias is not None:
            self.set_ticket_type_alias(type_name, alias)
    
    def set_ticket_type_alias(self, type_name, alias):
        assert alias is not None
        
        page_url = self.url + '/admin/agilo/types'
        tc.go(page_url)
        tc.find(type_name)
        tc.go("%s/%s" % (page_url, unicode_quote(type_name)))
        tc.code(200)
        tc.find(type_name) # Agilo config should be case safe now
        tc.formvalue('modcomp', 'alias', alias)
        tc.submit('save')
        tc.code(200)
        html = tc.show()
        
        type_detail_edit_link = """<a href="/admin/agilo/types/%s">%s</a>""" % (type_name, type_name)
        alias_table_part_middle = html.index(type_detail_edit_link)
        start = html.rindex('<tr>', 0, alias_table_part_middle)
        end = html.index('</tr>', alias_table_part_middle)
        type_table_part = html[start:end]
        assert '<td class="alias">%s</td>' % alias in type_table_part, type_table_part
    
    def delete_custom_field(self, fieldname, label):
        # get list page to delete a field
        page_url = self.url + '/admin/agilo/fields'
        tc.go(page_url)
        tc.url(page_url)
        tc.code(200)
        # see if one of the default links is there.
        tc.find('<td><a href="/admin/agilo/fields/%s">%s' % (unicode_quote(fieldname), unicode_quote(fieldname)))
        tc.find('<td>%s</td>' % label)
        
        # remove a field
        tc.formvalue('customfields', 'sel', '+%s' % fieldname)
        tc.submit('remove')
        # save should redirect to list page, see if field is gone
        tc.notfind(fieldname)
        tc.code(200)
    
    def _get_form_control(self, formname, fieldname):
        browser = tc.get_browser()
        form = browser.get_form(formname)
        return browser.get_form_field(form, fieldname)
    
    def _form_contains_field(self, formname, fieldname):
        try:
            self._get_form_control(formname, fieldname)
            return True
        except TwillException:
            return False
    
    def _set_ticket_formfield(self, fieldname, value):
        if not self._form_contains_field('propertyform', fieldname):
            fieldname = 'field-%s' % fieldname
        # twill silently ignores read-only (aka hidden) fields
        input_field = self._get_form_control('propertyform', fieldname)
        if fieldname == 'view_time' or fieldname == 'ts':
            input_field.readonly = False
        assert input_field.readonly == False
        tc.formvalue('propertyform', fieldname, str(value))
    
    def edit_ticket(self, ticket_id, **kwargs):
        """A very simple method for changing properties in a ticket. Probably
        it does not handle all cases but it was sufficient for me in the first
        place."""
        self.go_to_view_ticket_page(ticket_id)
        for fieldname in kwargs:
            self._set_ticket_formfield(fieldname, kwargs[fieldname])
        tc.submit('submit')
        tc.code(200)
    
    def _get_alias_name(self, ticket_type):
        """Get the alias from AgiloConfig"""
        config = AgiloConfig(self.env)
        config.reload() # Needed cause the config is changed on the server
        alias = config.ALIASES.get(ticket_type)
        if alias is None:
            # Not asserting as we do not know if the call needs an alias, it
            # might be that the None is an acceptable result to check the 
            # existance of a real alias
            print "\nWARNING: No Alias found for type: %s, %s" % \
                (ticket_type, config.ALIASES)
        return alias
    
    def go_to_new_ticket_page(self, ticket_type, should_fail=False):
        page_url = self.url + "/newticket"
        fail = False
        # remember that types key for agilo must be lowercase, even if Trac
        # allows uppercase type, in the DB, agilo needs to store configuration
        # for them in the config file, and there only lowercase is allowed.
        tc.go(page_url + "?type=" + ticket_type)
        if not should_fail:
            tc.url(page_url + "\?type=" + ticket_type)
        alias_name = self._get_alias_name(ticket_type)
        if should_fail:
            tc.notfind("Create New %s" % alias_name)
            # Tell the caller that we failed
            fail = True
        else:
            tc.find("Create New %s" % alias_name)
        # Inform the caller what happen with the failure
        return should_fail and fail
    
    def go_to_team_overview_page(self, team_name):
        return TeamOverviewPageTester(self, team_name).go()
    
    def go_to_team_sprint_detail_page(self, team_name, sprint_name):
        return TeamSprintDetailTester(self, team_name, sprint_name).go()
    
    def go_to_team_page(self, team_name=None, sprint_name=None):
        page_url = self.url + TEAM_URL
        if team_name is not None:
            page_url += '/%s' % unicode_quote(team_name)
            if sprint_name is not None:
                page_url += '/%s' % unicode_quote(sprint_name)
        tc.go(page_url)
        tc.code(200)
    
    def get_position_in_backlog(self, ticket_id, backlog_name, scope=None):
        """Returns the position of the ticket with the given id in the given
        backlog"""
        from agilo.scrum.backlog import BacklogController
        get_backlog = BacklogController.GetBacklogCommand(self.env,
                                                          name=backlog_name,
                                                          scope=scope,
                                                          reload=True)
        backlog = BacklogController(self.env).process_command(get_backlog)
        if backlog and backlog.exists:
            return backlog.get_pos_of_ticket(ticket_id)
    
    def get_form_field_value(self, form_name, field_name):
        """
        Returns the value set in the given form field. Raises twill
        exceptions if the form or the field are not existing
        """
        value = None
        brw = tc.get_browser()
        form = brw.get_form(form_name)
        if form is not None:
            try:
                value = form[field_name]
            except KeyError:
                print "Form (%s) has no field: %s" % (form.name, field_name)
        return value
    
    def create_new_agilo_ticket(self, ticket_type, summary, description=None, 
                                should_fail=False, referenced=False,
                                restrict_owner=False, show_form=False,
                                link=None, **kwargs):
        if not referenced:
            if link is not None:
                self.go_to_view_ticket_page(link)
                link = self._find_reference_creation_link(tc.showlinks(), 
                                                          ticket_type)
                tc.go(link.url)
            else:
                if self.go_to_new_ticket_page(ticket_type, should_fail):
                    # it properly already failed :-)
                    return
        if description == None:
            description = random_page()
        tc.formvalue('propertyform', 'summary', summary)
        tc.formvalue('propertyform', 'field-description', description)
        
        for key, value in kwargs.items():
            tc.formvalue('propertyform', 'field-' + str(key), str(value))
        
        if show_form:
            print_form(1, tc.get_browser().get_form('propertyform'), None)
        # Submit the form
        tc.submit('submit')
        if not should_fail:
            try:
                tc.code(200)
                if referenced or link:
                    # The ticket id in the URL is the one of the
                    # referencing ticket, so we should find the link
                    # of the newly created one, cause we are in the
                    # edit page of the linking ticket now
                    self.ticketcount = self.get_ticket_id_from_link(summary)
                    assert self.ticketcount is not None, \
                        "Linked Ticket was not created"
                else:
                    self.ticketcount = \
                        self.get_ticket_id_from_url(tc.get_browser().get_url())
                    assert self.ticketcount is not None, "Ticket was not created"
                    tc.url(self.ticket_url(self.ticketcount, edit=False))
            
            except TwillAssertionError, e:
                filename = twill_write_html()
                args = e.args + (filename,)
                raise TwillAssertionError(*args)
        else:
            # Behavior is changed, now the new ticket redirects to the first 
            # available type that can be created by the logged in user.
            tc.url(self.url + '/newticket')
        # If should fail we return Nothing, or the last valid ticket will be 
        # returned
        if not should_fail:
            return self.ticketcount
    
    def get_ticket_id_from_url(self, url):
        """Extract the ticket ID from the given ticket url"""
        re_id = re.compile(r'/ticket/(?P<id>[0-9]+)')
        m = re_id.search(url)
        if m:
            return int(m.group('id'))
        # Print the url for debugging if there is not ticket number
        raise TwillAssertionError("No ticket id found in: %s" % url)
    
    def get_ticket_id_from_link(self, summary):
        """Extract the ticket ID from a link into a ticket edit page
        given the corresponding ticket summary"""
        re_id = re.compile(r'>#(?P<id>[0-9]+)</a>\):\s*(?=%s)' % \
                           summary, re.MULTILINE)
        m = re_id.search(tc.show())
        if m:
            return int(m.group('id'))
        # Print the page for debugging if there is no ticket id
        raise TwillAssertionError("No ticket id found matching " + \
                                  "summary: %s" % summary)
        
    def get_user_name_of_current_user(self):
        '''Return the user name of the user currently logged in or None if no
        user is logged in.'''
        contents = tc.show()
        match = re.search('ogged in as (.*?)</li>', contents)
        if match is None:
            return None
        return match.group(1)
    
    def get_time_of_last_change(self, ticket_id):
        self.go_to_view_ticket_page(ticket_id)
        browser = tc.get_browser()
        form = browser.get_form('propertyform')
        from agilo.ticket import AgiloTicketSystem
        if AgiloTicketSystem.is_trac_1_0():
            ts = browser.get_form_field(form, 'view_time')
        else:
            ts = browser.get_form_field(form, 'ts')
        return ts.value
    
    def get_reporter_of_ticket(self, ticket_id):
        '''Return the user name of the user who reported the ticket in the first
        place.'''
        # deprecated!
        return TicketViewPageTester(self, ticket_id).reporter()
    
    def get_owner_of_ticket(self, ticket_id):
        # deprecated!
        return TicketViewPageTester(self, ticket_id).owner()
    
    def get_status_of_ticket(self, ticket_id):
        # deprecated!
        return TicketViewPageTester(self, ticket_id).status()
    
    def get_privileges_for_user(self, username):
        tc.go(self.url + '/admin/general/perm')
        html = tc.show()
        match = re.search('<tr.*?<td>' + username + '</td>(.*?)</tr>', html, re.DOTALL)
        if match is None:
            return []
        permission_html = match.group(1)
        from agilo.ticket import AgiloTicketSystem
        if AgiloTicketSystem.is_trac_1_0():
            label_re = '<label>.*/>(.*)</label>'
        else:
            label_re = '<label[^/]*?>(\w+)</label>'
        return "".join(re.findall(label_re, permission_html, re.S)).split()

    # overriding method from trac's FunctionalTester because it uses the search
    # box which is hidden in agilo
    def go_to_ticket(self, ticketid):
        return self.go_to_view_ticket_page(ticketid, should_fail=False)
    
    def go_to_view_ticket_page(self, ticket_id, should_fail=False):
        page_url = self.ticket_url(ticket_id, edit=False)
        tc.go(page_url)
        tc.url(page_url)
        if not should_fail:
            tc.code(200)
            tc.find(' #%d' % ticket_id)
        return page_url
    
    def ticket_url(self, ticket_id, edit=False):
        page_url = self.url + '/ticket/%d' % ticket_id
        if edit:
            page_url += '?pane=edit'
        return page_url

    def go_to_team_member_admin_page(self, team_member_name, team_name):
        return TeamMemberAdminPageTester(self, team_member_name, team_name).go()
        
    # Uses the non-admin page, if you create a method for the admin page, use
    # this name 'go_to_sprint_edit_admin_page'
    def go_to_sprint_edit_page(self, sprint_name):
        return SprintEditPageTester(self, sprint_name).go()
    
    def browser_shows_ticket_edit_page(self, ticket_id):
        try:
            tc.code(200)
            tc.find(' #%d' % ticket_id)
            page_url_with_arguments = self.ticket_url(ticket_id, edit=True)
            b = tc.get_browser()
            return (b.get_url() == page_url_with_arguments)
        except TwillAssertionError:
            pass
        return False
    
    def _find_reference_creation_link(self, links, ticket_type):
        expected_link_text = "Create a new referenced '%s'" % self._get_alias_name(ticket_type)
        for link in links:
            if link.text.lower() == expected_link_text.lower():
                return link
        error_msg = 'No creation link found!'
        # use tc.find so that the html page will be saved but 'assert False'
        # as a save guard in case error_msg will be present just by chance.
        tc.find(error_msg)
        assert False, error_msg
    
    def create_referenced_ticket(self, referenced_id, ticket_type, 
                                 summary, **kwargs):
        self.go_to_view_ticket_page(referenced_id)
        link = self._find_reference_creation_link(tc.showlinks(), 
                                                  ticket_type)
        tc.go(link.url)
        return self.create_new_agilo_ticket(ticket_type=ticket_type, 
                                            summary=summary, 
                                            referenced=True, 
                                            **kwargs)
    
    # OVERRIDE: we have to override the standard method to check
    # before the milestone creation or the standard method will break
    # in case the milestone already exists. We have to check here
    # cause we can't predict the order in which the tests will be 
    # called. You need to be Admin to enter here.
    def create_milestone(self, name=None, due=None):
        """Creates the specified milestone. Returns the name of the
        milestone.
        """
        if name:
            admin_milestone = '/admin/ticket/milestones'
            tc.go(self.url + admin_milestone)
            html_page = tc.show()
            regex = re.compile(">%s</a>" % name, re.MULTILINE)
            if regex.search(html_page):
                # already there, just return the name
                return name
        return super(AgiloTester, self).create_milestone(name, due)
    
    def create_sprint_via_admin(self, name, start=None, duration=None, end=None, 
                                milestone=None, team=None, tz=None):
        '''Adds a new sprint'''
        page_url = self.url + '/admin/agilo/sprints'
        tc.go(page_url)
        # fill form
        tc.fv('addsprint', 'name', name)
        if start is None:
            start = now()
        if duration is None and end is None:
            duration = '10'
        tc.fv('addsprint', 'start', format_datetime(start, tzinfo=tz))
        if duration:
            tc.fv('addsprint', 'duration', str(duration))
        if end:
            tc.fv('addsprint', 'end', format_datetime(end, tzinfo=tz))
        if milestone:
            tc.formvalue('addsprint', 'milestone', milestone)
        tc.submit()
        tc.code(200)
        # add redirects to list view, new sprint should be in there
        tc.find(name)
        if team:
            # we can't use follow until the whiteboard link is dynamic
            # otherwise twill will pick up the link to the whiteboard!
            # tc.follow(name)
            sprint_detail_url = page_url + '/' + unicode_quote(name)
            tc.go(sprint_detail_url)
            tc.formvalue('modcomp', 'team', '+%s' % team)
            tc.submit('save')
            tc.url(page_url)
            # see above
            # tc.follow(name)
            tc.go(sprint_detail_url)
            tc.find('<option selected="selected">\s*%s\s*</option>' % team, flags='ms')
    
    # REFACT! split in create_team and create_milestone
    def create_sprint_with_team(self, sprint_name, team_name=None, **kwargs):
        current_user = self.current_user
        self.login_as(Usernames.admin)
        milestone_name = self.create_milestone('MilestoneFor' + sprint_name)
        if not team_name:
            team_name = 'TeamFor' + sprint_name
        self.create_new_team(team_name)
        self.add_member_to_team(team_name, team_name + 'Member')
        self.login_as(Usernames.product_owner)
        self.create_sprint_for_milestone(milestone_name, sprint_name, 
                                         team=team_name, **kwargs)
        if current_user is not None:
            self.login_as(current_user)
        return sprint_name
    
    def create_sprint_for_milestone(self, milestone_name, sprint_name, start=None, 
                                    duration=None, end=None, team=None):
        "Adds a new sprint for a milestone (through the normal user interface)"
        page_url = self.url + '/roadmap'
        tc.go(page_url)
        tc.code(200)
        
        if start is None:
            start = today()
        if duration is None and end is None:
            duration = '10'
        # Formname for Sprint adding
        form_name = 'addnew_%s' % milestone_name.replace(' ', '_')
        tc.formvalue(form_name, 'add', 'click')
        tc.submit('add')
        tc.url(self.url + SPRINT_URL)
        tc.find("New Sprint for milestone %s" % milestone_name)
        
        tc.formvalue('editform', 'name', sprint_name)
        tc.formvalue('editform', 'start', format_date(date_to_datetime(start)))
        if end:
            tc.formvalue('editform', 'end', format_date(date_to_datetime(end)))
        if duration:
            tc.formvalue('editform', 'duration', str(duration))
        if team:
            tc.formvalue('editform', 'team', "+%s" % team)
        tc.submit("save")
        tc.code(200)
        tc.notfind("Warning: ")
        tc.url(self.url + SPRINT_URL + "/" + unicode_quote(sprint_name))
        tc.notfind("Trac Error")
    
    def link_tickets(self, source_id, target_id):
        self.go_to_view_ticket_page(source_id)
        tc.formvalue('create_link', 'dest', str(target_id))
        tc.submit('cmd')
        tc.code(200)
    
    # ------------------------------------------------------------------------
    # Copied from trac's FunctionalTester but with the ability to specify a 
    # password
    def login(self, username, password=None, should_fail=False):
        """Login as the given user"""
        # When we use twill for different hosts, we need to reset the cookies -
        # otherwise twill does not honor the cookie expiry from trac and 
        # continues to send the old cookie.
        tc.clear_cookies()
        tc.add_auth("", self.url, username, password or username)
        self.go_to_front()
        tc.find("Login")
        tc.follow("Login")
        if not should_fail:
            # We've provided authentication info earlier, so this should
            # redirect back to the base url.
            tc.find("ogged in as %s" % username)
            tc.find("Logout")
            tc.url(self.url)
        else:
            tc.notfind("ogged in as %s" % username)
            tc.notfind("Logout")
            tc.find("Login")
        from trac.tests.functional import internal_error
        tc.notfind(internal_error)
    # -------------------------------------------------------------------------
    
    
    def login_as(self, user_name, password=None, should_fail=False):
        # REFACT? return if already logged in correctly
        self.logout()
        self.login(user_name, password=password, should_fail=should_fail)
        self.current_user = user_name
    
    def logout(self):
        # We need to go to a known page where the logout link is present. Maybe 
        # the last test displayed some non-html data (e.g. CSV export) before
        # so we won't find a logout link on the current page.
        self.go_to_front()
        try:
            super(AgiloTester, self).logout()
        except (TwillAssertionError, BrowserStateError):
            pass
        tc.notfind("Logged in as")
        self.current_user = None
    
    def modify_custom_field(self, fieldname, **kwargs):
        page_url = self.url + '/admin/agilo/fields/%s' % unicode_quote(fieldname)
        tc.go(page_url)
        tc.url(page_url)
        tc.code(200)
        
        tc.find(fieldname)
        for key in kwargs:
            tc.formvalue('addcf', key, kwargs[key])
        tc.submit('save')
        tc.code(200)
    
    def go_to_sprint_backlog(self, sprint):
        url_template = '%(prefix)s/%(backlog)s?bscope=%(scope)s'
        backlog_path = url_template % dict(prefix=unicode_quote(BACKLOG_URL),
                                           backlog=unicode_quote('Sprint Backlog'),
                                           scope=unicode_quote(sprint))
        url = self.url + backlog_path
        tc.go(url)
        tc.code(200)
    
    def go_to_product_backlog(self):
        url_template = '%(prefix)s/%(backlog)s'
        backlog_path = url_template % dict(prefix=BACKLOG_URL, backlog='Product Backlog')
        url = self.url + unicode_quote(backlog_path)
        tc.go(url)
        tc.url(url)
        tc.code(200)
    
    def navigate_to_ticket_page(self, ticket_id):
        return TicketViewPageTester(self, ticket_id).go()
    
    def perform_import(self, csv_data, encoding='UTF-8', expected_tickets=None):
        '''Performs the import for the specified data. Afterwards the tickets
        should be created. 
        If expected ticket is given (list of tupels (summary, type)), the tester
        will check after import that these tickets appear in the result html
        and are really in the database by visiting the ticket pages.
        Return a list of 4-tupels [(ticket_id, summary, type, state] with the
        created tickets.'''
        self.upload_csv_for_import(csv_data, encoding)
        tc.find('<h1>Import Preview</h1>')
        tc.notfind('<strong>Warning:</strong>')
        
        # Select one form for twill
        tc.formvalue('import', 'perform_action', '1')
        tc.submit('Import')
        
        tc.find('Imported Tickets')
        tc.notfind('<input type="submit" value="Preview" />')
        tc.notfind('<input type="submit" name="cancel" value="Cancel" />')
        
        changed_tickets = self._get_changed_tickets_from_import_success_page()
        if expected_tickets is not None:
            assert len(expected_tickets) == len(changed_tickets), "%s != %s" % \
                        (len(expected_tickets), len(changed_tickets))
            for expected_ticket, hit in zip(expected_tickets, changed_tickets):
                ticket_id = hit[0]
                summary = hit[1]
                type = hit[2]
                assert expected_ticket[0].encode("UTF-8") == summary
                assert expected_ticket[1] == type
                self.go_to_view_ticket_page(ticket_id)
                tc.find(summary)
        return changed_tickets
    
    def set_option(self, section, option, value):
        config = AgiloConfig(self.env)
        config.change_option(option, value, section)
        config.save()
    
    def set_default_ticket_type(self, new_default_type):
        """Sets a new default ticket type and returns the old one. The user
        currently logged in needs to be TRAC_ADMIN"""
        agilo_config = AgiloConfig(self.env)
        old_default_type = agilo_config.get('default_type', 'ticket')
        
        tc.go('/admin/ticket/type')
        tc.formvalue('enumtable', 'default', new_default_type)
        tc.submit('apply')
        tc.code(200)
        return old_default_type
    
    def set_timezone_for_current_user(self, tz_name):
        tc.go('/prefs/datetime')
        tc.code(200)
        tc.formvalue('userprefs', 'tz', '+'+tz_name)
        tc.submit()
        tc.code(200)
    
    def show_type_in_backlog(self, backlog_name, new_type):
        backlog_admin_url = self.url + '/admin/agilo/backlogs'
        tc.go(backlog_admin_url)
        tc.follow(backlog_name)
        tc.formvalue('modcomp', 'ticket_types', '+%s' % new_type)
        tc.submit('save')
    
    def select_form_for_twill(self, formname, submit_button_name):
        """Select a form so that you can submit it later without changing any 
        form field. This method does not submit the form."""
        browser = twill.get_browser()
        form = browser.get_form(formname)
        control = browser.get_form_field(form, submit_button_name)
        browser.clicked(form, control)
    
    def go_to_import_page(self, action_name='do_import'):
        tc.go('%s?%s=1' % (IMPORT_URL, action_name))
        tc.notfind('<strong>Warning:</strong>')
    
    def build_csv_for_ticket_deletion_from(self, ticket_info):
        csv_fp = StringIO()
        writer = UnicodeCSVWriter(csv_fp)
        writer.writerow((Key.ID, Key.SUMMARY))
        for (ticket_id, summary, type, state) in ticket_info:
            writer.writerow((ticket_id, summary))
        csv_fp.seek(0)
        csv_delete_data = csv_fp.read().decode('UTF-8')
        return csv_delete_data
    
    def upload_csv_for_delete_import(self, csv_data, file_encoding='UTF-8'):
        self.go_to_import_page(ImportParameter.DO_DELETE)
        tc.find('<h1>Delete Existing Tickets from CSV</h1>')
        tc.find('type="submit" value="Preview"')
        encoding = self._upload_csv_data(csv_data, file_encoding)
        return encoding
    
    def upload_csv_for_update_import(self, csv_data, file_encoding='UTF-8'):
        self.go_to_import_page(ImportParameter.DO_UPDATE)
        tc.find('<h1>Update Existing Tickets from CSV</h1>')
        tc.find('type="submit" value="Preview"')
        encoding = self._upload_csv_data(csv_data, file_encoding)
        return encoding
    
    def _upload_csv_data(self, csv_data, file_encoding=None):
        '''Return the encoding used for the file upload'''
        bytestring = csv_data
        if hasattr(csv_data, 'encode') and file_encoding is not None:
            bytestring = csv_data.encode(file_encoding)
        upload_file = StringIO(bytestring)
        tc.formfile('import', 'attachment', 'dummy_filename', fp=upload_file)
        tc.submit()
        return file_encoding
    
    def upload_csv_for_import(self, csv_data, file_encoding='UTF-8'):
        self.go_to_import_page(ImportParameter.DO_IMPORT)
        tc.find('<h1>Import New Tickets from CSV</h1>')
        self._upload_csv_data(csv_data, file_encoding)
    
    def _get_changed_tickets_from_import_success_page(self, expect_valid_links=True):
        html = tc.show()
        
        if expect_valid_links:
            regex = re.compile('href="/ticket/(\d+)"(?: title="(\w+): (.*?) \((\w+)\)")?(?: rel="nofollow")?>#\\1</a> (.*?)\s</li>', re.MULTILINE)
        else:
            regex = re.compile('<a class="missing ticket">#(\d+)</a> (.*?)\s</li>')
            # trac 0.11.1 did used a different 
            if len(regex.findall(html)) == 0:
                regex = re.compile('href="/ticket/\d+"(?: title="\w+: .*? \(\w+\)")?(?: rel="nofollow")?>#(\d+)</a> (.*?)\s</li>', re.MULTILINE)
        
        matches = regex.findall(html)
        changed_tickets = []
        for match in matches:
            new_ticket_id = int(match[0])
            self.ticketcount = max(self.ticketcount, new_ticket_id)
            ticket_type = expect_valid_links and match[1] or None
            ticket_title = expect_valid_links and match[2] or match[1]
            ticket_status = expect_valid_links and match[3] or None
            hit = (new_ticket_id, ticket_title, ticket_type, ticket_status)
            changed_tickets.append(hit)
        return changed_tickets
    
    def _walk_through_preview_and_get_imported_tickets(self, expected_heading, expected_action, force=False, delete_tickets=False):
        # force encoding
        tc.formvalue('import_preview', 'file_encoding', 'UTF-8')
        tc.submit('Preview')
        tc.code(200)
        
        tc.formvalue('import', 'file_encoding', 'UTF-8')
        if force:
            tc.formvalue('import', 'force', 'on')
        tc.submit(expected_action)
        
        tc.find(expected_heading)
        tc.notfind('<input type="submit" value="Preview" />')
        tc.notfind('<input type="submit" name="cancel" value="Cancel" />')
        changed_tickets = self._get_changed_tickets_from_import_success_page(expect_valid_links=not delete_tickets)
        return changed_tickets
    
    def perform_ticket_deletion_through_csv_upload(self, ticket_info, force=False):
        csv_delete_data = self.build_csv_for_ticket_deletion_from(ticket_info)
        self.upload_csv_for_delete_import(csv_delete_data)
        return self._walk_through_preview_and_get_imported_tickets('Deleted Tickets', 'Delete', force=force, delete_tickets=True)
    
    def perform_ticket_update_through_csv_upload(self, ticket_info):
        csv_delete_data = self.build_csv_for_ticket_deletion_from(ticket_info)
        self.upload_csv_for_update_import(csv_delete_data)
        return self._walk_through_preview_and_get_imported_tickets('Updated Tickets', 'Update')
    
    def change_field_for_type(self, field_name, type_name, show=True):
        page_url = self.url + '/admin/agilo/types/' + unicode_quote(type_name)
        tc.go(page_url)
        tc.url(page_url)
        tc.code(200)
        tc.find('Type:')
        tc.find(type_name)
        tc.find('Alias:')
        
        modifier = show and '+' or '-'
        tc.formvalue('modcomp', 'fields', modifier + field_name)
        tc.submit('save')
        tc.code(200)
    
    def grant_permission(self, username, permission):
        tc.go(self.url + '/admin/general/perm')
        tc.formvalue('addperm', 'gp_subject', username)
        tc.formvalue('addperm', 'action', '+%s' % permission)
        tc.submit('add')
    
    def hide_field_for_type(self, field_name, type_name):
        """Hide the given field for this type (this requires 
        TRAC_ADMIN rights)"""
        return self.change_field_for_type(field_name, type_name, False)
    
    def show_field_for_type(self, field_name, type_name):
        """Make the given field available for this type (this requires 
        TRAC_ADMIN rights)"""
        return self.change_field_for_type(field_name, type_name, True)
    
    def _set_ticket_id_sequence(self, cursor=None, new_value=1):
        """Sets the id sequence of the ticket table back to new value (for 
        databases which use sequences like Postgres and MySQL). It is a noop for
        sqlite.
        new_value is the 'next_value', not the current max id."""
        ticket_table = 'ticket'
        db_type = get_db_type(self.env)
        if not cursor:
            cursor = self.env.get_db_cnx().cursor()
        sql = None
        if db_type == 'postgres':
            sql = "select setval('%s_id_seq', %d, false);" % (ticket_table, new_value)
        elif db_type == 'mysql':
            sql = "alter table %s auto_increment=%s" % (ticket_table, new_value)
        if sql is not None:
            cursor.execute(sql)
        self.ticketcount = new_value
    
    def _reset_id_sequence(self, cursor=None):
        # Most databases have a separate counter for automatically increasing
        # values. We have to reset this counter when we delete all tickets as
        # the code assumes that the next tickets will be created as '0'.
        self._set_ticket_id_sequence(cursor=cursor)
    
    def delete_all_tickets(self):
        """Deletes all the tickets from the given environment"""
        db = self.env.get_db_cnx()
        cursor = db.cursor()
        try:
            cursor.execute("DELETE FROM ticket")
            cursor.execute("DELETE FROM ticket_change")
            cursor.execute("DELETE FROM ticket_custom")
            cursor.execute("DELETE FROM %s" % LINKS_TABLE)
            cursor.execute("DELETE FROM %s" % BACKLOG_TICKET_TABLE)
            self._reset_id_sequence(cursor)
            db.commit()
            self.ticketcount = 0
        except Exception, e:
            db.rollback()
            print "ERROR while deleting tickets: %s" % str(e)
    
    def delete_sprints_and_milestones(self):
        """Deletes the Sprints and the Milestones from the DB"""
        db = self.env.get_db_cnx()
        cursor = db.cursor()
        try:
            cursor.execute("DELETE FROM milestone")
            cursor.execute("DELETE FROM agilo_sprint")
            db.commit()
        except Exception, e:
            db.rollback()
            print "ERROR while deleting tickets: %s" % str(e)
    
