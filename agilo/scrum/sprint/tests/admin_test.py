# -*- encoding: utf-8 -*-
#   Copyright 2010 Agile42 GmbH, Berlin (Germany)
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
from datetime import timedelta

from trac.util.datefmt import format_date

from agilo.scrum.sprint import Sprint, SprintAdminPanel
from agilo.test import AgiloTestCase
from agilo.utils.days_time import now


class SprintAdminPanelTest(AgiloTestCase):

    def setUp(self):
        self.super()
        self.panel = SprintAdminPanel(self.env)
        self.req = self._request_with_valid_sprint_data()

    def _request_with_valid_sprint_data(self):
        start = format_date(now())
        end = format_date(now() + timedelta(10))
        req = self.teh.mock_request()
        req.args = dict(name=self.sprint_name(), add=True, start=start, end=end, milestone="Test milestone fnord")
        return req

    def _assert_request_contains_warning(self, expected_warning):
        expected_warning = expected_warning.lower()
        actual_warning = "".join(self.req.chrome['warnings']).lower()
        self.assert_contains(expected_warning, actual_warning)

    def _assert_creating_sprint_fails(self):
        self.panel.list_save_view(self.req, 'agilo', 'sprints')
        self.assert_false(Sprint(self.env, name=self.req.args['name']).exists)

    def _assert_creating_sprint_succeeds(self):
        call = lambda: self.panel.list_save_view(self.req, 'agilo', 'sprints')
        expected_target = "/admin/agilo/sprints"
        self.teh.redirect_for_call(self.req, call, assert_expected_target=expected_target)
        sprint = Sprint(self.env, name=self.req.args['name'])
        self.assert_true(sprint.exists)
        return sprint

    def test_do_not_create_sprint_without_name(self):
        self.req.args['name'] = ""
        self.panel.list_save_view(self.req, 'agilo', 'sprints')
        self._assert_request_contains_warning('enter a sprint name')

    def test_do_not_create_sprint_if_already_exists(self):
        call = lambda: self.panel.list_save_view(self.req, 'agilo', 'sprints')
        self._assert_creating_sprint_succeeds()

        expected_target = "/admin/agilo/sprints/" + self.sprint_name()
        self.teh.redirect_for_call(self.req, call, assert_expected_target=expected_target)

    def test_do_not_create_sprint_without_enough_data(self):
        self.req.args['start'] = ""
        self.req.args['end'] = ""
        self.req.args['duration'] = ""
        self._assert_creating_sprint_fails()
        self._assert_request_contains_warning('not enough data')

    def test_do_not_create_sprint_with_start_and_both_end_and_duration(self):
        self.assert_trueish(self.req.args['end'])
        self.req.args['duration'] = "10"
        self._assert_creating_sprint_fails()
        self._assert_request_contains_warning('end date or a duration')

    def test_do_not_create_sprint_with_start_and_no_end_nor_duration(self):
        self.req.args['end'] = ""
        self.req.args['duration'] = ""
        self._assert_creating_sprint_fails()
        self._assert_request_contains_warning('end date or a duration')

    def test_do_not_create_sprint_with_only_end_date(self):
        del self.req.args['start']
        self.assert_trueish(self.req.args['end'])
        self._assert_creating_sprint_fails()
        self._assert_request_contains_warning('start date or a duration')

    def test_do_not_create_sprints_with_slashes_in_name(self):
        self.req.args['name'] = "a/b"
        self._assert_creating_sprint_fails()
        self._assert_request_contains_warning('do not use "/')

    def test_sprint_created_with_start_and_end_has_correct_values(self):
        self.teh.disable_sprint_date_normalization()
        sprint = self._assert_creating_sprint_succeeds()
        self.assert_equals(self.req.args['start'], format_date(sprint.start))
        self.assert_equals(self.req.args['end'], format_date(sprint.end))

    def test_sprint_created_with_milestone(self):
        sprint = self._assert_creating_sprint_succeeds()
        self.assert_equals(self.req.args['milestone'], sprint.milestone)


    def test_can_not_edit_sprint_name_so_it_contains_a_slash(self):
        sprint = self.teh.create_sprint('fnord')
        self.req.args = dict(name='a/b')
        self.panel.detail_save_view(self.req, 'agilo', 'sprints', sprint.name)
        self.assert_false(Sprint(self.env, name='a/b').exists)

