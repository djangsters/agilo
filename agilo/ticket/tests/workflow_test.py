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


from agilo.test import AgiloTestCase
from agilo.ticket import AgiloTicket
from agilo.ticket.workflow_support import TicketStatusManipulator, \
    TransitionFinder, TicketHierarchyMover
from agilo.utils import Key, Status, Type



class TestFindTransitionInWorkflow(AgiloTestCase):
    
    def setUp(self):
        self.super()
        self.task = AgiloTicket(self.env, t_type=Type.TASK)
        # this task is not stored in the db on purpose - so I can check 
        # that no workflow does any permanent damage!
        del self.task._old[Key.TYPE]
        self._set_status_to(Status.NEW)
        req = self.teh.mock_request('foo')
        self.finder = TransitionFinder(self.env, req, self.task)
        self.assert_equals({}, self.task._old)
    
    def _set_status_to(self, status):
        self.task[Key.STATUS] = status
        del self.task._old[Key.STATUS]
        self.assert_equals({}, self.task._old)
    
    def test_can_find_transition_from_new_to_in_progress(self):
        self.assert_equals(Status.NEW, self.task[Key.STATUS])
        transition = self.finder.transition_to_in_progress_state()
        self.assert_equals(['accept'], transition)
        self.assert_equals({}, self.task._old)
    
    def test_can_find_direct_transition_from_accepted_to_closed(self):
        self._set_status_to(Status.ACCEPTED)
        transition = self.finder.transition_to_closed_state()
        self.assert_equals(['resolve'], transition)
        self.assert_equals({}, self.task._old)
    
    def test_can_find_direct_transition_from_assigned_to_new(self):
        self.teh.change_workflow_config([('putback', 'assigned -> new')])
        self._set_status_to(Status.ASSIGNED)
        transition = self.finder.transition_to_new_state()
        self.assert_equals(['putback'], transition)
        self.assert_equals({}, self.task._old)
    
    def test_can_find_even_indirect_transitions(self):
        self.teh.change_workflow_config([('putback', 'assigned -> new')])
        self._set_status_to(Status.ACCEPTED)
        transition = self.finder.transition_to_new_state()
        self.assert_equals(['reassign', 'putback'], transition)
        self.assert_equals({}, self.task._old)
    
    def test_use_shortest_transition(self):
        self.teh.change_workflow_config([('ask', 'assigned -> needinfo'),
                                      ('invalidate', 'needinfo -> new'),
                                      ('putback', 'assigned -> new'),
                                      ])
        self._set_status_to(Status.ACCEPTED)
        transition = self.finder.transition_to_new_state()
        self.assert_equals(['reassign', 'putback'], transition)
        self.assert_equals({}, self.task._old)
    
    def test_return_none_for_assigned_to_new_if_no_transition_allowed(self):
        self._set_status_to('assigned')
        transition = self.finder.transition_to_new_state()
        self.assert_none(transition)
        self.assert_equals({}, self.task._old)
    
    def test_return_none_for_reopenend_to_new_if_no_transition_allowed(self):
        self._set_status_to(Status.REOPENED)
        transition = self.finder.transition_to_new_state()
        self.assert_none(transition)
        self.assert_equals({}, self.task._old)
    
    def test_empty_transition_if_ticket_is_already_in_target_state(self):
        self.assert_equals(Status.NEW, self.task[Key.STATUS]) 
        self.assert_equals([], self.finder.transition_to_new_state())
        
        self._set_status_to(Status.ACCEPTED)
        self.assert_equals([], self.finder.transition_to_in_progress_state())
        
        self._set_status_to(Status.CLOSED)
        self.assert_equals([], self.finder.transition_to_closed_state())


class TestManipulateTicketStatus(AgiloTestCase):
    
    def setUp(self):
        self.super()
        self.task = AgiloTicket(self.env, t_type=Type.TASK)
        # this task is not stored in the db on purpose - so I can check 
        # that no workflow does any permanent damage!
        del self.task._old[Key.TYPE]
        req = self.teh.mock_request('foo')
        self.manipulator = TicketStatusManipulator(self.env, req, self.task)
        self.assert_equals({}, self.task._old)
    
    def _set_status_to(self, status):
        self.task[Key.STATUS] = status
        del self.task._old[Key.STATUS]
        self.assert_equals({}, self.task._old)
    
    def test_ignores_workflow_if_no_valid_transition_to_new_was_found(self):
        self._set_status_to('assigned')
        self.manipulator.change_status_to('new')
        self.assert_equals(Status.NEW, self.task[Key.STATUS])
    
    def test_delete_owner_if_new_status_is_new(self):
        self._set_status_to(Status.ACCEPTED)
        self.task[Key.OWNER] = 'foo'
        self.manipulator.change_status_to('new')
        self.assert_equals(Status.NEW, self.task[Key.STATUS])
        self.assert_equals('', self.task[Key.OWNER])
    
    def test_delete_resolution_if_ticket_was_closed_before(self):
        self._set_status_to(Status.CLOSED)
        self.task[Key.OWNER] = 'foo'
        self.task[Key.RESOLUTION] = Status.RES_FIXED
        self.manipulator.change_status_to('in_progress')
        self.assert_equals(Status.REOPENED, self.task[Key.STATUS])
        self.assert_equals('', self.task[Key.RESOLUTION])
    
    def test_can_ignore_workflow_for_transition_to_closed(self):
        self.teh.change_workflow_config([('resolve', '* -> in_qa')])
        self._set_status_to(Status.ACCEPTED)
        self.task[Key.OWNER] = 'foo'
        self.manipulator.change_status_to('closed')
        self.assert_equals(Status.CLOSED, self.task[Key.STATUS])
        self.assert_equals(Status.RES_FIXED, self.task[Key.RESOLUTION])
    
    def test_can_ignore_workflow_for_transition_to_in_progress(self):
        self.teh.change_workflow_config([('reopen', 'assigned -> new')])
        self._set_status_to(Status.CLOSED)
        self.task[Key.OWNER] = 'bar'
        self.task[Key.RESOLUTION] = Status.RES_FIXED
        self.manipulator.change_status_to('in_progress')
        self.assert_equals(Status.ACCEPTED, self.task[Key.STATUS])
        self.assert_equals('', self.task[Key.RESOLUTION])
        self.assert_equals('foo', self.task[Key.OWNER])
    
    def test_can_ignore_workflow_for_transition_custom_ticket_status(self):
        self.teh.change_workflow_config([('fnordify', 'new -> fnord')])
        self._set_status_to(Status.NEW)
        self.manipulator.change_status_to('fnord')
        self.assert_equals('fnord', self.task[Key.STATUS])
    
    def test_will_choose_assigned_as_default_in_progress_status(self):
        # not sure in what order the workflows are found, but 'abc' helped trigger this bug
        # since it's alphabetically smaller than 'accept'
        self.teh.change_workflow_config([('abc', 'new -> fnord')])
        self._set_status_to(Status.NEW)
        self.manipulator.change_status_to('in_progress')
        self.assert_equals(Status.ACCEPTED, self.task[Key.STATUS])
    
    def test_can_transition_to_custom_ticket_status(self):
        self.teh.change_workflow_config([('fnordify', 'new -> fnord')])
        self._set_status_to(Status.NEW)
        self.manipulator.change_status_to('fnord')
        self.assert_equals('fnord', self.task[Key.STATUS])
    

