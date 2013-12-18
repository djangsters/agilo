# -*- encoding: utf-8 -*-
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

from trac.util.datefmt import format_date, timezone, localtz

from agilo.api import ICommand
from agilo.scrum.sprint import Sprint, SprintEditView
from agilo.test import AgiloTestCase, Usernames
from agilo.utils import Action
from agilo.utils.days_time import now
from trac.web.api import RequestDone


class SprintCreationTest(AgiloTestCase):
    
    def setUp(self):
        self.super()
        self.view = SprintEditView(self.env)
        self.teh.grant_permission(Usernames.product_owner, Action.SPRINT_EDIT)
        self.milestone = self.teh.create_milestone('milestone')
    
    def test_can_not_create_sprints_with_slash_in_name(self):
        req = self.teh.mock_request(Usernames.product_owner)
        req.args = dict(add='add', sprint_name='a/b', start=format_date(now()), 
                        duration=10, milestone=self.milestone.name)
        self.assert_raises(ICommand.NotValidError, self.view.do_post, req)
        self.assert_false(Sprint(self.env, name='a/b').exists)
    
    def test_return_error_if_sprint_already_exists(self):
        self.teh.create_sprint('fnord')
        req = self.teh.mock_request(Usernames.product_owner)
        req.args = dict(add='add', sprint_name='fnord', start=format_date(now()), 
                        duration=10, milestone=self.milestone.name)
        self.assert_raises(ICommand.NotValidError, self.view.do_post, req)

    def _assert_prepared_data_contains_time_offset(self, data, timezone_info):
        self.assert_contains("timezone_of_sprint", data)
        hours_offset = timezone_info.utcoffset(now()).seconds / 3600
        self.assert_isinstance(data["timezone_of_sprint"], basestring)
        self.assert_contains(str(hours_offset), data['timezone_of_sprint'])

    def test_can_prepare_human_readable_timezone_for_template_if_using_server_time(self):
        req = self.teh.mock_request(Usernames.product_owner)
        req.tz = localtz

        data = self.view.prepare_data(req)
        self._assert_prepared_data_contains_time_offset(data, localtz)
        self.assert_contains("Default timezone", data['timezone_of_sprint'])

    def test_can_prepare_human_readable_timezone_for_template_if_using_user_time(self):
        req = self.teh.mock_request(Usernames.product_owner)
        sydney_in_winter = timezone("GMT +10:00")
        req.tz = sydney_in_winter

        data = self.view.prepare_data(req)
        self._assert_prepared_data_contains_time_offset(data, sydney_in_winter)

    def test_can_create_sprints_for_milestones_with_slash_in_name(self):
        self.teh.create_milestone("milestone/fnord")
        req = self.teh.mock_request(Usernames.product_owner)

        req.args = dict(add='add', sprint_name='fnord', start=format_date(now()),
                        duration=10, milestone="milestone/fnord")
        self.assert_raises(RequestDone, self.view.do_post, req)


class SprintEditTest(AgiloTestCase):
    
    def setUp(self):
        self.super()
        self.view = SprintEditView(self.env)
        self.teh.grant_permission(Usernames.product_owner, Action.SPRINT_EDIT)
        self.sprint = self.teh.create_sprint('fnord')
    
    def test_can_not_rename_sprints_to_have_slash_in_name(self):
        req = self.teh.mock_request(Usernames.product_owner)
        req.args = dict(edit='edit', save=True, 
                        sprint_name='a/b', 
                        name='fnord',
                        start=format_date(self.sprint.start), 
                        end=format_date(self.sprint.end), 
                        milestone=self.sprint.milestone)
        self.assert_raises(ICommand.NotValidError, self.view.do_post, req)
        self.assert_false(Sprint(self.env, name='a/b').exists)

