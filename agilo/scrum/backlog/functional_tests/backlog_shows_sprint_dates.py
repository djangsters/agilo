# -*- encoding: utf-8 -*-
#   Copyright 2013 Agilo Software GmbH All rights reserved
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
#       - Stefano Rago <stefano.rago__at__agilosoftware.com>
#       - Claudio Di Cosmo <claudio.dicosmo__at__agilosoftware.com>

import agilo.utils.filterwarnings

from agilo.test import Usernames
from agilo.utils import Key, Type
from agilo.test.functional import AgiloFunctionalTestCase
from trac.tests.functional import tc

class SprintBacklogShowsSprintDates(AgiloFunctionalTestCase):

    def setUp(self):
        self.super()
        self.tester.login_as(Usernames.admin)
        self.sprint = self.teh.create_sprint(self.sprint_name())

    def runTest(self):
        self.tester.go_to_sprint_backlog(self.sprint_name())
        tc.find(self.sprint.start.strftime("%a %B %d"))
        tc.find(self.sprint.end.strftime("%a %B %d"))

if __name__ == '__main__':
    from agilo.test import run_all_tests
    run_all_tests(__file__)

