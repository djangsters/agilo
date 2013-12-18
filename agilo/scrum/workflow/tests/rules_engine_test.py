# -*- encoding: utf-8 -*-
#   Copyright 2008 Agile42 GmbH, Berlin (Germany)
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
#   Authors: 
#       - Andrea Tomasini <andrea.tomasini_at_agile42.com>

from trac.core import Component, implements

from agilo.scrum.workflow.api import RuleEngine, IRule, RuleValidationException
from agilo.scrum.workflow.rules import OwnerIsATeamMemberRule
from agilo.test import AgiloTestCase
from agilo.utils import Key, Status, Type


class RuleEngineTest(AgiloTestCase):
    """Tests the rules and the rule engine"""
    
    def setUp(self):
        self.super()
        self.assert_true(self.env.is_component_enabled(RuleEngine))
        self.assert_true(self.env.is_component_enabled(OwnerIsATeamMemberRule))
    
    def testRuleEngine(self):
        """Tests if the extension point works"""
        class TestRule(Component):
            implements(IRule)
            
            def validate(self, ticket):
                # This is a safeguard that prevents that this rule kicks in 
                # beyond this test case (which could happen because once a 
                # component was instantiated, it will always be found via the
                # extension point
                if ticket == None:
                    raise RuleValidationException
        
        self.assert_raises(RuleValidationException, 
                          RuleEngine(self.env).validate_rules, None)
        
    def testOwnerIsATeamMember(self):
        """Tests the OwnerIsATeamMemberRule"""
        t = self.teh.create_team('A-Team')
        tm = self.teh.create_member('TeamMember', t)
        self.assert_true(tm.save())
        s = self.teh.create_sprint('Test Sprint')
        s.team = t
        self.assert_true(s.save())
        task = self.teh.create_ticket(Type.TASK, props={Key.REMAINING_TIME: '12.5'})
        task[Key.OWNER] = tm.name
        task[Key.SPRINT] = s.name
        self.assert_true(task.save_changes(tm.name, 'Changed Owner...'), "Owner change not allowed?")
        self.teh.move_changetime_to_the_past([task])
        # Now reload the ticket and assign an owner which is not a team member
        task = self.teh.load_ticket(task)
        self.assert_not_none(task)
        task[Key.OWNER] = 'NotATeamMember'
        self.assert_raises(RuleValidationException, task.save_changes, 'NotATeamMember', 'Trying to override...')
    
    def testRemoveLettersFromRemainingTime(self):
        task = self.teh.create_ticket(Type.TASK)
        task[Key.REMAINING_TIME] = '12.5h'
        task.save_changes('Foo', 'Blah')
        
        self.assert_equals('12.5', task[Key.REMAINING_TIME])
    
    def testRemoveInvalidNumbersFromRemainingTime(self):
        task = self.teh.create_ticket(Type.TASK)
        task[Key.REMAINING_TIME] = 'foobar'
        task.save_changes('Foo', 'Blah')
        self.assert_equals('', task[Key.REMAINING_TIME])
    
    def testReopenClosedTask(self):
        task_props = {Key.REMAINING_TIME: '0', Key.STATUS: Status.CLOSED,
                      Key.RESOLUTION: Status.RES_FIXED }
        task = self.teh.create_ticket(Type.TASK, props=task_props)
        
        task[Key.STATUS] = Status.REOPENED
        task[Key.RESOLUTION] = None
        task.save_changes(None, 'it is not done yet')
        self.assert_equals(Status.REOPENED, task[Key.STATUS])
        self.assert_equals('0', task[Key.REMAINING_TIME])
        self.assert_equals('', task[Key.RESOLUTION])
    
    def testDoNotCloseTaskWithRemainingTime0WhenRemainingTimeDidNotChange(self):
        task_props = {Key.REMAINING_TIME: '0', Key.STATUS: Status.CLOSED,
                      Key.RESOLUTION: Status.RES_FIXED }
        task = self.teh.create_ticket(Type.TASK, props=task_props)
        
        self.teh.move_changetime_to_the_past([task])
        task[Key.STATUS] = Status.REOPENED
        task[Key.RESOLUTION] = None
        task.save_changes(None, 'reopening...')
        self.assert_equals(Status.REOPENED, task[Key.STATUS])
        
        self.teh.move_changetime_to_the_past([task])
        task[Key.STATUS] = Status.NEW
        task.save_changes(None, 'Actually I can not do it')
        
        self.assert_equals(Status.NEW, task[Key.STATUS])
        self.assert_equals('0', task[Key.REMAINING_TIME])
        self.assert_equals('', task[Key.RESOLUTION])
    
    def testSetRemainingTimeToZeroForClosedTasks(self):
        task_props = {Key.REMAINING_TIME: '5'}
        task = self.teh.create_ticket(Type.TASK, props=task_props)
        
        task[Key.STATUS] = Status.CLOSED
        # This is a situation as if the status was updated directly from the 
        # sprint backlog (the view ticket page will always set a resolution)
        task[Key.RESOLUTION] = None
        task.save_changes(None, 'duplicated task')
        self.assert_equals(Status.CLOSED, task[Key.STATUS])
        self.assert_equals('0', task[Key.REMAINING_TIME])
        self.assert_equals('', task[Key.RESOLUTION])

    def testStorySetToAcceptedIfAtLeastOneTaskIs(self):
        task_props = {Key.REMAINING_TIME: '5'}
        story = self.teh.create_ticket(Type.USER_STORY, props={Key.STORY_PRIORITY: 'Mandatory'})
        task = self.teh.create_ticket(Type.TASK, props=task_props)
        self.assert_true(story.link_to(task))
        # check status
        self.assert_equals(Status.NEW, story[Key.STATUS])
        self.assert_equals(Status.NEW, task[Key.STATUS])
        # accept the task and check also the story changed
        task[Key.STATUS] = Status.ACCEPTED
        task.save_changes('tester', 'Acecpting the task...')
        self.assert_equals(Status.ACCEPTED, story[Key.STATUS])

