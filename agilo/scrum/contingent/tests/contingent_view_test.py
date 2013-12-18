# -*- encoding: utf-8 -*-
#   Copyright 2011 Agilo Software GmbH, Berlin (Germany)
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

from trac.web.api import RequestDone

from agilo.test import AgiloTestCase
from agilo.utils import Role
from agilo.scrum.contingent.web_ui import AddTimeToContingentView
from agilo.scrum.contingent.model import ContingentModelManager


class CanRenderContingentViewTest(AgiloTestCase):
    
    def setUp(self):
        self.super()
        self.contingent_name = 'fnord'
        self.sprint = self.teh.create_sprint("fnord", team='some team')
        self.teh.add_contingent_to_sprint(self.contingent_name, 3, self.sprint)
        self.teh.grant_permission('anonymous', Role.SCRUM_MASTER)
    
    def _assert_add_one_hour_to_contingent(self):
        add_time_to_contingent_view = AddTimeToContingentView(self.env)
        request_to_add_one_hour = self.teh.mock_request(args= { 'sprint':self.sprint.name, 'col_add_time_fnord': '1'})
        self.assert_raises(RequestDone,
                           lambda: add_time_to_contingent_view.do_post(request_to_add_one_hour))

    
    def test_add_time_to_contingent_smoke_test(self):
        self._assert_add_one_hour_to_contingent()
        # add another hour, so we see a difference between 'amount' style setting
        # versus 'delta' style adding
        self._assert_add_one_hour_to_contingent()
        
        used_up_time = self.teh.used_up_time_in_contingent(self.contingent_name, self.sprint.name)
        self.assert_equals(2, used_up_time)
        
