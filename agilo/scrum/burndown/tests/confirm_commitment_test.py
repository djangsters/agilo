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

from agilo.api import ValueObject
from agilo.scrum.burndown.model import (BurndownDataAggregator, 
    BurndownDataChange, BurndownDataConfirmCommitment, BurndownDataConstants)
from agilo.test import AgiloTestCase
from agilo.utils import Key
from agilo.utils.days_time import now


class ConfirmCommitmentTest(AgiloTestCase):
    
    def setUp(self):
        self.super()
        self.sprint = self.teh.create_sprint(self.sprint_name())
        self.aggregator = BurndownDataAggregator(self.env)
        self.confirmer = BurndownDataConfirmCommitment(self.env)
    
    def changes(self, sprint=None):
        return self.aggregator.changes_for_sprint(sprint and ValueObject(name=sprint) or self.sprint)
    
    def create_change(self, delta=23, marker_key=None, marker_value=None, **kwargs):
        change = BurndownDataChange(self.env)
        change.type = BurndownDataConstants.REMAINING_TIME
        change.scope = self.sprint.name
        change.when = now()
        change.set_delta(delta)
        for key, value in kwargs.items():
            setattr(change, key, value)
        if marker_key is not None:
            change.update_marker(marker_key, marker_value)
        return change
    
    def insert_changes(self):
        self.create_change().save()
        self.create_change().save()
        self.create_change().save()
    
    
    
    def test_can_remove_all_entries_that_are_already_set_for_a_sprint(self):
        self.insert_changes()
        self.confirmer.remove_old_changes_for_sprint(self.sprint)
        self.assert_length(0, self.changes())
    
    # TODO: might need to care about the key so story burndown values are not / too removed?
    def test_will_not_touch_entries_for_other_sprints_when_removing(self):
        self.insert_changes()
        self.create_change(scope='fnord').save()
        self.confirmer.remove_old_changes_for_sprint(self.sprint)
        self.assert_length(0, self.changes())
        self.assert_length(1, self.changes(sprint='fnord'))
    
    def test_sum_remaining_time_in_sprint(self):
        self.create_change(delta=3).save()
        self.assert_equals(3, self.confirmer.sum_remaining_time_for_sprint(self.sprint))
        self.create_change(delta=5).save()
        self.assert_equals(8, self.confirmer.sum_remaining_time_for_sprint(self.sprint))
        self.create_change(delta=10).save()
        self.assert_equals(18, self.confirmer.sum_remaining_time_for_sprint(self.sprint))
        self.create_change(delta=-12).save()
        self.assert_equals(6, self.confirmer.sum_remaining_time_for_sprint(self.sprint))
    
    def test_adding_initial_remaining_time(self):
        self.confirmer.add_initial_change_for_sprint_with_remaining_time(self.sprint, 10)
        self.assert_length(1, self.changes())
        self.assert_equals(10, self.changes()[0].delta())
    
    def test_created_initial_burndown_element_has_correct_time(self):
        self.confirmer.add_initial_change_for_sprint_with_remaining_time(self.sprint, 23)
        self.assert_almost_equals(now(), self.changes()[0].when, max_delta=timedelta(seconds=2))
    
    def test_enters_sum_of_removed_burndown_as_first_entry_after_removing_all_others(self):
        self.create_change(delta=10).save()
        self.create_change(delta=7).save()
        self.create_change(delta=6).save()
        self.confirmer.confirm_commitment_for_sprint(self.sprint)
        self.assert_length(1, self.changes())
        self.assert_equals(23, self.changes()[0].delta())
    
    # TODO: Consider to only remove ticket-change-entries until the target time!
    def test_can_set_time_of_commitment(self):
        self.create_change(delta=30).save()
        some_time_ago = now() - timedelta(days=3)
        self.confirmer.confirm_commitment_for_sprint(self.sprint, when=some_time_ago)
        self.assert_length(1, self.changes())
        self.assert_almost_equals(some_time_ago, self.changes()[0].when, max_delta=timedelta(seconds=2))
    
    def test_can_add_metadata_with_commitment_for_each_component_if_filtered_burndown_is_activated(self):
        self.teh.enable_burndown_filter()
        self.create_change(delta=3, when=self.sprint.start, marker_key=Key.COMPONENT, marker_value='foo').save()
        self.create_change(delta=5, when=self.sprint.start, marker_key=Key.COMPONENT, marker_value='bar').save()
        self.create_change(delta=7, when=self.sprint.start).save()
        self.confirmer.confirm_commitment_for_sprint(self.sprint, when=self.sprint.start)
        self.assert_length(1, self.changes())
        change = self.changes()[0]
        self.assert_true(change.has_marker(BurndownDataConstants.DELTAS_BY_COMPONENT))
        deltas = change.marker_value(BurndownDataConstants.DELTAS_BY_COMPONENT)
        self.assert_equals(dict(foo=3, bar=5), deltas)
    
    def test_stores_correct_component_metadata_if_confirm_commitment_is_pressed_twice(self):
        self.teh.enable_burndown_filter()
        self.create_change(delta=3, when=self.sprint.start, marker_key=Key.COMPONENT, marker_value='foo').save()
        self.confirmer.confirm_commitment_for_sprint(self.sprint, when=self.sprint.start)
        self.confirmer.confirm_commitment_for_sprint(self.sprint, when=self.sprint.start)
        
        self.assert_length(1, self.changes())
        change = self.changes()[0]
        deltas = change.marker_value(BurndownDataConstants.DELTAS_BY_COMPONENT)
        self.assert_equals(dict(foo=3), deltas)

