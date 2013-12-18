# -*- encoding: utf-8 -*-
#   Copyright 2008 Agile42 GmbH, Berlin (Germany)
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

import re
import time
import urllib
import urllib2
from urllib2 import HTTPError

from trac.tests.functional import tc

from agilo.utils import Action, Type
from agilo.test import Usernames
from agilo.test.functional import AgiloFunctionalTestCase

from agilo.test import TestEnvHelper


class TestTeamMemberAcceptsTicket(AgiloFunctionalTestCase):
    def runTest(self):
        self._tester.login_as(Usernames.team_member)
        ticket_id = self._tester.create_new_agilo_task('foo', 'abc')
        self._tester.accept_ticket(ticket_id)


class TestTeamMemberChangesHisTicket(AgiloFunctionalTestCase):
    def runTest(self):
        self._tester.login_as(Usernames.team_member)
        ticket_id = self._tester.create_new_agilo_task('foo', 'abc')
        self._tester.accept_ticket(ticket_id)

        # we must not change the ticket too fast because trac stores the change
        # time only as seconds so we add a small break here.
        time.sleep(1)

        self._tester.go_to_view_ticket_page(ticket_id)
        new_summary = 'really interesting'
        tc.formvalue('propertyform', 'field_summary', new_summary)
        tc.submit('submit')
        tc.find(new_summary)


class TestProductOwnerCreatesRequirement(AgiloFunctionalTestCase):
    def runTest(self):
        self._tester.login_as(Usernames.product_owner)
        ticket_id = self._tester.create_new_agilo_ticket(Type.REQUIREMENT, 'req')
        self._tester.go_to_view_ticket_page(ticket_id)
        new_summary = 'really interesting'
        tc.formvalue('propertyform', 'field_summary', new_summary)
        tc.submit('submit')
        tc.find(new_summary)


class TestTeamMembersCanNotCreateOrEditRequirements(AgiloFunctionalTestCase):
    def runTest(self):
        # Create a requirement as a Product Owner, than test that a Team Member
        # can't edit it
        self._tester.login_as(Usernames.product_owner)
        ticket_id = self._tester.create_new_agilo_ticket(Type.REQUIREMENT, 'req')
        self._tester.login_as(Usernames.team_member)
        self._tester.go_to_view_ticket_page(ticket_id, should_fail=True)
        tc.notfind("#properties")
        tc.find("In order to edit this ticket you need to be either")

        # Now try to create a ticket as well
        ticket_id = self._tester.create_new_agilo_ticket(Type.REQUIREMENT, 'req', should_fail=True)


class TestTeamMembersCanNotEditOthersTasks(AgiloFunctionalTestCase):

    def _get_valid_form_token(self, ticket_id):
        self._tester.go_to_view_ticket_page(ticket_id)
        contents = tc.show()
        match = re.search('name="__FORM_TOKEN" value="(\S+)"', contents)
        assert match != None
        token = match.group(1)
        return token

    def _assert_no_brute_force_ticket_change(self, my_ticket_id, foreign_ticket_id):
        """
        We just try to change the ticket with plain post request so we can
        check that the server really checks the permissions (and does not only
        hide the edit form)
        """
        token = self._get_valid_form_token(my_ticket_id)
        new_summary = 'i should not do this'
        values = {'__FORM_TOKEN': token, 'summary': new_summary, 'pane': 'edit',
                  'field_reporter': Usernames.team_member, 'field_type': Type.TASK,
                  'action': 'leave', 'submit': 'Submit changes'}
        url = '%s/ticket/%d' % (self._tester.url, foreign_ticket_id)
        data = urllib.urlencode(values)
        http_req = urllib2.Request(url, data)
        http_req.add_header('Cookie', 'trac_form_token=%s' % token)

        class MyHTTPRedirectHandler(urllib2.HTTPRedirectHandler):
            def http_error_302(self, req, fp, code, msg, headers):
                # some versions of urllib incorrectly pass through
                # the URL's fragment identifier... this strips it
                headers['location'] = headers['location'].split('#')[0]
                return urllib2.HTTPRedirectHandler.http_error_302(self, req, fp, code, msg, headers)
            http_error_301 = http_error_303 = http_error_307 = http_error_302

        try:
            cookieprocessor = urllib2.HTTPCookieProcessor()
            opener = urllib2.build_opener(MyHTTPRedirectHandler, cookieprocessor)
            urllib2.install_opener(opener)

            http_response = urllib2.urlopen(http_req)
            response_content = http_response.read()
            self.assertFalse(new_summary in response_content)
        except HTTPError, e:
            self.assertEqual(403, e.code)
    
    def runTest(self):
        self._tester.login_as(Usernames.team_member)
        ticket_id = self._tester.create_new_agilo_task('some task')
        self._tester.accept_ticket(ticket_id)
        
        self._tester.login_as(Usernames.second_team_member)
        self._tester.go_to_view_ticket_page(ticket_id, should_fail=True)
        tc.notfind("#properties")
        tc.find("In order to edit this ticket you need to be either")

        second_ticket_id = self._tester.create_new_agilo_task('my task')
        self._assert_no_brute_force_ticket_change(second_ticket_id, ticket_id)


