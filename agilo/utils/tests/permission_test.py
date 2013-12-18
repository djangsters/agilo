# -*- coding: utf-8 -*-
#   Copyright 2008 Agile42 GmbH - Andrea Tomasini
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
# Authors:
#    - Jonas von Poser <jonas.vonposer@agile42.com>
#    - Felix Schwarz <felix.schwarz__at__agile42.com>


from datetime import timedelta

from trac.perm import PermissionCache, PermissionError, PermissionSystem
from trac.resource import Resource
from trac.ticket.model import Type as TicketType

from agilo.test import AgiloTestCase
from agilo.ticket.web_ui import AgiloTicketModule
from agilo.utils import Action, Type, Key, Role, Realm
from agilo.utils.config import AgiloConfig
from agilo.utils.days_time import now
from agilo.utils.permissions import AgiloPolicy


name_team_member = 'tester'
name_product_owner = 'product owner'

class TestAgiloPermissions(AgiloTestCase):
    
    def setUp(self):
        self.super()
        self.env.config.set('trac', 'permission_policies', 'AgiloPolicy, DefaultPermissionPolicy, LegacyAttachmentPolicy')
        self.perm = PermissionSystem(self.env)
    
    def test_roles(self):
        self.teh.grant_permission('master', 'SCRUM_MASTER')
        self.teh.grant_permission('owner', 'PRODUCT_OWNER')
        
        # test if contains main and sub permission
        # for scrum master
        permissions = self.perm.get_user_permissions('master')
        self.assert_true('SCRUM_MASTER' in permissions)
        self.assert_true(Action.SAVE_REMAINING_TIME in permissions)
        
        # for product owner
        permissions = self.perm.get_user_permissions('owner')
        self.assert_true('PRODUCT_OWNER' in permissions)
        self.assert_true(Action.CREATE_STORY in permissions)
        self.assert_true(Action.CREATE_REQUIREMENT in permissions)
    
    def test_ticket_permissions(self):
        # create user with the necessary permission
        self.teh.grant_permission(name_team_member, Role.TEAM_MEMBER)
        perm_cache = PermissionCache(self.env, name_team_member)
        
        ticket = self.teh.create_ticket(Type.TASK)
        perm_cache(Realm.TICKET, ticket.id).assert_permission(Action.TICKET_EDIT)
        # a team member should be able to save the remaining time for unassigned
        # tickets
        perm_cache(Realm.TICKET, ticket.id).assert_permission(Action.SAVE_REMAINING_TIME)
        
        # Don't change the remaining time for tickets which belong to other 
        # team members
        ticket[Key.OWNER] = "Just another team member"
        ticket.save_changes("foo", "bar")
        
        new_perm_cache = PermissionCache(self.env, name_team_member)
        self.assert_raises(PermissionError,
                          new_perm_cache(Realm.TICKET, ticket.id).assert_permission, 
                          Action.SAVE_REMAINING_TIME)
    
    def test_edit_description_action_is_scoped_as_well(self):
        self.teh.grant_permission(name_team_member, Role.TEAM_MEMBER)
        perm = PermissionCache(self.env, name_team_member)
        requirement = self.teh.create_ticket(Type.REQUIREMENT)
        requirement_resource = requirement.resource
        self.assert_false(perm.has_permission(Action.TICKET_EDIT_DESCRIPTION, requirement_resource))
    
    def test_reporters_can_only_edit_unassigned_tickets(self):
        self.teh.grant_permission(name_team_member, Role.TEAM_MEMBER)
        ticket = self.teh.create_ticket(Type.TASK)
        ticket[Key.REPORTER] = name_team_member
        ticket[Key.OWNER] = None
        some_minutes_ago = now() - timedelta(minutes=2)
        ticket.save_changes("foo", "bar", when=some_minutes_ago)
        self.assert_equals(name_team_member, ticket[Key.REPORTER])
        self.assertNotEqual(name_team_member, ticket[Key.OWNER])
        
        perm_cache = PermissionCache(self.env, name_team_member)
        perm_cache(Realm.TICKET, ticket.id).assert_permission(Action.TICKET_EDIT)
        perm_cache(Realm.TICKET, ticket.id).assert_permission(Action.TICKET_EDIT_PAGE_ACCESS)
    
    def test_ticket_owner_or_resource_can_save_time(self):
        another_team_member = 'another team member'
        self.teh.grant_permission(name_team_member, Role.TEAM_MEMBER)
        self.teh.grant_permission(another_team_member, Role.TEAM_MEMBER)
        ticket = self.teh.create_ticket(Type.TASK, props={Key.OWNER: name_team_member,
                                                          Key.REMAINING_TIME: '12'})
        # Check that name_team_member can change remaining time
        new_perm_cache = PermissionCache(self.env, name_team_member)
        new_perm_cache(Realm.TICKET, ticket.id).assert_permission(Action.SAVE_REMAINING_TIME)
        
        # Check that another_team_member can't change remaining time
        self.assert_true(another_team_member not in ticket.get_resource_list(include_owner=True))
        new_perm_cache = PermissionCache(self.env, another_team_member)
        self.assert_raises(PermissionError,
                          new_perm_cache(Realm.TICKET, ticket.id).assert_permission, 
                          Action.SAVE_REMAINING_TIME)
    
    def test_all_users_in_resources_can_edit_ticket(self):
        ticket = self.teh.create_ticket(Type.TASK)
        ticket[Key.OWNER] = "Just another team member"
        ticket[Key.RESOURCES] = " foo, %s, bar " % name_team_member
        ticket.save_changes("foo", "bar")
        self.teh.grant_permission(name_team_member, Role.TEAM_MEMBER)
        perm_cache = PermissionCache(self.env, name_team_member)
        
        self.assertNotEqual(ticket[Key.OWNER], name_team_member)
        perm_cache(Realm.TICKET, ticket.id).assert_permission(Action.TICKET_EDIT)
    
    def test_attachement_permissions(self):
        # create user with the necessary permission
        self.teh.grant_permission(name_team_member, Role.TEAM_MEMBER)
        self.teh.grant_permission(name_product_owner, Role.PRODUCT_OWNER)
        
        ticket = self.teh.create_ticket(Type.REQUIREMENT)
        # None of the two users we use for testing must be the ticket's owner,
        # else they could always edit the ticket.
        ticket[Key.OWNER] = 'someone'
        ticket.save_changes('foo', 'we have to change the owner')
        
        # a product owner should be able to attach files to the ticket, but a 
        # team member must not
        po_perm_cache = PermissionCache(self.env, name_product_owner)
        self.assert_true(Action.ATTACHMENT_CREATE in po_perm_cache(Realm.TICKET, ticket.id))
        
        tm_perm_cache = PermissionCache(self.env, name_team_member)
        self.assert_raises(PermissionError,
            tm_perm_cache(Realm.TICKET, ticket.id).assert_permission, Action.ATTACHMENT_CREATE)
    
    def test_can_edit_ticket_if_he_can_create_referenced_tickets(self):
        self.teh.grant_permission(name_team_member, Role.TEAM_MEMBER)
        perm_cache = PermissionCache(self.env, name_team_member)
        
        story = self.teh.create_ticket(Type.USER_STORY)
        self.assert_true(perm_cache.has_permission(Action.TICKET_EDIT_PAGE_ACCESS, story.resource))
        self.assert_false(perm_cache.has_permission(Action.TICKET_EDIT, story.resource))
    
    # TODO: self.perm() as replacement for perm_cache...
    
    def _create_custom_ticket_type(self, type_name, field_names):
        custom_type = TicketType(self.env)
        custom_type.name = type_name
        custom_type.insert()
        
        config = AgiloConfig(self.env)
        config.change_option(type_name, field_names, section=AgiloConfig.AGILO_TYPES)
        config.reload()
        self.assert_true(type_name in config.get_available_types())
    
    def test_can_edit_ticket_for_custom_types(self):
        custom_type_name = 'MaintenanceTask'
        self._create_custom_ticket_type(custom_type_name, [Key.COMPONENT])
        permission_name = 'CREATE_' + custom_type_name.upper()
        self.teh.grant_permission(name_team_member, permission_name)
        self.teh.grant_permission(name_team_member, Role.TEAM_MEMBER)
        
        perm_cache = PermissionCache(self.env, name_team_member)
        ticket = self.teh.create_ticket(custom_type_name)
        self.assert_true(perm_cache.has_permission(Action.TICKET_EDIT, ticket.resource))
        self.assert_true(perm_cache.has_permission(Action.TICKET_EDIT_PAGE_ACCESS, ticket.resource))
    
    def test_team_members_can_edit_bugs(self):
        bug = self.teh.create_ticket(Type.BUG, {Key.SUMMARY: 'A bug'})
        self.teh.grant_permission(name_team_member, Role.TEAM_MEMBER)
        
        perm = PermissionCache(self.env, name_team_member)
        self.assert_true(perm.has_permission(Action.TICKET_EDIT, bug.resource))


