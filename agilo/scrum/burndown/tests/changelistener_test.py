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


from agilo.scrum.burndown import BurndownDataAggregator
from agilo.scrum.burndown.model import BurndownDataChangeModelManager, BurndownDataConstants
from agilo.test import AgiloTestCase
from agilo.ticket import AgiloTicket
from agilo.utils import Key, Type, Status
from agilo.utils.config import AgiloConfig

class BurndownDataChangeListenerTest(AgiloTestCase):
    
    def setUp(self):
        self.super()
        self.sprint = self.teh.create_sprint('BurndownDataChangeListenerTestSprint')
    
    def _create_ticket(self, sprint=None, remaining_time=None, ticket_type=Type.TASK, component=None):
        ticket = AgiloTicket(self.env, t_type=ticket_type)
        
        if sprint is None:
            sprint = self.sprint
        if sprint != '':
            # REFACT: create a new method to remove None vs. '' semantics
            ticket[Key.SPRINT] = self._sprint_name(sprint)
        if remaining_time is not None:
            ticket[Key.REMAINING_TIME] = remaining_time
        if component is not None:
            ticket[Key.COMPONENT] = component
        ticket.insert()
        
        return ticket
    
    def _create_ticket_without_history(self, *args, **kwargs):
        ticket = self._create_ticket(*args, **kwargs)
        self._remove_all_changes()
        return ticket
    
    def _remove_all_changes(self):
        changes = BurndownDataChangeModelManager(self.env).select()
        for change in changes:
            change.delete()
        self.assert_no_changes_stored()
    
    def _change_ticket_and_save(self, ticket, key, value, author=None, comment=None):
        ticket[key] = value
        ticket.save_changes(author, comment)
    
    def _sprint_name(self, sprint_or_sprint_name):
        if isinstance(sprint_or_sprint_name, basestring):
                return sprint_or_sprint_name
        return sprint_or_sprint_name.name 
    
    def _add_remaining_time_field_for_bugs(self):
        self.teh.add_field_for_type(Key.REMAINING_TIME, Type.BUG)
    
    def _add_remaining_time_field_for_requirements(self):
        self.teh.add_field_for_type(Key.REMAINING_TIME, Type.REQUIREMENT)
    
    def _changes_for_sprint(self, sprint=None):
        if sprint is None:
            sprint = self.sprint
        return BurndownDataAggregator(self.env).changes_for_sprint(sprint)
    
    def assert_one_change_exists_with_delta(self, expected_remaining_time, sprint=None):
        changes = self._changes_for_sprint(sprint)
        self.assert_length(1, changes)
        self.assert_equals(expected_remaining_time, changes[0].delta())
    
    def assert_no_change_exists_for_sprint(self, sprint=None):
        changes = self._changes_for_sprint(sprint)
        self.assert_length(0, changes)
    
    def assert_no_changes_stored(self):
        changes = BurndownDataChangeModelManager(self.env).select()
        self.assert_length(0, changes)
    
    def filter_skip_changes(self, changes):
        return filter(lambda change: not change.has_marker(BurndownDataConstants.SKIP_AGGREGATION), changes)

    def assert_no_non_skip_changes_stored(self):
        changes = BurndownDataChangeModelManager(self.env).select()
        changes = self.filter_skip_changes(changes)
        self.assert_length(0, changes)
    

class TicketCreateBurndownListenerTest(BurndownDataChangeListenerTest):

    def test_can_store_change_when_creating_new_ticket(self):
        self._create_ticket(self.sprint, '4.5')
        self.assert_one_change_exists_with_delta(4.5)
    
    def test_does_not_store_change_when_ticket_has_no_sprint_field(self):
        self._add_remaining_time_field_for_requirements()
        self._create_ticket(remaining_time='4.5', ticket_type=Type.REQUIREMENT)
        self.assert_no_changes_stored()
    
    def test_does_not_store_change_when_ticket_has_no_remaining_time_field(self):
        self._create_ticket(sprint=self.sprint, ticket_type=Type.USER_STORY)
        self.assert_no_changes_stored()
    
    def test_does_not_store_change_if_task_is_not_planned_for_a_sprint(self):
        self._create_ticket(sprint='', remaining_time='4.5')
        self.assert_no_changes_stored()
    
    def test_does_not_store_change_if_task_has_no_remaining_time_set(self):
        self._create_ticket(self.sprint)
        self.assert_no_changes_stored()
    

