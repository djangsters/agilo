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

import agilo.utils.filterwarnings

from agilo.test import Usernames
from agilo.test.functional import AgiloFunctionalTestCase

from agilo.utils import Key, Type
from agilo.utils.config import  AgiloConfig

class CanReloadBurndownOnFilterChanges(AgiloFunctionalTestCase):
    testtype = 'windmill'
    
    def setUp(self):
        self.super()
        self.tester.login_as(Usernames.admin)
        self.tester.create_sprint_with_team(self.sprint_name())
        self.tester.set_option(AgiloConfig.AGILO_GENERAL, 'backlog_filter_attribute', 'component')
        self.tester.set_option(AgiloConfig.AGILO_GENERAL, 'should_reload_burndown_on_filter_change_when_filtering_by_component', True)
        self.tester.show_field_for_type(Key.COMPONENT, Type.USER_STORY) # might be shown by default!
        self.tester.create_new_agilo_userstory('story', component='component1', sprint=self.sprint_name())
    
    def runTest(self):
        self.windmill_tester.login_as(Usernames.team_member)
        backlog = self.windmill_tester.go_to_new_sprint_backlog()
        
        backlog.click_show_burndown_chart_toggle()
        
        # switch to filtered burndown
        backlog.output_for_js("$('#chart-container').empty()")
        backlog.set_filter_value('component1')
        self.windmill_tester.windmill.waits.forElement(xpath="//*[@id='chart-container']/*[@id='burndownchart']") 
        
        # switch back to unfiltered burndown
        backlog.output_for_js("$('#chart-container').empty()")
        backlog.set_filter_value('')
        self.windmill_tester.windmill.waits.forElement(xpath="//*[@id='chart-container']/*[@id='burndownchart']") 
    


if __name__ == '__main__':
    from agilo.test import run_all_tests
    run_all_tests(__file__)

