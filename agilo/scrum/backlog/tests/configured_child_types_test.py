# -*- coding: utf-8 -*-
#   Copyright 2009 Agile42 GmbH
#   Copyright 2011 Agilo Software GmbH All rights reserved
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
# 
# Authors:
#     - Felix Schwarz <felix.schwarz__at__agile42.com>


from trac.util.compat import set

from agilo.scrum.backlog.json_ui import ConfiguredChildTypesView
from agilo.test import AgiloTestCase
from agilo.utils import Action, Key, Role, Type


class ChildBreakDownTest(AgiloTestCase):
    
    def setUp(self):
        self.super()
        self.view = ConfiguredChildTypesView(self.env)
    
    def call_view(self):
        req = self.teh.mock_request()
        return self.view.do_get(req, {})
    
    def configured_links(self):
        return self.call_view()['configured_links_tree']
    
    def permitted_links(self):
        return self.call_view()['permitted_links_tree']
    
    def grant_permission(self, action):
        self.teh.grant_permission('anonymous', action)
    
    def test_list_possible_types(self):
        default_types = set([Type.REQUIREMENT, Type.USER_STORY, Type.TASK, Type.BUG])
        self.assert_equals(default_types, set(self.permitted_links().keys()))
    
    def test_show_possible_children(self):
        self.grant_permission(Action.TRAC_ADMIN)
        link_tree = self.permitted_links()
        self.assert_equals([Type.USER_STORY], link_tree[Type.REQUIREMENT].keys())
        self.assert_equals([Type.TASK], link_tree[Type.USER_STORY].keys())
        self.assert_equals([], link_tree[Type.TASK].keys())
        self.assert_equals([Type.USER_STORY, Type.TASK], link_tree[Type.BUG].keys())
    
    def test_hide_types_which_the_user_may_not_create(self):
        self.grant_permission(Role.TEAM_MEMBER)
        link_tree = self.permitted_links()
        self.assert_equals([], link_tree[Type.REQUIREMENT].keys())
    
    def test_show_attributes_which_should_be_copied_for_referenced_tickets(self):
        self.grant_permission(Role.SCRUM_MASTER)
        link_tree = self.permitted_links()
        self.assert_equals([Type.TASK], link_tree[Type.USER_STORY].keys())
        attributes_to_copy = link_tree[Type.USER_STORY][Type.TASK]
        self.assert_equals(set([Key.SPRINT, Key.OWNER]), set(attributes_to_copy))
    
    def test_complete_linking_tree_also_shows_types_which_the_user_may_not_create(self):
        self.grant_permission(Role.TEAM_MEMBER)
        link_tree = self.configured_links()
        self.assert_equals([Type.USER_STORY], link_tree[Type.REQUIREMENT].keys())


