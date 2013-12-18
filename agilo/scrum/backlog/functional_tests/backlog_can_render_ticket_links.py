# -*- encoding: utf-8 -*-
#   Copyright 2012 Agilo Software GmbH All rights reserved
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

from agilo.test import Usernames
from agilo.test.functional import AgiloFunctionalTestCase

class CanRenderTicketLinks(AgiloFunctionalTestCase):
    testtype = 'windmill'
    
    def setUp(self):
        self.super()
        self.tester.delete_all_tickets()
        self.tester.login_as(Usernames.admin)
        self.story = self.create_story("New story")
        self.backlog = [self.story]
    
    def create_story(self, summary):
        ticket_id = self.tester.create_new_agilo_userstory(summary,  sprint='')
        return self.tester.navigate_to_ticket_page(ticket_id).ticket()
    
    def runTest(self):
        self.windmill_tester.login_as(Usernames.product_owner)
        new_backlog = self.windmill_tester.go_to_new_product_backlog()
        new_backlog.assert_shows_only(self.backlog)
        link = new_backlog.output_for_js("$($('#ticketID-%s').children('span').get(0).children[0]).attr('href')" % self.story.id)
        self.windmill.open(url=link)
        self.windmill.asserts.assertNode(jquery=u'("h1:contains(\'#%s\')")[0]' % self.story.id)
        
if __name__ == '__main__':
    from agilo.test import run_all_tests
    run_all_tests(__file__)