class TestProductOwnerCanNotCreateTasks(AgiloFunctionalTestCase):
    def runTest(self):
        self._tester.login_as(Usernames.product_owner)
        self._tester.create_new_agilo_task('I feel like a dev', should_fail=True)


class TestTeamMemberCanAddComments(AgiloFunctionalTestCase):
    def runTest(self):
        self._tester.login_as(Usernames.product_owner)
        ticket_id = self._tester.create_new_agilo_ticket(Type.REQUIREMENT, 'req')
        
        self._tester.login_as(Usernames.team_member)
        self._tester.add_comment(ticket_id)


class TestUserWithPermissionCanCreateAndEditTicketWithCustomType(AgiloFunctionalTestCase):
    def runTest(self):
        self.tester.login_as(Usernames.admin)
        type_name = 'my_custom_type'
        self.tester.create_new_ticket_type(type_name, alias='My_Custom_Type')
        self.tester.grant_permission(Usernames.product_owner, 'CREATE_MY_CUSTOM_TYPE')
        
        self.tester.login_as(Usernames.product_owner)
        ticket_id = self._tester.create_new_agilo_ticket(type_name, 'foo')
        
        # Check that ticket edit is possible too
        self.tester.login_as(Usernames.team_member)
        self.tester.accept_ticket(ticket_id)


class TestTracAdminCanCreateTicketWithCustomTypeWithoutAdditionalPermission(AgiloFunctionalTestCase):
    def runTest(self):
        self._tester.login_as(Usernames.admin)
        # We need to handle mixed case type names
        # FIXME: (AT) as of now we can not, the key sent to the config of trac
        # will be normalized to lowercase from the ConfigParser of Python, so
        # we can not allow types with camelcase or other things. The solution
        # could be to wrap also the trac type configuration, and replace there
        # before saving in the DB
        type_name = 'really_new_custom_type'
        alias_name = 'Really_New_Custom_Type'
        self._tester.create_new_ticket_type(type_name, alias=alias_name)
        ticket_id = self._tester.create_new_agilo_ticket(type_name, 'foo')
        #assert ticket_id != None
        #self._tester.go_to_view_ticket_page(ticket_id)
        # TODO: See bug #509
        tc.find('%s #%s' % (alias_name, ticket_id))


