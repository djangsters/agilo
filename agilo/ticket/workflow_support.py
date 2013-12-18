# -*- coding: utf-8 -*-
#   Copyright 2007-2008 Agile42 GmbH - Andrea Tomasini
#   Copyright 2011 Agilo Software GmbH All rights reserved 
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
# 
# Authors:
#     - Felix Schwarz <felix.schwarz__at__agile42.com>

from agilo.ticket import AgiloTicketSystem
from agilo.utils import Key, Status


class NoValue(object):
    pass
no_value = NoValue()

class TransitionFinder(object):
    
    def __init__(self, env, req, ticket):
        self.ats = AgiloTicketSystem(env)
        self.req = req
        self.ticket = ticket
        
        self._old_status_stack = []
        self._status_stack = []
        self.candidate_queue = None
        self.checked_status = None
    
    def get_status_after_ticket_changes(self, controller, action):
        changes = controller.get_ticket_changes(self.req, self.ticket, action)
        return changes.get('status')
    
    def _find_more_paths_from(self, status):
        final_action = None
        improvements = []
        for controller in self.ats.action_controllers:
            weighted_actions = sorted(controller.get_ticket_actions(self.req, self.ticket))
            for weight, action in weighted_actions:
                new_status = self.get_status_after_ticket_changes(controller, action)
                if (new_status in self.checked_status):
                    continue
                if self.is_perfect_match(new_status):
                    final_action = action
                    break
                elif self.is_improvement(new_status):
                    self.checked_status.add(new_status)
                    improvements.append((action, new_status))
        return (final_action, improvements)
    
    def _set_ticket_status_and_save_old_one(self, status):
        old_status = self.ticket._old.get(Key.STATUS, no_value)
        self._old_status_stack.append(old_status)
        self._status_stack.append(self.ticket[Key.STATUS])
        
        self.ticket[Key.STATUS] = status
        self.ticket._old[Key.STATUS] = status
    
    def _restore_ticket_status(self):
        self.ticket[Key.STATUS] = self._status_stack.pop()
        last_value = self._old_status_stack.pop()
        if last_value is no_value:
            del self.ticket._old[Key.STATUS]
        else:
            self.ticket._old[Key.STATUS] = last_value
    
    def _get_list_of_actions(self, current_path, final_action):
        actions = [action for (action, new_state) in current_path]
        return actions + [final_action]
    
    def _put_candidates_in_queue(self, current_path, candidates):
        for item in candidates:
            candidate = current_path + [item]
            self.candidate_queue.append(candidate)
    
    def _explore_level_and_store_new_candidates(self, current_status, path):
        self._set_ticket_status_and_save_old_one(current_status)
        final_action, candidates = self._find_more_paths_from(current_status)
        self._restore_ticket_status()
        if final_action is not None:
            return self._get_list_of_actions(path, final_action)
        self._put_candidates_in_queue(path, candidates)
        return None
    
    def _find_path_to_expected_status(self):
        current_status = self.ticket[Key.STATUS]
        if self.is_perfect_match(current_status):
            return []
        path = []
        self.candidate_queue = []
        self.checked_status = set([current_status, None])
        
        action_series = self._explore_level_and_store_new_candidates(current_status, path)
        if action_series is not None:
            return action_series
        
        while len(self.candidate_queue) > 0:
            path = self.candidate_queue.pop(0)
            last_status = path[-1][1]
            
            action_series = self._explore_level_and_store_new_candidates(last_status, path)
            if action_series is not None:
                return action_series
        
        #raise AssertionError('No suitable transition found!')
        return None
    
    def transition_to_in_progress_state(self):
        return self.transition_to_custom_in_progress_state(Status.ACCEPTED)
    
    def transition_to_custom_in_progress_state(self, custom_in_progress_state):
        def is_perfect_match(new_status):
            return new_status == custom_in_progress_state
        
        def is_improvement(new_status):
            return new_status not in ['new', 'closed']
        
        self.is_perfect_match = is_perfect_match
        self.is_improvement = is_improvement
        return self._find_path_to_expected_status()
    
    def transition_to_closed_state(self):
        def is_perfect_match(new_status):
            return new_status == 'closed'
        
        def is_improvement(new_status):
            return new_status != 'new'
        self.is_perfect_match = is_perfect_match
        self.is_improvement = is_improvement
        return self._find_path_to_expected_status()
    
    def transition_to_new_state(self):
        def is_perfect_match(new_status):
            return new_status == 'new'
        
        def is_improvement(new_status):
            return new_status != 'closed'
        self.is_perfect_match = is_perfect_match
        self.is_improvement = is_improvement
        return self._find_path_to_expected_status()