class TestAgiloTicketModulePermissions(AgiloTestCase):
    """
    Tests the permissions using a Mock HTTP request to mock the behavior of
    the ticket module
    """
    
    def setUp(self):
        """Creates the environment and a couple of tickets"""
        self.super()
        # add agilo policy to policies
        self.env.config.set('trac', 'permission_policies', 'AgiloPolicy, DefaultPermissionPolicy, LegacyAttachmentPolicy')
        # create user with the necessary permission
        self.teh.grant_permission(name_team_member, Role.TEAM_MEMBER)
        self.teh.grant_permission(name_product_owner, Role.PRODUCT_OWNER)
    
    def test_can_edit_ticket_from_ticket_module(self):
        """
        Test the can_edit_ticket method directly on the TicketModule
        using a Mocked Request Object
        """
        task = self.teh.create_ticket(Type.TASK, props={Key.OWNER: name_team_member})
        req = self.teh.mock_request(name_team_member)
        self.assert_true(AgiloTicketModule(self.env).can_edit_ticket(req, task),
                        "No permission to edit: %s as: %s!!!" % (task, req.authname))
        # Now make sure that the product owner can't edit task
        req = self.teh.mock_request(name_product_owner)
        self.assert_false(AgiloTicketModule(self.env).can_edit_ticket(req, task),
                         "Permission to edit: %s as: %s!!!" % (task, req.authname))
        # Now create a Story, both role should be able to edit it
        story = self.teh.create_ticket(Type.USER_STORY, 
                                       props={Key.OWNER: name_product_owner,
                                              Key.STORY_PRIORITY: 'Mandatory'})
        self.assert_true(AgiloTicketModule(self.env).can_edit_ticket(req, story),
                        "No permission to edit: %s as: %s!!!" % (story, req.authname))
        # Now the team member too
        req = self.teh.mock_request(name_team_member)
        self.assert_false(AgiloTicketModule(self.env).can_edit_ticket(req, story))
        # Now a Requirement that should only be touched by the Product Owner
        requirement = self.teh.create_ticket(Type.REQUIREMENT, 
                                             props={Key.OWNER: name_product_owner,
                                                    Key.BUSINESS_VALUE: '2000'})
        self.assert_false(AgiloTicketModule(self.env).can_edit_ticket(req, requirement),
                         "Permission to edit: %s as: %s!!!" % (requirement, req.authname))
        # Now the team member too
        req = self.teh.mock_request(name_product_owner)
        self.assert_true(AgiloTicketModule(self.env).can_edit_ticket(req, requirement),
                        "No permission to edit: %s as: %s!!!" % (requirement, req.authname))
    
    def test_create_related_tickets(self):
        """
        Test the list of possible related ticket to create given a type and
        a login permissions.
        """
        req = self.teh.mock_request(name_product_owner)
        story = self.teh.create_ticket(Type.USER_STORY, 
                                       props={Key.OWNER: name_product_owner,
                                              Key.STORY_PRIORITY: 'Mandatory'})
        # Build a fake data dictionary containing the ticket
        data = {Key.TICKET: story}
        AgiloTicketModule(self.env)._prepare_create_referenced(req, data)
        # Now check that being a Product Owner there is no link to create a task
        self.assert_false(Type.TASK in data['create_referenced'])
        
        # Now login as a team member and the link should be there
        req.perm = PermissionCache(self.env, name_team_member)
        req.authname = name_team_member
        AgiloTicketModule(self.env)._prepare_create_referenced(req, data)
        allowed_links = data['create_referenced']
        allowed_destination_types = [l.dest_type for l in allowed_links]
        self.assert_true(Type.TASK in allowed_destination_types)



