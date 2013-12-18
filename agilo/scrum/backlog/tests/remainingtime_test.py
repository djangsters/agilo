# -*- encoding: utf-8 -*-
#   Copyright 2008-2009 Agile42 GmbH, Berlin (Germany)
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
#   Authors: 
#       - Jonas von Poser <jonas.vonposer__at__agile42.com>
#       - Felix Schwarz <felix.schwarz__at__agile42.com>

from datetime import date, timedelta

from agilo.scrum.backlog.burndown import RemainingTime
from agilo.test import AgiloTestCase
from agilo.utils import Key, Type
from agilo.utils.days_time import now, yesterday


class TestRemainingTime(AgiloTestCase):
    
    def testRemainingTime(self):
        # create a Agilo ticket
        t = self.teh.create_ticket(Type.TASK, props={
            Key.SUMMARY : "This is an AgiloTicket",
            Key.DESCRIPTION : "This is the description of the ticket...",
        })
        # create the corresponding RemainingTime object
        rt = RemainingTime(self.env, t)
        # set a value for remaining time
        rt.set_remaining_time(10, day=date(2008, 7, 1))
        # get remaining time for today, still the same
        rt = RemainingTime(self.env, t)
        self.assert_equals(rt.get_remaining_time(day=date(2008, 7, 1)), 10)
        # reload, today is really today
        rt = RemainingTime(self.env, t)
        self.assert_equals(rt.get_remaining_time(day=date(2008, 8, 1)), 10)
        # set a value for today
        rt.set_remaining_time(2.5, day=date(2008, 8, 1))
        # get remaining time between the two dates
        self.assert_equals(rt.get_remaining_time(date(2008, 7, 15)), 10)
        # get remaining time before there was anything
        self.assert_equals(rt.get_remaining_time(date(2008, 6, 15)), 0)
        # or after today...
        self.assert_equals(rt.get_remaining_time(date(2008, 8, 15)), 2.5)
    
    def testTicketRemainingTime(self):
        # set new remaining time on ticket
        t = self.teh.create_ticket(Type.TASK, props = {
            Key.SUMMARY : "This is an AgiloTicket",
            Key.DESCRIPTION : "This is the description of the ticket...",
            Key.REMAINING_TIME : "10",
        })
        
        # check for today
        rt = RemainingTime(self.env, t)
        self.assert_equals(rt.get_remaining_time(), 10)
        
        # ticket listener should update remaining time
        t[Key.REMAINING_TIME] = "1"
        t.save_changes('author', 'description')
        rt = RemainingTime(self.env, t)
        self.assert_equals(rt.get_remaining_time(), 1)
    
    def testRemainingTimeUpdaterShouldStoreFloatValues(self):
        task = self.teh.create_ticket(Type.TASK)
        task[Key.REMAINING_TIME] = '12.5'
        task.save_changes('foo', 'bar')
        
        remaining = RemainingTime(self.env, task)
        self.assert_almost_equals(12.5, remaining.get_remaining_time(), places=2)
    
    def testRemainingTimeStoredUponTicketCreation(self):
        # Unfortunately we can' test the RemainingTimeUpdater itself because it
        # depends on 'today' and I can't think of a way to fake that. But at 
        # least we can check that the remaining time is stored-when there is no
        # remaining time yet.
        task = self.teh.create_ticket(Type.TASK)
        remaining = RemainingTime(self.env, task)
        # Bad: We have to assume that remaining.history contains only the real
        # db items and current values will be taken from the ticket directly 
        # (not put into .history).
        self.assert_equals(0, len(remaining.history))
        
        task[Key.REMAINING_TIME] = '5'
        task.save_changes('foo', 'bar')
        remaining = RemainingTime(self.env, task)
        self.assert_equals(1, len(remaining.history))
    
    def testUseRemainingTimeFieldForTodaysRemainingTime(self):
        # The remaining time of a task for today should be taken from the 
        # remaining time field of the task regardless if there is any data stored
        # in the database.
        task = self.teh.create_ticket(Type.TASK)
        task[Key.REMAINING_TIME] = '5'
        
        remaining = RemainingTime(self.env, task)
        self.assert_equals(5, remaining.get_remaining_time(now()))
    
    def testStoreRemainingTimeAsTimestamp(self):
        task = self.teh.create_ticket(Type.TASK)
        task[Key.REMAINING_TIME] = '5'
        task.save_changes(None, None)
        
        an_hour_before = now() - timedelta(hours=1)
        half_an_hour_before = now() - timedelta(minutes=30)
        
        remaining = RemainingTime(self.env, task)
        remaining.set_remaining_time(3, day=an_hour_before)
        
        self.assert_equals(5, remaining.get_remaining_time())
        self.assert_equals(5, remaining.get_remaining_time(now()))
        self.assert_equals(3, remaining.get_remaining_time(half_an_hour_before))
        self.assert_equals(3, remaining.get_remaining_time(an_hour_before))
        self.assert_equals(0, remaining.get_remaining_time(yesterday()))