class TicketChangeBurndownListenerTest(BurndownDataChangeListenerTest):
    
    def setUp(self):
        self.super()
        self.sprint2 = self.teh.create_sprint('SecondBurndownDataChangeListenerTestSprint')
    
    def test_store_change_when_remaining_time_is_changed(self):
        task = self._create_ticket_without_history(remaining_time=10)
        self._change_ticket_and_save(task, Key.REMAINING_TIME, 2)
        self.assert_one_change_exists_with_delta(-8)
    
    def test_store_change_when_remaining_time_set_to_zero(self):
        task = self._create_ticket_without_history(remaining_time=10)
        self._change_ticket_and_save(task, Key.REMAINING_TIME, 0)
        self.assert_one_change_exists_with_delta(-10)
    
    def test_can_store_change_when_task_is_closed(self):
        # Actually this is done by a business rule which is called *before*
        # any change listener - however we want to be sure that we always 
        # store correct data.
        task = self._create_ticket_without_history(remaining_time=10)
        self._change_ticket_and_save(task, Key.STATUS, Status.CLOSED)
        self.assert_one_change_exists_with_delta(-10)
    
    def test_does_not_store_changed_remaining_time_when_ticket_has_no_sprint_field(self):
        self._add_remaining_time_field_for_requirements()
        requirement = self._create_ticket_without_history(remaining_time='4', ticket_type=Type.REQUIREMENT)
        self._change_ticket_and_save(requirement, Key.REMAINING_TIME, 1)
        self.assert_no_changes_stored()
    
    def test_does_not_store_edit_change_when_ticket_has_no_remaining_time_field(self):
        story = self._create_ticket_without_history(sprint=self.sprint, ticket_type=Type.USER_STORY)
        self._change_ticket_and_save(story, Key.SPRINT, self.sprint2.name)
        self.assert_no_non_skip_changes_stored()
    
    def test_does_not_store_change_on_unrelated_edit(self):
        task = self._create_ticket_without_history(remaining_time=10)
        self._change_ticket_and_save(task, Key.SUMMARY, 'fnord')
        self.assert_no_changes_stored()
    
    def test_dont_store_change_for_plain_type_changes(self):
        self._add_remaining_time_field_for_bugs()
        task = self._create_ticket_without_history(sprint=self.sprint, remaining_time=10)
        self._change_ticket_and_save(task, Key.TYPE, Type.BUG)
        self.assert_no_changes_stored()
    
    def test_type_change_removes_remaining_time_but_value_was_set_at_creation(self):
        # Actually we'd like to have one change recorded with a delta of '-4'.
        # However during type switching some fields are not visible anymore in 
        # the ticket object and their values were never saved to the ticket 
        # changelog (because these fields don't appear in ticket._old)
        task = self._create_ticket_without_history(remaining_time=4)
        self._change_ticket_and_save(task, Key.TYPE, Type.USER_STORY)
        self.assert_no_changes_stored()
    
    def test_store_change_on_type_change_even_if_new_type_has_no_sprint(self):
        # Same as the above test, this is not expected behavior, but
        # a known bug.
        task = self._create_ticket_without_history(sprint='', remaining_time=7)
        self._change_ticket_and_save(task, Key.SPRINT, self.sprint.name)
        self._remove_all_changes()
        self.teh.move_changetime_to_the_past([task])
        self._add_remaining_time_field_for_requirements()
        self._change_ticket_and_save(task, Key.TYPE, Type.REQUIREMENT)
        self.assert_no_changes_stored()
    
    def test_store_change_on_type_change_even_if_new_type_has_no_remaining_time(self):
        task = self._create_ticket_without_history()
        self._change_ticket_and_save(task, Key.REMAINING_TIME, '4')
        self._remove_all_changes()
        self.teh.move_changetime_to_the_past([task])
        self._change_ticket_and_save(task, Key.TYPE, Type.USER_STORY)
        self.assert_one_change_exists_with_delta(-4)
    
    def test_can_store_change_when_adding_sprint(self):
        task = self._create_ticket_without_history(sprint='', remaining_time=10)
        self._change_ticket_and_save(task, Key.SPRINT, self.sprint.name)
        self.assert_one_change_exists_with_delta(10)
    
    def test_can_store_two_changes_when_changing_sprint(self):
        task = self._create_ticket_without_history(remaining_time=10)
        self._change_ticket_and_save(task, Key.SPRINT, self.sprint2.name)
        self.assert_one_change_exists_with_delta(-10, sprint=self.sprint)
        self.assert_one_change_exists_with_delta(10, sprint=self.sprint2)
    
    def test_stores_correct_delta_if_sprint_changed_and_remaining_time_set_to_zero(self):
        task = self._create_ticket_without_history(remaining_time=10)
        task[Key.SPRINT] = self.sprint2.name
        task[Key.REMAINING_TIME] = 0
        task.save_changes(None, None)
        self.assert_one_change_exists_with_delta(-10, sprint=self.sprint)
        self.assert_no_change_exists_for_sprint(self.sprint2)
    
    def test_store_two_deltas_if_task_is_moved_to_another_sprint_and_is_time_increased(self):
        task = self._create_ticket_without_history(remaining_time=10)
        task[Key.SPRINT] = self.sprint2.name
        task[Key.REMAINING_TIME] = 15
        task.save_changes(None, None)
        self.assert_one_change_exists_with_delta(-10, sprint=self.sprint)
        self.assert_one_change_exists_with_delta(15, self.sprint2)
    
    def test_can_store_change_when_removing_sprint(self):
        task = self._create_ticket_without_history(remaining_time=10)
        self._change_ticket_and_save(task, Key.SPRINT, '')
        self.assert_one_change_exists_with_delta(-10)
    
