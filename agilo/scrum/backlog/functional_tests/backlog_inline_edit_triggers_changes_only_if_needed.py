# -*- encoding: utf-8 -*-
#   Copyright 2012 Agile42 GmbH, Berlin (Germany)
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

import time

from agilo.test import Usernames
from agilo.test.functional import AgiloFunctionalTestCase
from agilo.utils import Type

class BacklogInlineEditingTriggersChangesOnlyIfNeeded(AgiloFunctionalTestCase):
    testtype = 'windmill'
    
    def setUp(self):
        self.super()
        self.tester.login_as(Usernames.admin)
#        self.tester.create_sprint_with_small_backlog()
        ids = self.tester.create_sprint_with_small_backlog()
        self.story_id = ids[1]
        self.second_task_id = ids[2][1]
        sprint_name = self.tester.testcase.sprint_name()
        #the bug only manifests itself when the ticket doesn't have remaining time set
        self.task_id = self.tester.create_referenced_ticket(self.story_id, Type.TASK, 'Extra Task', sprint=sprint_name)
    
    def runTest(self):
        print self.teh.env.path
        self.windmill_tester.login_as(Usernames.team_member)
        self.windmill_tester.go_to_new_sprint_backlog()
        
        #click the task's summary and click away without typing anything
        self.windmill.click(jquery="('#ticketID-%d .summary')[0]" % self.task_id)
        time.sleep(2)
        self.windmill.execJS(js="$('#ticketID-%d .summary input').blur()" % self.task_id)
        time.sleep(2)
        self.windmill.click(jquery="('#ticketID-%d .id a')[0]" % self.task_id)
        self.assert_equals(self.windmill_tester.output_for_js("$('#changelog h3.change').length"), 0)
        
        self.windmill_tester.go_to_new_sprint_backlog()
        #actually edit the task's summary
        self.windmill.click(jquery="('#ticketID-%d .summary')[0]" % self.task_id)
        time.sleep(2)
        self.windmill.type(text='Modified summary', jquery=u"('#ticketID-%d .summary input')[0]" % self.task_id)
        time.sleep(2)
        self.windmill.execJS(js="$('#ticketID-%d .summary input').blur()" % self.task_id)
        time.sleep(2)
        self.windmill.click(jquery="('#ticketID-%d .id a')[0]" % self.task_id)
        self.assert_equals(self.windmill_tester.output_for_js("$('#changelog h3.change').length"), 1)

if __name__ == '__main__':
    from agilo.test import run_all_tests
    run_all_tests(__file__)

