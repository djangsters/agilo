# -*- coding: utf-8 -*-

import types

from trac.tests.functional import tc
from trac.util.datefmt import utc
from twill.errors import TwillAssertionError

from agilo.test import Usernames
from agilo.test.functional import AgiloFunctionalTestCase
from agilo.utils import Type
from agilo.utils.config import AgiloConfig
from agilo.utils.days_time import now


def set_config_value(env, name, section, new_value):
    agilo_config = AgiloConfig(env)
    old_value = agilo_config.get(name, section)
    agilo_config.change_option(name, new_value, section=section, save=True)
    return old_value

def set_default_type_option(env, new_value):
    return set_config_value(env, 'default_type', 'ticket', new_value)


class TestAttachmentForNewTickets(AgiloFunctionalTestCase):
    """Test that a user can add a new attachment when filing a new ticket
    (see bug #234)."""
    def runTest(self):
        self._tester.login_as(Usernames.product_owner)
        self._tester.go_to_new_ticket_page(Type.REQUIREMENT)
        tc.find('I have files to attach to this ticket')


class TestAddAttachmentButtonIsVisible(AgiloFunctionalTestCase):
    """Test that the add attachment button is visible on the edit ticket page
    (#894)."""
    def runTest(self):
        self.tester.login_as(Usernames.product_owner)
        requirement_id = self.tester.create_new_agilo_requirement('My Requirement')
        self.tester.go_to_view_ticket_page(requirement_id)
        self.tester.select_form_for_twill('attachfile', 'attachfilebutton')
        tc.submit('attachfile')
        tc.find('Add Attachment to')


class TestNoNewTicketInNavigationBar(AgiloFunctionalTestCase):
    def runTest(self):
        self._tester.go_to_front()
        tc.notfind('New Ticket')


class TestChangeHistoryHeadingVisibleEvenWhenNotLoggedIn(AgiloFunctionalTestCase):
    """Regression test for bug #168: Change history header should be visible
    for anonymous users too"""
    
    def runTest(self):
        self._tester.login_as(Usernames.product_owner)
        ticket_id = self._tester.create_new_agilo_userstory('Foo Bar')
        self._tester.add_comment(ticket_id)
        
        self._tester.go_to_view_ticket_page(ticket_id)
        tc.find('Change History')
        tc.find('Attachments')
        
        self._tester.logout()
        self._tester.go_to_view_ticket_page(ticket_id)
        tc.find('Change History')
        tc.notfind('Attachments')


class TestTicketSummaryIsDisplayedDuringPreview(AgiloFunctionalTestCase):
    """Test that ticket's summary is visible on the preview page"""
    
    def runTest(self):
        # Setting the a default type different from the ticket type to be 
        # created triggered another bug in the preview display...
        self._tester.login_as(Usernames.admin)
        
        self._tester.login_as(Usernames.product_owner)
        title = 'Foo Bar Title'
        ticket_id = self._tester.create_new_agilo_userstory(title)
        self._tester.go_to_view_ticket_page(ticket_id)
        
        new_title = 'bulb'
        tc.formvalue('propertyform', 'summary', new_title)
        tc.submit('preview')
        
        tc.code(200)
        from agilo.ticket.api import AgiloTicketSystem
        if AgiloTicketSystem.is_trac_1_0():
            tc.find('<span[^>]*>%s</span>' % new_title)
        else:
            tc.find('<h2[^>]*>%s</h2>' % new_title)

class TestCommentFormOnEditTicketPageToo(AgiloFunctionalTestCase):
    
    def runTest(self):
        self._tester.login_as(Usernames.product_owner)
        ticket_id = self._tester.create_new_agilo_userstory('Foo Bar')
        self._tester.go_to_view_ticket_page(ticket_id)
        # check that the comment form is on the edit page, too
        tc.formvalue("propertyform", "comment", "foobar")


class TestNewTicketPageDisplaysTypeSpecificFields(AgiloFunctionalTestCase):
    
    def runTest(self):
        # It is important that the new ticket form works even if another default
        # ticket type was set.
        self._tester.login_as(Usernames.admin)
        self._tester.set_default_ticket_type(Type.TASK)
        
        self._tester.login_as(Usernames.product_owner)
        self._tester.go_to_new_ticket_page('requirement')
        tc.formvalue('propertyform', 'field-summary', 'blah')
        # This implicitly checks that the additional fields for 
        # requirements are visible
        tc.formvalue('propertyform', 'field-businessvalue', '+200')
        tc.submit('preview')


