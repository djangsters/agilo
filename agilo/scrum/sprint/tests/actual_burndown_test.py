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

from agilo.scrum.burndown import BurndownDataChange
from agilo.scrum.burndown.model import BurndownDataConstants
from agilo.scrum.sprint import SprintController
from agilo.test import AgiloTestCase
from agilo.utils import Key, Type
from agilo.utils.days_time import now

# REFACT: consider move to agilo.scrum.burndown.tests
class ActualBurndownTest(AgiloTestCase):
    
    def setUp(self):
        self.super()
        self.teh.disable_sprint_date_normalization()
        self.sprint = self.teh.create_sprint(name='Sprint 1', start=now() - timedelta(days=3), end=now() + timedelta(days=3))
        # already enteres a remaining time!
        self.task = self.teh.create_task(remaining_time=5, sprint=self.sprint.name)
        
        self.assert_true(self.sprint.is_currently_running)
    
    def actual_burndown(self, filter_by_component=None):
        command = SprintController.GetActualBurndownCommand(self.env,
            sprint=self.sprint.name, filter_by_component=filter_by_component,
            remaining_field=BurndownDataConstants.REMAINING_TIME)
        return SprintController(self.env).process_command(command)
    
    def set_remaining_time(self, task, when, remaining):
        BurndownDataChange.remaining_time_entry(self.env, remaining, self.sprint.name, when).save()
    
    def test_can_calculate_current_remaining_time_for_one_task(self):
        task_creation_time = self.sprint.start + timedelta(hours=1)
        self.set_remaining_time(self.task, task_creation_time, 12)
        
        remaining_times = self.actual_burndown()
        self.assert_length(3, remaining_times)
        last = remaining_times[-1]
        self.assert_almost_equals(now(), last.when, max_delta=timedelta(seconds=2))
        self.assert_equals(5 + 12, last.remaining_time)
    
    def test_can_calculate_first_remaining_time_for_one_task(self):
        first = self.actual_burndown()[0]
        self.assert_almost_equals(self.task.time_created, first.when, max_delta=timedelta(seconds=2))
        self.assert_equals(5, first.remaining_time)
    
    def test_can_filter_by_component(self):
        self.teh.enable_burndown_filter()
        self.teh.add_field_for_type(Key.COMPONENT, Type.TASK)
        task2 = self.teh.create_task(remaining_time=7, sprint=self.sprint.name, component='fnord')
        
        actual_burndown = self.actual_burndown(filter_by_component='fnord')
        self.assert_length(2, actual_burndown)
        self.assert_equals(7, actual_burndown[0].remaining_time)
        self.assert_equals(7, actual_burndown[1].remaining_time)