class TicketStatusManipulator(object):
    
    DEFAULT_SIMPLE_STATUSES = ['new', 'in_progress', 'closed']
    
    def __init__(self, env, req, ticket):
        self.req = req
        self.env = env
        self.ticket = ticket
        self.simple_status = None
    
    def _get_action_controllers_for_action(self, action):
        def _get_actions_for(controller):
            weighted_actions = controller.get_ticket_actions(self.req, self.ticket)
            actions = [action for (weight, action) in weighted_actions]
            return actions
        
        controllers = []
        ats = AgiloTicketSystem(self.env)
        for controller in ats.action_controllers:
            if action in _get_actions_for(controller):
                controllers.append(controller)
        return controllers
    
    def _apply_changes_for_transition(self, transition):
        for action in transition:
            controller_changes = {}
            for controller in self._get_action_controllers_for_action(action):
                changes = controller.get_ticket_changes(self.req, self.ticket, action)
                controller_changes.update(changes)
            for field_name, value in controller_changes.items():
                self.ticket[field_name] = value
    
    def _find_transition_to(self):
        finder = TransitionFinder(self.env, self.req, self.ticket)
        
        transition = None
        if self.simple_status == 'new':
            transition = finder.transition_to_new_state()
        elif self.simple_status == 'in_progress':
            transition = finder.transition_to_in_progress_state()
        elif self.simple_status == 'closed':
            transition = finder.transition_to_closed_state()
        else:
            transition = finder.transition_to_custom_in_progress_state(self.simple_status)
        return transition
    
    def _force_new_status(self):
        if self.simple_status == 'new':
            self.ticket[Key.STATUS] = Status.NEW
            self.ticket[Key.OWNER] = ''
            self.ticket[Key.RESOLUTION] = ''
        elif self.simple_status == 'in_progress':
            self.ticket[Key.STATUS] = Status.ACCEPTED
            self.ticket[Key.RESOLUTION] = ''
            self.ticket[Key.OWNER] = self.req.authname
        elif self.simple_status == 'closed':
            self.ticket[Key.STATUS] = Status.CLOSED
            self.ticket[Key.RESOLUTION] = Status.RES_FIXED
        else:
            self.ticket[Key.STATUS] = self.simple_status
            self.ticket[Key.RESOLUTION] = ''
            self.ticket[Key.OWNER] = self.req.authname
            
    
    def change_status_to(self, simple_status):
        """Change the ticket's status to the given 'simple status' (only new,
        in_progress, closed). Tries to use trac's workflow mechanism but will 
        fall back to brute force if necessary.
        Return True if changes were made to the ticket, otherwise False (e.g. 
        when the ticket was already in the target state)."""
        self.simple_status = simple_status
        transition = self._find_transition_to()
        if transition is None:
            self._force_new_status()
        elif len(transition) > 0:
            self._apply_changes_for_transition(transition)
        else:
            # ticket is already in a good state
            return False
        return True

class TicketHierarchyMover(object):

    def __init__(self, env, ticket, source_sprint_name, target_sprint_name, changelog_author='agilo'):
        self.env = env
        self.ticket = ticket
        # Trac treats None and empty string the same for custom fields
        self.source_sprint_name = source_sprint_name or ''
        self.target_sprint_name = target_sprint_name or ''
        self.changelog_author = changelog_author
    
    def execute(self):
        for ticket in self._all_children():
            if self._should_move_child(ticket):
                self._move_child(ticket)
    
    def _all_children(self):
        return self._all_children_for_ticket(self.ticket)
    
    def _all_children_for_ticket(self, ticket):
        all_children = set()
        for child in ticket.get_outgoing():
            all_children.add(child)
            all_children.update(self._all_children_for_ticket(child))
        return all_children
    
    def _should_move_child(self, ticket):
        if ticket[Key.STATUS] == Status.CLOSED \
            or not ticket.is_writeable_field(Key.SPRINT):
            return False
        
        sprint = ticket[Key.SPRINT] or '' # trac returns None if the sprint was never set
        return sprint == self.source_sprint_name
    
    def _move_child(self, ticket):
        ticket[Key.SPRINT] = self.target_sprint_name
        ticket.save_changes(self.changelog_author,
                            'Referencing ticket #%s has changed sprint.' % self.ticket.id)
    