class TestDescriptionDiffAndHistoryCanBeDisplayed(AgiloFunctionalTestCase):
    
    def runTest(self):
        '''Checks that a modified description produces a description diff and
        we can look at that diff later as well as the ticket history page.'''
        self._tester.login_as(Usernames.admin)
        ticket_id = self._tester.create_new_agilo_task('Blub', 
                                                       'The boring description')
        self._tester.go_to_view_ticket_page(ticket_id)
        
        tc.formvalue('propertyform', 'field_description', 
                     'A new, exciting description')
        tc.submit('submit')
        
        self._tester.go_to_view_ticket_page(ticket_id)
        tc.follow('diff')
        tc.code(200)
        
        # There seems to be no easyer way to get to the ticket history page
        tc.follow('Ticket History')
        tc.code(200)


class TestNoDoubledSprints(AgiloFunctionalTestCase):
    
    def runTest(self):
        '''Checks that on the ticket edit page, only one empty sprint
        is displayed (bug #273)'''
        self._tester.login_as(Usernames.admin)
        ticket_id = self._tester.create_new_agilo_userstory('Foo Bar')
        self._tester.go_to_view_ticket_page(ticket_id)
        tc.notfind('"field_sprint">\s*<option></option>\s*<option[^>]*></option>')
        
        # create a sprint
        self._tester.create_sprint_via_admin('My Sprint', now(tz=utc), '14')
        # and test again
        self._tester.go_to_view_ticket_page(ticket_id)
        tc.notfind('"field_sprint">\s*<option></option>\s*<option[^>]*></option>')


class TestDeleteTicket(AgiloFunctionalTestCase):
    
    def runTest(self):
        """Tests the ticket delete method"""
        self._tester.login_as(Usernames.admin)
        ticket_id = self._tester.create_new_agilo_userstory('Delete Me')
        self._tester.go_to_view_ticket_page(ticket_id)
        tc.formvalue('propertyform', 'delete', 'click')
        tc.submit('delete')
        self._tester.go_to_view_ticket_page(ticket_id, should_fail=True)
        tc.code(404)
        from agilo.ticket import AgiloTicketSystem
        if AgiloTicketSystem.is_trac_1_0():
            return
        else:
            self._tester._set_ticket_id_sequence(new_value=self._tester.ticketcount)

class TestTicketTypesInNewTicket(AgiloFunctionalTestCase):
    """Tests that the ticket types pulldown menu reflect agilo permission"""
    
    def assertNotFindItem(self, fieldname, value, message):
        try:
            tc.fv('propertyform', fieldname, value)
            self.fail(message)
        except TwillAssertionError, e:
            # AT: looks like after 0.11.4 the Trac guys are wrapping
            # machanize errors into TwillAssertionError
            self.assertTrue('cannot find value/label "%s" in list control' % value in str(e))
        except Exception, e:# ClientForm.ItemNotFoundError:
            # Problem here is twofold:
            # 1. twill ships its own copy of mechanize, hence the exceptions 
            #    raised are not something like ClientForm... but something like
            #    _mechanize_dist.ClientForm.... Unfortunately, in some cases,
            #    normal mechanize Exceptions may be raised.
            # 2. In Python 2.4 the exception 'e' will be an instance, not the 
            #    class itself. 
            if type(e) == types.InstanceType:
                exception_class = e.__class__
            else:
                exception_class = type(e)
            class_str = str(exception_class)
            item_not_found = (class_str.find('ClientForm.ItemNotFoundError') > -1)
            error_msg = "Wrong Exception type: %s, should be: %s" % \
                        (class_str, 'ClientForm.ItemNotFoundError')
            self.assertTrue(item_not_found, error_msg)
    
    def runTest(self):
        # First login as team member, there should be no Requirement but the task
        self._tester.login_as(Usernames.team_member)
        tc.go('/newticket?type=task')
        tc.url(r'(.+)(/newticket\?type=task)')
        error_msg = 'Requirement should not be allowed for team members!'
        self.assertNotFindItem('field-type', 'Requirement', error_msg)
        tc.fv('propertyform', 'field-type', 'Task')
        
        # Now login as PO and the Requirement should be there, but the task not
        self._tester.login_as(Usernames.product_owner)
        tc.go('/newticket?type=requirement')
        tc.url(r'(.+)(/newticket\?type=requirement)')
        error_msg = 'Task should not be allowed for product owner!'
        self.assertNotFindItem('field-type', 'Task', error_msg)
        tc.fv('propertyform', 'field-type', 'Requirement')


