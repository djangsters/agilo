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
#        - Andrea Tomasini <andrea.tomasini__at__agile42.com>
#        - Felix Schwarz <felix.schwarz__at__agile42.com>
#        - Jonas von Poser <jonas.vonposer__at__agile42.com>

from datetime import timedelta

from trac.util.datefmt import format_datetime
from trac.tests.functional import tc
from agilo.test import Usernames
from agilo.test.functional import AgiloFunctionalTestCase

from agilo.scrum import SPRINT_URL
from agilo.test import TestEnvHelper
from agilo.utils import Key, Type
from agilo.utils.days_time import normalize_date, now


class TestSprint(AgiloFunctionalTestCase):
    
    def _test_roadmap(self):
        # get page for editing requirement ticket type
        self._tester.login_as(Usernames.team_member)
        page_url = self._tester.url + '/roadmap'
        tc.go(page_url)
        tc.url(page_url)
        tc.code(200)
        # page should not enable new sprint functionality...
        tc.notfind('Add new sprint')
        
        # ... except for ScrumMasters
        self._tester.login_as(Usernames.scrum_master)
        tc.go(page_url)
        tc.find('Add new sprint')

        # ... and Product Owners
        self._tester.login_as(Usernames.product_owner)
        tc.go(page_url)
        tc.find('Add new sprint')

    def _create_sprint(self, name, start_date=None, duration=20, team=None):
        """Creates a sprint"""
        page_url = self._tester.url + '/roadmap'
        tc.go(page_url)
        # click "Add new sprint"
        tc.fv('addnew', 'add', 'click')
        tc.submit()
        tc.url(SPRINT_URL)
        tc.fv('editform', 'name', name)
        if not start_date:
            start_date = now() # This is with localtz
        start_date = normalize_date(start_date)
        tc.fv('editform', 'start', format_datetime(start_date))
        tc.fv('editform', 'duration', str(duration))
        if team:
            tc.fv('editform', 'team', team)
        tc.submit('save')
        tc.url('%s/%s' % (SPRINT_URL, name))
        tc.find('"%s"' % name)
        tc.find(r'(%s)' % format_datetime(start_date))
        
    def _add_tickets_to_the_sprint(self, sprint_name):
        """Adds some tickets to the sprint to verify that these tickets are
        retargeted upon closing or deleting the sprint."""
        us1_id = self._tester.create_new_agilo_userstory("Planned User Story", 
                                                          sprint=sprint_name)
        # this shouldn't appear in the count of the retarget tickets
        us2_id = self._tester.create_new_agilo_userstory("Unplanned User Story")
        # this should appear as well, cause it is bound to the story which is 
        # planned
        t1_id = self._tester.create_referenced_ticket(us1_id, Type.TASK, 
                                                      "Unplanned Task")
        t2_id = self._tester.create_referenced_ticket(us1_id, Type.TASK, 
                                                      "Planned Task",
                                                      sprint=sprint_name)
        # return the id of the not planned story and the not planned task
        return us1_id, us2_id, t1_id, t2_id
        
    def add_sprint(self):
        '''Adds new sprints through the roadmap'''
        # We have to create the milestone too
        self._tester.login_as(Usernames.admin)
        milestone_name = 'milestone1'
        self._tester.create_milestone(name=milestone_name)
        # Now login as Scrum Master
        self._tester.login_as(Usernames.scrum_master)
        start = now() - timedelta(days=3)
        self._tester.create_sprint_for_milestone(milestone_name,
                                                 'TestSprint',
                                                 start=start,
                                                 duration='15')
        # add another
        start = start + timedelta(days=15)
        self._tester.create_sprint_for_milestone(milestone_name,
                                                 'TestSprint2',
                                                 start=start,
                                                 duration='15')

    def add_sprint_for_milestone_with_slash_in_name(self):
        '''Adds a new sprint for a milestone with a slash in its name'''
        self._tester.login_as(Usernames.admin)
        milestone_name = 'milestone/test'
        self._tester.create_milestone(name=milestone_name)
        start = now() - timedelta(days=3)
        self._tester.create_sprint_for_milestone(milestone_name,
                                                 'TestSprint',
                                                 start=start,
                                                 duration='15')

    def delete_sprint(self):
        # login as Administrator
        self._tester.login_as(Usernames.admin)
        us1_id, us2_id, t1_id, t2_id = \
            self._add_tickets_to_the_sprint('TestSprint')
        # Now login as Scrum Master
        self._tester.login_as(Usernames.scrum_master)
        
        def _delete_sprint(name, retarget=None, tickets=0):
            page_url = '%s/%s' % (SPRINT_URL, name)
            confirm_url = '%s/%s/confirm' % (SPRINT_URL, name)
            tc.go(page_url)
            tc.fv('confirmform', 'delete', 'click')
            tc.submit()
            # show confirmation form
            tc.url(confirm_url)
            if retarget is not None:
                # should show that some tickets can be re-targeted
                tc.find('Retarget the %s remaining tickets to sprint' % tickets)
                tc.fv('confirmform', 'retarget', retarget)
            tc.fv('confirmform', 'sure', 'click')
            tc.submit('sure')
            # we're back at the roadmap
            tc.code(200)
            tc.url('/roadmap')
        
        # Delete Testsprint with retarget to Testsprint2
        _delete_sprint('TestSprint', 'TestSprint2', tickets=3)
        # the sprint is gone
        tc.notfind('<em>TestSprint</em>')
        tc.find('<em>TestSprint2</em>')
        # Check that retargeted ticket show who did the retargeting
        self._tester.go_to_view_ticket_page(us1_id)
        tc.notfind('ago.* by anonymous')
        tc.find('ago.* by %s' % Usernames.scrum_master)
        # Delete Testsprint with retarget to Testsprint2
        _delete_sprint('TestSprint2')

    def close_sprint(self):
        self._tester.login_as(Usernames.scrum_master)
        env = self._testenv.get_trac_environment()
        teh = TestEnvHelper(env=env, env_key=self.env_key)
        team = teh.create_team('A-Team')
        tm = teh.create_member(name="TeamMember", team=team)
        self._create_sprint('TestSprintClose', team=team.name)
        self._create_sprint('TestSprintClose2', team=team.name)
        # create a ticket
        ticket = teh.create_ticket(Type.TASK, props={Key.SPRINT: 'TestSprintClose',
                                                     Key.OWNER: tm.name})
        self.assertEqual(ticket[Key.SPRINT], 'TestSprintClose')
        
        def _close_sprint(name, retarget=None):
            page_url = '%s/%s' % (SPRINT_URL, name)
            confirm_url = '%s/%s/confirm' % (SPRINT_URL, name)
            tc.go(page_url)
            tc.fv('confirmform', 'close', 'click')
            tc.submit()
            # show confirmation form
            tc.url(confirm_url)
            if retarget is not None:
                # should show that one ticket can be retargeted
                tc.find('Retarget the \d+ remaining tickets to sprint')
                tc.fv('confirmform', 'retarget', retarget)
            tc.fv('confirmform', 'sure', 'click')
            tc.submit('sure')
            
            # we're back at the roadmap
            tc.url('/roadmap')
        
        # Closes Testsprint with retarget to Testsprint2
        _close_sprint('TestSprintClose', 'TestSprintClose2')
        # and the ticket now has a new sprint
        ticket = teh.load_ticket(ticket=ticket)
        self.assertEqual(ticket[Key.SPRINT], 'TestSprintClose2')
        # Check that retargeted ticket show who did the retargeting
        self._tester.go_to_view_ticket_page(ticket.id)
        tc.notfind('ago.* by anonymous')
        tc.find('ago.* by %s' % Usernames.scrum_master)
        
        # Delete Testsprint with retarget to Testsprint2
        _close_sprint('TestSprintClose2')

    def runTest(self):
        self._test_roadmap()
        self.add_sprint()
        self.delete_sprint()
        self.close_sprint()
        self.add_sprint_for_milestone_with_slash_in_name()