class ChangingSprintOnStoryWillSkipAggregationTest(BurndownDataChangeListenerTest):
    
    def setUp(self):
        self.super()
        self.sprint2 = self.teh.create_sprint('SecondBurndownDataChangeListenerTestSprint')
    
    def test_creates_skip_aggregation_markers_when_moving_story_to_another_sprint(self):
        story = self._create_ticket_without_history(sprint=self.sprint, ticket_type=Type.USER_STORY)
        self._change_ticket_and_save(story, Key.SPRINT, self.sprint2.name)
        
        changes = self._changes_for_sprint(self.sprint)
        self.assert_minimum_length(2, changes)
        self.assert_true(changes[0].has_marker(BurndownDataConstants.SKIP_AGGREGATION))
        self.assert_true(changes[1].has_marker(BurndownDataConstants.SKIP_AGGREGATION))
        changes = self._changes_for_sprint(self.sprint2)
        self.assert_minimum_length(2, changes)
        self.assert_true(changes[0].has_marker(BurndownDataConstants.SKIP_AGGREGATION))
        self.assert_true(changes[1].has_marker(BurndownDataConstants.SKIP_AGGREGATION))
    
    def test_creates_skip_aggregation_markers_when_removing_story_from_sprint(self):
        story = self._create_ticket_without_history(sprint=self.sprint, ticket_type=Type.USER_STORY)
        self._change_ticket_and_save(story, Key.SPRINT, None)
        
        changes = self._changes_for_sprint(self.sprint)
        self.assert_minimum_length(2, changes)
        self.assert_true(changes[0].has_marker(BurndownDataConstants.SKIP_AGGREGATION))
        self.assert_true(changes[1].has_marker(BurndownDataConstants.SKIP_AGGREGATION))
    
    def test_creates_skip_aggregation_markers_when_adding_story_to_sprint(self):
        story = self._create_ticket_without_history(sprint='', ticket_type=Type.USER_STORY)
        task = self._create_ticket_without_history(sprint='', ticket_type=Type.TASK)
        self.assert_true(story.link_to(task))
        self._change_ticket_and_save(story, Key.SPRINT, self.sprint.name)
        
        changes = self._changes_for_sprint(self.sprint)
        self.assert_minimum_length(2, changes)
        self.assert_true(changes[0].has_marker(BurndownDataConstants.SKIP_AGGREGATION))
        self.assert_true(changes[1].has_marker(BurndownDataConstants.SKIP_AGGREGATION))
        
        task = AgiloTicket(self.env, task.id)
        self.assert_equals(self.sprint.name, task[Key.SPRINT])
    
    def test_can_move_child_tasks_when_moving_a_story(self):
        story = self._create_ticket_without_history(ticket_type=Type.USER_STORY)
        task = self._create_ticket_without_history(ticket_type=Type.TASK, remaining_time=14)
        self.assert_true(story.link_to(task))
        self._change_ticket_and_save(story, Key.SPRINT, self.sprint2.name)
        
        def _assert_three_changes_with_delta(sprint, delta):
            changes = self._changes_for_sprint(sprint)
            self.assert_minimum_length(3, changes)
            self.assert_true(changes[0].has_marker(BurndownDataConstants.SKIP_AGGREGATION))
            self.assert_equals(delta, changes[1].delta())
            self.assert_false(changes[1].has_marker(BurndownDataConstants.SKIP_AGGREGATION))
            self.assert_true(changes[2].has_marker(BurndownDataConstants.SKIP_AGGREGATION))
        _assert_three_changes_with_delta(self.sprint, -14)
        _assert_three_changes_with_delta(self.sprint2, 14)
    
    def test_does_not_explode_with_cascaded_stories(self):
        bug = self._create_ticket_without_history(ticket_type=Type.BUG)
        task1 = self._create_ticket_without_history(ticket_type=Type.TASK, remaining_time=14)
        self.assert_true(bug.link_to(task1))
        story = self._create_ticket_without_history(ticket_type=Type.USER_STORY)
        self.assert_true(bug.link_to(story))
        task2 = self._create_ticket_without_history(ticket_type=Type.TASK, remaining_time=16)
        self.assert_true(story.link_to(task2))
        self._change_ticket_and_save(bug, Key.SPRINT, self.sprint2.name)
        
        def _assert_changes_exist(sprint):
            changes = self._changes_for_sprint(sprint)
            non_skip_changes = self.filter_skip_changes(changes)
            self.assert_minimum_length(6, changes)
            self.assert_length(2, non_skip_changes)
        _assert_changes_exist(self.sprint)
    
    def test_can_record_author_in_changelog_of_moved_tickets(self):
        story = self._create_ticket_without_history(ticket_type=Type.USER_STORY)
        task = self._create_ticket_without_history(ticket_type=Type.TASK, remaining_time=14)
        self.assert_true(story.link_to(task))
        self._change_ticket_and_save(story, Key.SPRINT, self.sprint2.name, author="fnord")
        
        self.assert_equals("fnord", self.teh.last_changelog_author(task))
    
