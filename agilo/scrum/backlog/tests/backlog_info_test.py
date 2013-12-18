# -*- encoding: utf-8 -*-
#   Copyright 2008 Agile42 GmbH, Berlin (Germany)
#   Copyright 2011 Agilo Software GmbH All rights reserved
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


import agilo.utils.filterwarnings

from agilo.scrum.backlog.json_ui import BacklogInfoJSONView
from agilo.test import AgiloTestCase, Usernames
from agilo.utils.config import AgiloConfig
from agilo.utils.constants import Key, BacklogType, Action, Role
from agilo.utils.days_time import date_to_datetime, now, today

from datetime import timedelta


class BacklogInfoTest(AgiloTestCase):
    def setUp(self):
        self.super()
        self.req = self.teh.mock_request(username=Usernames.team_member)
        self.json_view = BacklogInfoJSONView(self.env)
    
    def _create_sprint_backlog(self):
        self.sprint_backlog_name = 'Fnord Backlog'
        self.sprint_name = 'Sprint Name'
        self.teh.create_sprint(self.sprint_name)
        return self.teh.create_backlog(self.sprint_backlog_name,
                                       scope=self.sprint_name, b_type=BacklogType.SPRINT)
    
    def backlog_info(self):
        view = BacklogInfoJSONView(self.env)
        return view.backlog_info_for_backlog(self.req, self.backlog)['content']


class CanFetchBacklogInfoTest(BacklogInfoTest):
    
    def test_can_fetch_global_backlog_by_name(self):
        self.global_backlog_name = 'Global Backlog'
        self.teh.create_backlog(self.global_backlog_name)
        
        backlog_info = self.json_view.backlog_info(self.req, Key.GLOBAL, self.global_backlog_name)
        self.assert_not_none(backlog_info)
    
    def test_can_fetch_sprint_backlog(self):
        self._create_sprint_backlog()
        backlog_info = self.json_view.backlog_info(self.req, self.sprint_name, self.sprint_backlog_name)
        self.assert_not_none(backlog_info)
    
    def test_has_sprint_and_name(self):
        backlog = self._create_sprint_backlog()
        backlog_info = self.json_view._backlog_info_content(self.req, backlog)
        self.assert_equals('sprint', backlog_info['type'])
        self.assert_equals(self.sprint_backlog_name, backlog_info['name'])
        self.assert_equals(self.sprint_name, backlog_info['sprint_or_release'])
    
    def test_has_username(self):
        backlog = self.teh.create_backlog()
        req = self.teh.mock_request('fnord_user')
        backlog_info = self.json_view._backlog_info_content(req, backlog)
        self.assert_equals('fnord_user', backlog_info['username'])