class TestMoveTicketHierarchyOnSprintChange(AgiloTestCase):
    
    def setUp(self):
        self.super()
        
        self.old_sprint = 'Old Sprint'
        self.new_sprint = 'New Sprint'
        self.teh.create_sprint(self.old_sprint)
        self.teh.create_sprint(self.new_sprint)
        self._create_story_and_task()
    
    def _create_story_and_task(self):
        self.story = self.teh.create_story(sprint=self.old_sprint)
        self.task = self.teh.create_task(sprint=self.old_sprint)
        self.assert_true(self.story.link_to(self.task))
    
    def _assert_ticket_has_sprint(self, ticket_id, sprint_name):
        ticket = AgiloTicket(self.env, ticket_id)
        self.assert_equals(sprint_name, ticket[Key.SPRINT])
        
    def _assert_ticket_has_new_sprint(self, ticket_id):
        self._assert_ticket_has_sprint(ticket_id, self.new_sprint)
    
    def _assert_ticket_has_old_sprint(self, ticket_id):
        self._assert_ticket_has_sprint(ticket_id, self.old_sprint)
    
    def _assert_move_task_of_story(self):
        mover = TicketHierarchyMover(self.env, self.story, self.old_sprint, self.new_sprint)
        self._assert_ticket_has_old_sprint(self.task.id)
        mover.execute()
        self._assert_ticket_has_new_sprint(self.task.id)
    
    def test_can_move_task_of_a_story(self):
        self._assert_move_task_of_story()
    
    def test_can_pull_in_task_of_a_story(self):
        self.old_sprint = ''
        self._create_story_and_task()
        self._assert_move_task_of_story()
    
    def test_can_pull_out_task_of_a_story(self):
        self.new_sprint = ''
        self._assert_move_task_of_story()
    
    def test_can_have_identical_source_and_destination(self):
        self.new_sprint = self.old_sprint
        self._assert_move_task_of_story()
    
    def test_does_not_move_closed_task(self):
        self.task[Key.STATUS] = Status.CLOSED
        self.task.save_changes(None, None)
        
        mover = TicketHierarchyMover(self.env, self.story, self.old_sprint, self.new_sprint)
        mover.execute()
        self._assert_ticket_has_old_sprint(self.task.id)
    
    def test_does_not_move_task_with_different_sprint(self):
        self.teh.create_sprint('Third Sprint')
        self.task[Key.SPRINT] = 'Third Sprint'
        self.task.save_changes(None, None)
        
        mover = TicketHierarchyMover(self.env, self.story, self.old_sprint, self.new_sprint)
        mover.execute()
        self._assert_ticket_has_sprint(self.task.id, 'Third Sprint')
    
    def test_can_move_indirect_task(self):
        bug = self.teh.create_ticket(t_type=Type.BUG, props=dict(sprint=self.old_sprint))
        self.assert_true(bug.link_to(self.story))
        
        mover = TicketHierarchyMover(self.env, bug, self.old_sprint, self.new_sprint)
        mover.execute()
        self._assert_ticket_has_new_sprint(self.task.id)
    
    def test_will_store_default_author_on_changelog(self):
        self._assert_move_task_of_story()
        self.assert_equals("agilo", self.teh.last_changelog_author(self.task))
    
    def test_will_store_custom_author_on_changelog(self):
        mover = TicketHierarchyMover(self.env, self.story, self.old_sprint,
                                     self.new_sprint, changelog_author="fnord")
        mover.execute()
        self.assert_equals("fnord", self.teh.last_changelog_author(self.task))
    
    def test_does_not_explode_if_child_has_no_sprint_field(self):
        self.teh.allow_link_from_to(Type.USER_STORY, Type.REQUIREMENT)
        # recreate object because the allowed links are cached inside
        self.story = AgiloTicket(self.env, self.story.id)
        
        requirement = self.teh.create_ticket(t_type=Type.REQUIREMENT)
        self.assert_true(self.story.link_to(requirement))
        
        mover = TicketHierarchyMover(self.env, self.story, self.old_sprint, self.new_sprint)
        mover.execute()
        self._assert_ticket_has_sprint(requirement.id, '')
    