class BacklogEditPermissionTest(AgiloTestCase):
    
    def setUp(self):
        self.super()
        self.policy = AgiloPolicy(self.env)
    
    def policy_decision(self, resource=None, username='foo'):
        perm = PermissionCache(self.env, username)
        return self.policy.check_permission(Action.BACKLOG_EDIT, username, resource, perm)
    
    def test_backlog_edit_without_resource_falls_back_to_trac_permissions(self):
        self.assert_none(self.policy_decision(resource=None))
        
        self.teh.grant_permission('foo', Action.BACKLOG_EDIT)
        self.assert_none(self.policy_decision(resource=None))
    
    def test_product_owner_has_backlog_edit_without_resource_because_they_can_potentially_edit_the_product_backlog(self):
        self.teh.grant_permission('foo', Role.PRODUCT_OWNER)
        self.assert_true(self.policy_decision(resource=None))
    
    def test_scrum_master_has_backlog_edit_without_resource_because_they_can_potentially_edit_the_sprint_backlog(self):
        self.teh.grant_permission('foo', Role.SCRUM_MASTER)
        self.assert_true(self.policy_decision(resource=None))
    
    def product_backlog_resource(self):
        return Resource(Realm.BACKLOG, Key.PRODUCT_BACKLOG)
    
    def sprint_backlog_resource(self):
        return Resource(Realm.BACKLOG, Key.SPRINT_BACKLOG)
    
    def other_backlog_resource(self):
        return Resource(Realm.BACKLOG, 'My Own Backlog')
    
    def test_product_owner_can_edit_the_product_backlog(self):
        self.teh.grant_permission('foo', Role.PRODUCT_OWNER)
        
        self.assert_none(self.policy_decision(resource=self.sprint_backlog_resource()))
        self.assert_true(self.policy_decision(resource=self.product_backlog_resource()))
    
    def test_scrum_master_can_edit_the_sprint_backlog(self):
        self.teh.grant_permission('foo', Role.SCRUM_MASTER)
        
        self.assert_none(self.policy_decision(resource=self.product_backlog_resource()))
        self.assert_true(self.policy_decision(resource=self.sprint_backlog_resource()))
    
    def test_all_authenticated_users_can_unknown_backlogs(self):
        self.teh.grant_permission('foo', Role.SCRUM_MASTER)
        
        other_backlog = self.other_backlog_resource()
        self.assert_true(self.policy_decision(resource=other_backlog))
        other_backlog = self.policy_decision(resource=self.other_backlog_resource(), username='anonymous')
        self.assert_none(other_backlog)
    
    def test_no_endless_loop_if_permission_is_checked_with_string_instead_of_resource(self):
        perm = PermissionCache(self.env, 'foo')
        perm.has_permission('AGILO_BACKLOG_EDIT', '%s:Sprint Backlog' % Realm.BACKLOG) 