class BacklogInfoContainsPermissionsTest(BacklogInfoTest):
    
    def access_rights_for_backlog(self, backlog, req=None):
        if req is None:
            req = self.req
        return self.json_view._backlog_info_content(req, backlog)['access_control']
    
    def permissions_for_backlog(self, backlog, req=None):
        return self.json_view.backlog_info_for_backlog(req or self.req, backlog)['permissions']
    
    def test_can_see_read_only_backlog_if_enough_rights_are_available(self):
        self.teh.grant_permission(Usernames.team_member, Action.BACKLOG_EDIT)
        backlog = self.teh.create_backlog()
        backlog_access = self.access_rights_for_backlog(backlog)
        self.assert_equals('', backlog_access['reason'])
        self.assert_false(backlog_access['is_read_only'])
    
    def test_gets_read_only_backlog_for_ended_sprint(self):
        # ensure it ends before the weekend so the test doesn't fail on mondays...
        sprint_start = date_to_datetime(today() - timedelta(days=4))
        sprint_end = sprint_start + timedelta(days=1)
        sprint = self.teh.create_sprint(name='fnord', start=sprint_start, end=sprint_end)
        self.assert_smaller_than(sprint.end, date_to_datetime(today()))
        backlog = self.teh.create_backlog(scope=sprint.name, b_type=BacklogType.SPRINT)
        backlog_access = self.access_rights_for_backlog(backlog)
        self.assert_true(backlog_access['is_read_only'])
        self.assert_equals('Cannot modify sprints that have ended.', backlog_access['reason'])
    
    def test_gets_read_only_backlog_for_running_sprint_with_too_few_rights(self):
        sprint = self.teh.create_sprint(name='fnord')
        backlog = self.teh.create_backlog(scope=sprint.name, b_type=BacklogType.SPRINT)
        backlog_access = self.access_rights_for_backlog(backlog)
        self.assert_true(backlog_access['is_read_only'])
        self.assert_equals('Not enough permissions to modify this sprint.', backlog_access['reason'])
    
    def test_gets_read_only_backlog_for_global_backlog_with_too_few_rights(self):
        backlog = self.teh.create_backlog()
        backlog_access = self.access_rights_for_backlog(backlog)
        self.assert_true(backlog_access['is_read_only'])
        self.assert_equals('Not enough permissions to modify this backlog.', backlog_access['reason'])
    
    def test_not_read_only_if_sprint_not_started(self):
        self.teh.grant_permission(Usernames.team_member, Action.BACKLOG_EDIT)
        sprint = self.teh.create_sprint(name='fnord', start=date_to_datetime(today() + timedelta(3)))
        backlog = self.teh.create_backlog(scope=sprint.name, b_type=BacklogType.SPRINT)
        backlog_access = self.access_rights_for_backlog(backlog)
        self.assert_false(backlog_access['is_read_only'], backlog_access['reason'])
    
    def test_add_confirm_commitment_for_sprint_backlogs(self):
        team = self.teh.create_team('fnord team')
        sprint = self.teh.create_sprint(name='fnord', start=now(), team=team)
        self.teh.grant_permission(Usernames.team_member, Action.CONFIRM_COMMITMENT)
        
        sprint_backlog = self.teh.create_backlog(scope=sprint.name, b_type=BacklogType.SPRINT)
        permissions = self.permissions_for_backlog(sprint_backlog)
        self.assert_contains('AGILO_CONFIRM_COMMITMENT', permissions)
        
        global_backlog = self.teh.create_backlog_without_tickets('FooBacklog', BacklogType.GLOBAL)
        permissions = self.permissions_for_backlog(global_backlog)
        self.assert_not_contains('AGILO_CONFIRM_COMMITMENT', permissions)


class BacklogInfoContainsConfigurationTest(BacklogInfoTest):
    
    def setUp(self):
        self.super()
        self.backlog = self._create_sprint_backlog()
        self.SHOULD_RELOAD = 'should_reload_burndown_on_filter_change_when_filtering_by_component'
    
    def test_returns_configured_columns(self):
        self.backlog.config.backlog_columns = ['foo:editable', 'bar:editable|baz']
        info = self.json_view._backlog_info_content(self.req, self.backlog)
        self.assert_equals(info['configured_columns']['columns'], ['id', 'summary', 'foo', ['bar', 'baz']])
    
    def test_returns_human_readable_names(self):
        # Still a pretty basic test, but better than nothing
        self.backlog.config.backlog_columns = ['summary:editable', 'sprint:editable', 'roif']
        info = self.json_view._backlog_info_content(self.req, self.backlog)
        
        expected = {
            'id': 'ID', 
            'summary' : 'Summary', 
            'sprint': 'Sprint', 
            'roif': 'Roif'
        }
        self.assert_equals(expected, info['configured_columns']['human_readable_names'])
    
    def test_returns_configured_ticket_type_aliases(self):
        self.env.config.set('agilo-types', 'story.alias', 'Fnord')
        AgiloConfig(self.env).reload()
        info = self.json_view._backlog_info_content(self.req, self.backlog)
        self.assert_equals('Fnord', info['type_aliases']['story'])
    
    def test_returns_no_filtering_setting_when_disabled(self):
        info = self.json_view._backlog_info_content(self.req, self.backlog)
        self.assert_not_contains('should_filter_by_attribute', info.keys())
        self.assert_not_contains(self.SHOULD_RELOAD, info.keys())
    
    def test_returns_filtering_setting(self):
        self.env.config.set('agilo-general', 'backlog_filter_attribute', 'owner')
        info = self.json_view._backlog_info_content(self.req, self.backlog)
        self.assert_contains('should_filter_by_attribute', info.keys())
        self.assert_equals('owner', info['should_filter_by_attribute'])
    
    def test_returns_reload_setting(self):
        self.env.config.set('agilo-general', 'backlog_filter_attribute', 'owner')
        self.env.config.set('agilo-general', self.SHOULD_RELOAD, True)
        info = self.json_view._backlog_info_content(self.req, self.backlog)
        self.assert_contains(self.SHOULD_RELOAD, info.keys())
        self.assert_true(info[self.SHOULD_RELOAD])
    