class TestTicketsCanBeReopened(AgiloFunctionalTestCase):
    
    def runTest(self):
        """Tests that tickets can be reopened."""
        self._tester.login_as(Usernames.admin)
        ticket_id = self._tester.create_new_agilo_task('Foo', remaining_time='2')
        self._tester.go_to_view_ticket_page(ticket_id)
        tc.formvalue('propertyform', 'action', 'resolve')
        # twill does not find radio buttons by id. 
        tc.formvalue('propertyform', 'action', 'resolve')
        tc.formvalue('propertyform', 'action_resolve_resolve_resolution', 'fixed')
        tc.submit('submit')
        tc.find('(closed)')
        tc.find('0.0h')
        
        self._tester.go_to_view_ticket_page(ticket_id)
        tc.formvalue('propertyform', 'action', 'reopen')
        tc.submit('submit')
        # brackets must be escaped, else they are used to group the regular 
        # expression
        tc.notfind('\(closed\)')


class TestTicketSaveIsNotSettingTypeAgain(AgiloFunctionalTestCase):
    """Test that saving the ticket will not set the type again and write in History
    the type is changed see bug #591"""
    
    def runTest(self):
        self._tester.login_as(Usernames.scrum_master)
        t_id = self._tester.create_new_agilo_task('Type should not be set')
        #Now go to edit page and save.
        self._tester.go_to_view_ticket_page(t_id)
        tc.fv('propertyform', 'submit', 'click')
        tc.submit('submit')
        # Now check that in the view page there is not type set to Task
        tc.notfind("<li>\s*<strong>type</strong>\s*set to\s*<em>Task</em>\s*</li>", 
                   flags='ims')


class TestNewTasksCanBeCreatedEvenIfRestrictOwnerIsUsed(AgiloFunctionalTestCase):
    """Regression test for bug #577: If restrict_owner is enabled, the owner
    field should be a select field prepopulated with the team members."""
    
    def _create_sprint_with_team_and_team_member(self, sprint_name, team_name):
        self._tester.login_as(Usernames.admin)
        self._tester.create_new_team(team_name)
        self._tester.add_member_to_team(team_name, 'RestrictOwnerTeamMember')
        self._tester.create_sprint_via_admin(sprint_name, now(), duration=9, 
                                   team=team_name)
    
    def _set_restrict_owner_option(self, new_value):
        env = self._testenv.get_trac_environment()
        agilo_config = AgiloConfig(env)
        old_value = agilo_config.get_bool('restrict_owner', 'ticket')
        agilo_config.change_option('restrict_owner', new_value, 
                                   section='ticket', save=True)
        return old_value
    
    def runTest(self):
        team_name = 'NewTasksWithRestrictOwnerTeam'
        sprint_name = 'NewTasksWithRestrictOwnerSprint'
        self._set_restrict_owner_option('true')
        self._create_sprint_with_team_and_team_member(sprint_name, team_name)
        self._tester.login_as(Usernames.team_member)
        self._tester.go_to_new_ticket_page(Type.TASK)
        tc.notfind('<input type="text" id="field-owner" name="field_owner"')
        self._tester.create_new_agilo_task('Foo Bar', sprint=sprint_name, 
                                           restrict_owner=True)



class TestOnlyTasksFieldsAreShownInPreview(AgiloFunctionalTestCase):
    """Regression test for bug #611: In the create preview of a Task only the
    fields valid for Tasks must be displayed (even if the ticket type is the
    default type)."""
    
    def runTest(self):
        self._tester.login_as(Usernames.team_member)
        self._tester.go_to_new_ticket_page(Type.TASK)
        tc.formvalue('propertyform', 'summary', 'Foo Summary')
        tc.submit('preview')
        tc.notfind('Business Value Points')
        tc.notfind('User Story Priority')


if __name__ == '__main__':
    from agilo.test.testfinder import run_all_tests
    run_all_tests(__file__)