class ConfirmCommitmentTest(AgiloTestCase):
    
    def setUp(self):
        self.super()
        self.policy = AgiloPolicy(self.env)
    
    def username(self):
        return 'foo'
    
    def policy_decision(self, resource=None, username=None):
        perm = PermissionCache(self.env, username)
        return self.policy.check_permission(Action.CONFIRM_COMMITMENT, username or self.username(), resource, perm)
    
    def test_does_not_care_if_no_resource_given(self):
        self.assert_none(self.policy_decision())
    
    def test_does_not_care_for_invalid_sprint_names(self):
        self.assert_none(self.policy_decision(Resource(Realm.SPRINT, 'invalid')))
    
    def test_sprint_must_have_a_team_assigned(self):
        sprint = self.teh.create_sprint('ConfirmCommitmentSprint')
        self.assert_none(sprint.team)
        
        self.assert_false(self.policy_decision(sprint.resource()))
    
    def test_can_confirm_if_sprint_started_at_most_yesterday(self):
        team = self.teh.create_team('A-Team')
        almost_a_day_ago = now() - timedelta(hours=23)
        sprint = self.teh.create_sprint('Sprint', start=almost_a_day_ago, team=team)
        
        self.assert_none(self.policy_decision(sprint.resource()))
    
    def test_can_not_confirm_if_sprint_started_more_than_one_day_ago(self):
        self.teh.disable_sprint_date_normalization()
        team = self.teh.create_team('A-Team')
        two_days_ago = now() - timedelta(days=2)
        sprint = self.teh.create_sprint('Sprint', start=two_days_ago, team=team)
        
        self.assert_false(self.policy_decision(sprint.resource()))


class ContingentPermissionsTest(AgiloTestCase):
    
    def setUp(self):
        self.super()
        self.policy = AgiloPolicy(self.env)
    
    def username(self):
        return 'foo'
    
    def ask_policy(self, action, resource=None, username=None):
        perm = PermissionCache(self.env, username)
        return self.policy.check_permission(action, username or self.username(), resource, perm)
    
    def assert_permission(self, action, resource=None, username=None):
        self.assert_true()
    
    def assert_no_permission(self, action, resource=None, username=None):
        self.assert_falsish(self.ask_policy(action, resource, username))
    
    def test_contingent_admin_must_be_able_to_add_time(self):
        self.assert_no_permission(Action.CONTINGENT_ADD_TIME)
        self.teh.grant_permission(self.username(), Action.CONTINGENT_ADMIN)
        
        self.assert_none(self.ask_policy(Action.CONTINGENT_ADD_TIME))


if __name__ == '__main__':
    from agilo.test.testfinder import run_unit_tests
    run_unit_tests(__file__)