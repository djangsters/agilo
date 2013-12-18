# -*- encoding: utf-8 -*-
#   Copyright 2009 Agile42 GmbH, Berlin (Germany)
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
#   
#   Author: 
#       - Felix Schwarz <felix.schwarz__at__agile42.com>

import agilo.utils.filterwarnings

from trac.web.api import RequestDone

from agilo.scrum.backlog import BacklogController, BacklogJSONView
from agilo.test import AgiloTestCase
from agilo.utils import BacklogType, Key, Role, Type


class CanFetchBacklogWithJSONTest(AgiloTestCase):
    
    def _fetch_json_backlog(self, url):
        view = BacklogJSONView(self.env)
        req = self.teh.mock_request(path_info=url)
        self.assert_true(view.match_request(req))
        self.assert_raises(RequestDone, view.process_request, req)
        self.assert_equals(200, req.response.code)
        self.assert_not_equals('', req.response.body)
        return req.response.body_as_json()
    
    def test_fetch_product_backlog(self):
        story = self.teh.create_ticket(Type.USER_STORY, {Key.SUMMARY: 'A Story'})
        self.assert_equals('', story[Key.MILESTONE])
        self.assert_equals('', story[Key.SPRINT])
        
        json_backlog = self._fetch_json_backlog('/json/backlogs/' + Key.PRODUCT_BACKLOG)
        self.assert_equals(1, len(json_backlog))
        self.assert_equals(story.id, json_backlog[0][Key.ID])
        self.assert_equals(story[Key.SUMMARY], json_backlog[0][Key.SUMMARY])
    
    def _create_new_release_backlog(self):
        controller = BacklogController(self.env)
        cmd = BacklogController.CreateBacklogCommand(self.env, name='Release Backlog', 
                                                     ticket_types=[Type.REQUIREMENT],
                                                     type=BacklogType.MILESTONE)
        controller.process_command(cmd)
    
    def test_fetch_release_backlog(self):
        self._create_new_release_backlog()
        milestone = self.teh.create_milestone('1.0')
        requirement = self.teh.create_ticket(Type.REQUIREMENT, {Key.SUMMARY: 'A Need', Key.MILESTONE: milestone.name})
        
        json_backlog = self._fetch_json_backlog('/json/backlogs/Release Backlog/' + milestone.name)
        self.assert_equals(1, len(json_backlog))
        self.assert_equals(requirement.id, json_backlog[0][Key.ID])
        self.assert_equals(requirement[Key.SUMMARY], json_backlog[0][Key.SUMMARY])
    
    def test_ticket_json_includes_can_edit_key(self):
        self.teh.create_ticket(Type.USER_STORY, {Key.SUMMARY: 'A Story'})
        json_backlog = self._fetch_json_backlog('/json/backlogs/' + Key.PRODUCT_BACKLOG)
        self.assert_false(json_backlog[0]['can_edit'])
        
        # Product backlog: need PO perms
        self.teh.grant_permission('anonymous', Role.PRODUCT_OWNER)
        json_backlog = self._fetch_json_backlog('/json/backlogs/' + Key.PRODUCT_BACKLOG)
        self.assert_true(json_backlog[0]['can_edit'])
    


if __name__ == '__main__':
    from agilo.test.testfinder import run_unit_tests
    run_unit_tests(__file__)