class BacklogInfoContainsInformationAboutTicketFieldsTest(BacklogInfoTest):
    
    def setUp(self):
        self.super()
        self.sprint = self.teh.create_sprint('fnord', team="fnord")
        self.backlog = self.teh.create_backlog_without_tickets('Foo', BacklogType.SPRINT, scope=self.sprint.name)
    
    def ticket_fields(self):
        return self.backlog_info()['ticket_fields']
    
    def field_with_name(self, fieldname):
        if fieldname not in self.ticket_fields():
            raise AssertionError
        return self.ticket_fields()[fieldname]
    
    def test_contains_field_information(self):
        self.assert_contains('ticket_fields', self.backlog_info())
        self.assert_equals({'type': 'text', 'label': 'Summary'},
                           self.field_with_name(Key.SUMMARY))
        self.assert_dict_contains({'type': 'select', 
                                   'value': '', 'options': [u'component1', u'component2']}, 
                                  self.field_with_name(Key.COMPONENT))
    
    def test_contains_list_of_calculated_properties(self):
        self.assert_contains('total_remaining_time', self.ticket_fields())
        field = self.ticket_fields()['total_remaining_time']
        expected_field = dict(is_calculated=True, type='text', label='Total Remaining Time')
        self.assert_dict_contains(expected_field, field)

    def test_backlog_info_has_owner_as_text_if_restrict_owner_is_not_set(self):
        self.assert_contains('owner', self.ticket_fields())
        owner_field = self.ticket_fields()['owner']
        self.assert_equals("text", owner_field["type"])
        self.assert_not_contains("options", owner_field)

    def _ticket_fields_for_restrict_owner(self):
        self.env.config.set('ticket', 'restrict_owner', 'true')
        AgiloConfig(self.env).reload()
        return self.ticket_fields()

    def test_backlog_info_has_owner_as_select_if_owner_restrict_is_enabled(self):
        ticket_fields = self._ticket_fields_for_restrict_owner()
        self.assert_contains('owner', ticket_fields)
        owner_field = ticket_fields['owner']
        self.assert_equals("select", owner_field["type"])

    def test_global_backlog_info_contains_users_as_options(self):
        self.backlog = self.teh.create_backlog_without_tickets('Global', BacklogType.GLOBAL)
        user_name = "member"
        self.teh.create_member(user_name)
        self.teh.emulate_login(user_name)

        owner_fields = self._ticket_fields_for_restrict_owner()['owner']
        self.assert_contains('options', owner_fields)
        self.assert_contains(user_name, owner_fields['options'])

    def test_sprint_backlog_info_contains_team_members_if_restrict_is_enabled(self):
        team_member_name = "member"
        self.teh.create_member(team_member_name, team=self.sprint.team)
        self.teh.emulate_login(team_member_name)

        owner_fields = self._ticket_fields_for_restrict_owner()['owner']
        self.assert_contains('options', owner_fields)
        self.assert_contains(team_member_name, owner_fields['options'])

    def test_sprint_backlog_info_does_not_contain_others_if_restrict_is_enabled(self):
        other_name = "fnord"
        self.teh.create_member(other_name)
        self.teh.emulate_login(other_name)

        owner_fields = self._ticket_fields_for_restrict_owner()['owner']
        self.assert_contains('options', owner_fields)
        self.assert_not_contains(other_name, owner_fields['options'])

    def test_sprint_backlog_info_invalidates_caches_when_adding_new_members(self):
        previous_owner_fields = self._ticket_fields_for_restrict_owner()['owner']
        team_member_name = "member"
        self.teh.create_member(team_member_name, team=self.sprint.team)
        self.teh.emulate_login(team_member_name)

        owner_fields = self._ticket_fields_for_restrict_owner()['owner']
        self.assert_contains('options', owner_fields)
        self.assert_contains(team_member_name, owner_fields['options'])

