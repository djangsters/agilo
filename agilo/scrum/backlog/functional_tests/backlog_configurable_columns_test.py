# -*- encoding: utf-8 -*-
#   Copyright 2009 Agile42 GmbH, Berlin (Germany)
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
#       - Martin Häcker <martin.haecker__at__agile42.com>


from agilo.test import Usernames
from agilo.test.functional import AgiloFunctionalTestCase

from agilo.utils import Key, Type
from agilo.utils.config import AgiloConfig
from agilo.scrum.backlog.backlog_config import BacklogConfiguration

class CanChangeColumnsTest(AgiloFunctionalTestCase):
    
    testtype = 'windmill'
    
    def setUp(self):
        self.super()
        env = self.testenv.get_trac_environment()
        config = BacklogConfiguration(env, Key.PRODUCT_BACKLOG)
        config.backlog_columns = [Key.DESCRIPTION, Key.STATUS]
        config.save()
        
        self.tester.login_as(Usernames.admin)
        ticket_id = self.tester.create_new_agilo_userstory('Story without sprint',  sprint='')
        self.story = self.tester.navigate_to_ticket_page(ticket_id).ticket()
        self.backlog = [self.story]
    
    def runTest(self):
        self.windmill_tester.login_as(Usernames.admin)
        backlog = self.windmill_tester.go_to_new_product_backlog()
        columns = backlog.shown_field_for_ticket(self.story.id)
        self.assertEquals(['id', 'summary', 'description', 'status'], columns)
        self.assertEquals('new', backlog.value_for_ticket_field(self.story.id, 'status'))
    

if __name__ == '__main__':
    from agilo.test import run_all_tests
    run_all_tests(__file__)