class TestTracAdminAndScrumMasterCanEditTasksWithoutAdditionalPermissions(AgiloFunctionalTestCase):
    def runTest(self):
        # Create a sprint to generate twill panic on Mac
        env = self.testenv.get_trac_environment()
        teh = TestEnvHelper(env=env, env_key=self.env_key)
        teh.create_sprint("Panic Sprint1")
        teh.create_sprint("Panic Sprint2")
        # Now at least one sprint is there
        self.tester.login_as(Usernames.product_owner)
        st_id = self.tester.create_new_agilo_ticket(Type.USER_STORY, "My Story")
        # Now login as team member and create an associated task to the story
        self.tester.login_as(Usernames.team_member)
        task_id = self.tester.create_referenced_ticket(st_id, Type.TASK, "My Task")
        # Make sure no sprint has been set for this task
        
        task_page = self.tester.navigate_to_ticket_page(task_id)
        self.assertEqual('n.a.', task_page.sprint())
        
        # Now login as admin and edit the ticket
        self.tester.login_as(Usernames.admin)
        self.tester.go_to_view_ticket_page(task_id)
        tc.fv('propertyform', 'field-remaining_time', '12')
        tc.submit('submit')
        task_page = self.tester.navigate_to_ticket_page(task_id)
        self.assertEqual('12.0h', task_page.remaining_time())
        self.assertEqual('n.a.', task_page.sprint())
        
        # Now login as team member and become the owner of the ticket
        self.tester.login_as(Usernames.team_member)
        self.tester.go_to_view_ticket_page(task_id)
        tc.fv('propertyform', 'field-remaining_time', '8')
        tc.fv('propertyform', 'action', 'accept')
        tc.submit('submit')
        
        task_page = self.tester.navigate_to_ticket_page(task_id)
        self.assertEqual('8.0h', task_page.remaining_time())
        self.assertEqual('n.a.', task_page.sprint())
        self.assertEqual(Usernames.team_member, task_page.owner())
        
        # Now the admin should be able to edit the task again
        self.tester.login_as(Usernames.admin)
        self.tester.go_to_view_ticket_page(task_id)
        tc.fv('propertyform', 'field-remaining_time', '9')
        tc.submit('submit')
        task_page = self.tester.navigate_to_ticket_page(task_id)
        self.assertEqual('9.0h', task_page.remaining_time())
        self.assertEqual('n.a.', task_page.sprint())
        
        # The Scrum Master should also be able
        self.tester.login_as(Usernames.scrum_master)
        self.tester.go_to_view_ticket_page(task_id)
        tc.fv('propertyform', 'field-remaining_time', '10')
        tc.submit('submit')
        
        task_page = self.tester.navigate_to_ticket_page(task_id)
        self.assertEqual('10.0h', task_page.remaining_time())
        self.assertEqual('n.a.', task_page.sprint())
        self.assertEqual(Usernames.team_member, task_page.owner())


class TicketAdminCanCreateReferencedTasksForStory(AgiloFunctionalTestCase):
    # This is a regression test for bug #838
    
    def setUp(self):
        super(TicketAdminCanCreateReferencedTasksForStory, self).setUp()
        self.testenv._setup_user(self.username(), [Action.TICKET_ADMIN])
    
    def username(self):
        return self.classname() + 'User'
    
    def runTest(self):
        self.tester.login_as(Usernames.product_owner)
        story_id = self.tester.create_new_agilo_userstory('My Story')
        
        self.tester.login_as(self.username())
        self.tester.create_referenced_ticket(story_id, Type.TASK, 'My Task')


class TicketAdminCanEditUserStories(AgiloFunctionalTestCase):
    
    def setUp(self):
        super(TicketAdminCanEditUserStories, self).setUp()
        self.testenv._setup_user(self.username(), [Action.TICKET_ADMIN])
    
    def username(self):
        return self.classname() + 'User'
    
    def runTest(self):
        self.tester.login_as(Usernames.product_owner)
        story_id = self.tester.create_new_agilo_userstory('My Story')
        
        self.tester.login_as(self.username())
        self.tester.edit_ticket(story_id, summary='Changed Summary')


class TeamMembersCanEditBugs(AgiloFunctionalTestCase):
    
    def runTest(self):
        self._tester.login_as(Usernames.team_member)
        bug_id = self.tester.create_new_agilo_ticket(Type.BUG, 'A nasty bug')
        
        self.tester.edit_ticket(bug_id, summary='double free in foobar.c')
        bug_page = self.tester.navigate_to_ticket_page(bug_id)
        self.assertEqual('double free in foobar.c', bug_page.summary())


if __name__ == '__main__':
    from agilo.test.testfinder import run_all_tests
    run_all_tests(__file__)

