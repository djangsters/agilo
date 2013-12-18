# -*- encoding: utf-8 -*-
#   Copyright 2008 Agile42 GmbH, Berlin (Germany)
#   Copyright 2007 Andrea Tomasini <andrea.tomasini_at_agile42.com>
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
#       - Andrea Tomasini <andrea.tomasini__at__agile42.com>

from datetime import datetime

from agilo.test.functional import AgiloFunctionalTestCase

from agilo.utils import BacklogType, Type
from agilo.test import TestEnvHelper

LOAD_TIMES = 3

class TestBacklogPerformance(AgiloFunctionalTestCase):
    """Tests the performance of a Backlog object, purely from a 
    computational point of view"""
    def _load_backlog_with_timing(self, backlog):
        times = []
        for i in range(LOAD_TIMES):
            start = datetime.now()
            backlog.values()
            times.append(datetime.now() - start)
        # calculate the average
        avg = sum([t.microseconds + t.seconds * 1000000 for t in times])/len(times)
        return times, avg

    def _test_global_backlog(self):
        """Test performance in loading and sorting a global Backlog with 100 items"""
        for num_items in [10, 100, 200]:
            backlog_name = "Performance %d" % num_items
            start = datetime.now()
            gb = self.teh.create_backlog(name=backlog_name,
                                         num_of_items=num_items)
            # Load backlog object with scope using BacklogModelManager
            stop = datetime.now()
            load_time = stop - start
            print "First Backlog Load with %d items: %s" % (num_items, load_time)
            actual_times, avg = self._load_backlog_with_timing(gb)
            print "Average load time with %d items: %s (%s)" % (num_items, avg, map(str, actual_times))
            self._tester.delete_all_tickets()
    
    def _test_sprint_backlog(self):
        """Test performance in loading and sorting a global Backlog with 100 items"""
        for num_items in [10, 100, 200]:
            s = self.teh.create_sprint("TestSprint%s" % num_items)
            start = datetime.now()
            sb = self.teh.create_backlog(name="Sprint Backlog %d" % num_items,
                                         ticket_types=[Type.REQUIREMENT, Type.USER_STORY, Type.TASK],
                                         num_of_items=num_items, 
                                         b_type=BacklogType.SPRINT,
                                         scope=s.name)
            #f num_items != sb.count():
                # print the backlog for debugging
                #from agilo.scrum.backlog.tests.backlog_test import print_backlog
                #print_backlog(sb)
            create_time = datetime.now() - start
            print "Created %s ticket in %s sec. (avg: %s)" % (num_items, create_time, create_time/num_items)
            actual_times, avg = self._load_backlog_with_timing(sb)
            print "Average load time with %d items: %s (%s)" % (num_items, avg, map(str, actual_times))
            self._tester.delete_all_tickets()
    
    def runTest(self):
        """Runs performance tests qith 10, 100, 200 items in a Backlog"""
        # We need to build a real environment at least we will test 
        # the IO
        self.teh = TestEnvHelper(env=self._testenv.get_trac_environment(), env_key=self.env_key)
        self._test_global_backlog()
        self._test_sprint_backlog()


if __name__ == '__main__':
    from agilo.test.testfinder import run_all_tests
    run_all_tests(__file__)