class CanSaveComponentMarkerOnTicketChangeTest(BurndownDataChangeListenerTest):
    
    def setUp(self):
        self.super()
        self.sprint2 = self.teh.create_sprint('SecondBurndownDataChangeListenerTestSprint')
        self.teh.add_field_for_type(Key.COMPONENT, Type.TASK)
        self.teh.enable_burndown_filter()
    
    def assert_one_change_exists_with_component(self, component, sprint=None):
        changes = self._changes_for_sprint(sprint)
        self.assert_length(1, changes)
        self.assert_equals(component, changes[0].marker_value(Key.COMPONENT))
    
    def test_can_save_component_marker_on_ticket_change(self):
        task = self._create_ticket_without_history(component='foo', remaining_time=10)
        self._change_ticket_and_save(task, Key.REMAINING_TIME, 2)
        self.assert_one_change_exists_with_component('foo')
    
    def test_can_save_component_marker_on_ticket_create(self):
        self._create_ticket(self.sprint, '4.5', component='foo')
        self.assert_one_change_exists_with_component('foo')
    
    def test_can_save_component_marker_on_ticket_delete(self):
        self._create_ticket_without_history(remaining_time=4, component='foo').delete()
        self.assert_one_change_exists_with_component('foo')
    
    def test_will_not_save_component_if_config_is_disabled(self):
        self.env.config.set(AgiloConfig.AGILO_GENERAL, 'should_reload_burndown_on_filter_change_when_filtering_by_component', False)
        task = self._create_ticket_without_history(component='foo', remaining_time=10)
        self._change_ticket_and_save(task, Key.REMAINING_TIME, 2)
        
        change = self._changes_for_sprint()[0]
        self.assert_false(change.has_marker(Key.COMPONENT))
    
    def test_will_not_save_duplicate_entries_on_component_change_if_disabled(self):
        self.env.config.set(AgiloConfig.AGILO_GENERAL, 'should_reload_burndown_on_filter_change_when_filtering_by_component', False)
        task = self._create_ticket_without_history(component='foo', remaining_time=10)
        self._change_ticket_and_save(task, Key.COMPONENT, 'bar')
        self.assert_no_changes_stored()
    
    def assert_burndown_change(self, change, sprint, delta, component):
        self.assert_equals(sprint, change.scope)
        self.assert_equals(delta, change.delta())
        self.assert_equals(component, change.marker_value(Key.COMPONENT))
    
    def test_save_change_on_component_change(self):
        task = self._create_ticket_without_history(component='foo', remaining_time=10)
        self._change_ticket_and_save(task, Key.COMPONENT, 'bar')
        changes = self._changes_for_sprint()
        self.assert_length(2, changes)
        self.assert_burndown_change(changes[0], self.sprint.name, -10, 'foo')
        self.assert_burndown_change(changes[1], self.sprint.name, 10, 'bar')
    
    def test_marks_all_changes_when_changing_remaining_time_and_sprint(self):
        task = self._create_ticket_without_history(component='foo', remaining_time=10)
        task[Key.SPRINT] = self.sprint2.name
        task[Key.REMAINING_TIME] = 7
        self._change_ticket_and_save(task, Key.COMPONENT, 'bar')
        changes = self._changes_for_sprint()
        self.assert_length(3, changes)
        self.assert_burndown_change(changes[0], self.sprint.name, -10, 'foo')
        self.assert_burndown_change(changes[1], self.sprint.name, 10, 'bar')
        self.assert_burndown_change(changes[2], self.sprint.name, -10, 'bar')
        changes = self._changes_for_sprint(self.sprint2)
        self.assert_length(1, changes)
        self.assert_burndown_change(changes[0], self.sprint2.name, 7, 'bar')
    

class TicketDeleteBurndownListenerTest(BurndownDataChangeListenerTest):
    
    def test_stores_delta_on_ticket_delete(self):
        self._create_ticket_without_history(remaining_time=4).delete()
        self.assert_one_change_exists_with_delta(-4)
    
    def test_does_not_store_delta_if_task_has_no_remaining_time(self):
        self._create_ticket_without_history().delete()
        self.assert_no_changes_stored()
    
    def test_does_not_store_delta_if_no_sprint_set(self):
        self._create_ticket_without_history(remaining_time=4, sprint='').delete()
        self.assert_no_changes_stored()
