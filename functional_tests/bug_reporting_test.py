#!/usr/bin/env python
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
#   Author: Stefano Rago <stefano.rago_at_agilosoftware.com>
from twill.errors import TwillAssertionError
from agilo.test import Usernames

from agilo.test.functional import AgiloFunctionalTestCase
from trac.tests.functional import tc


class TestBugReporting(AgiloFunctionalTestCase):
    """ Test that when an exception occurs in the Agilo code
        the bug reporting system uses the Agilo bug tracking system
        for reporting the bug instead of the default Trac instance
    """

    def should_be_skipped(self):
        import os
        return ((os.name == 'nt')) or (self.super())


    def runTest(self):
        self.tester.login_as(Usernames.admin)
        tc.go("backlog/Sprint%20Backlog?bscope=non-existing-sprint")
        tc.code(500)
        tc.find("Invalid Sprint name")
        try:
            tc.notfind("trac.edgewall.org/newticket")
        except TwillAssertionError:
            raise Exception("Found a link to the official trac bug tracking platform")

        tc.find("trac-hacks.org/newticket")


if __name__ == '__main__':
    from agilo.test.testfinder import run_all_tests
    run_all_tests(__file__)