class TestCacheIn0112DoesNotHideNewSprints(AgiloFunctionalTestCase):
    """New sprints must appear in the dropdown menu when creating a new task."""
    
    def runTest(self):
        self._tester.login_as(Usernames.admin)
        random_milestone_name = self._tester.create_milestone()
        
        self.tester.login_as(Usernames.scrum_master)
        sprint_name = 'NoCacheProblemsIn0112Sprint'
        start = now() - timedelta(days=3)
        self.tester.create_sprint_for_milestone(random_milestone_name, 
                                                 sprint_name, start, duration=9)
        
        self.tester.login_as(Usernames.team_member)
        task_id = self._tester.create_new_agilo_task('some task', 
                                                     sprint=sprint_name)
        ticket_page = self.tester.navigate_to_ticket_page(task_id)
        self.assertEqual(sprint_name, ticket_page.sprint())


class CanRenameSprints(AgiloFunctionalTestCase):
    def runTest(self):
        self.tester.login_as(Usernames.admin)
        self.tester.create_sprint_with_team(self.sprint_name(), self.team_name())
        
        new_name = 'New' + self.sprint_name()
        page = self.tester.go_to_sprint_edit_page(self.sprint_name())
        page.set_name(new_name)
        page.submit()
        
        self.assert_false(page.has_warnings())
        self.tester.go_to_sprint_edit_page(new_name)



if __name__ == '__main__':
    from agilo.test.testfinder import run_all_tests
    run_all_tests(__file__)

