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

from trac.core import Component, implements
from trac.ticket.api import ITicketChangeListener

from agilo.scrum.burndown.model import BurndownDataChange
from agilo.utils import Key
from agilo.utils.constants import Status
from agilo.utils.days_time import now
from agilo.ticket.api import AgiloTicketSystem
from agilo.ticket.workflow_support import TicketHierarchyMover
from agilo.utils.config import AgiloConfig


# If the sprint backlog is not configured to show tasks - this class will fail. 
# It doesn't check the configuration data of the sprint backlog
class BurndownDataChangeListener(Component):

    implements(ITicketChangeListener)

    # -------------------------------------------------------------------------
    #    TICKET CREATION
    # -------------------------------------------------------------------------

    # ITicketChangeListener method
    def ticket_created(self, ticket):
        if not ticket.is_writeable_field(Key.SPRINT) or not ticket[Key.SPRINT]:
            return

        component = self._current_component(ticket)

        if ticket.is_writeable_field(Key.REMAINING_TIME) and ticket[Key.REMAINING_TIME]:
            self._record_value_change(ticket[Key.SPRINT], ticket[Key.REMAINING_TIME], component)

        if ticket.is_writeable_field(Key.STORY_POINTS) and ticket[Key.STORY_POINTS] and self._current_value(Key.STATUS, ticket) != Status.CLOSED:
            self._record_value_change(ticket[Key.SPRINT], ticket[Key.STORY_POINTS], component, Key.STORY_POINTS)

    def _record_value_change(self, sprint, point_change, component=None, fieldname=Key.REMAINING_TIME):
        if fieldname == Key.STORY_POINTS:
            change = BurndownDataChange.remaining_points_entry(self.env, point_change, sprint, now())
        else:
            change = BurndownDataChange.remaining_time_entry(self.env, point_change, sprint, now())

        if component is not None and AgiloConfig(self.env).is_filtered_burndown_enabled():
            change.update_marker(Key.COMPONENT, component)
        change.save()

    # -------------------------------------------------------------------------
    #    TICKET CHANGE
    # -------------------------------------------------------------------------

    def _process_value_changed(self, ticket, comment, author, old_values, fieldname=Key.REMAINING_TIME):
        current_sprint_name = self._current_sprint_name(ticket)
        previous_sprint_name = self._previous_sprint_name(ticket, old_values, current_sprint_name)
        current_value = self._current_float_value(ticket, fieldname)
        previous_value = self._previous_float_value(ticket, old_values, current_value, fieldname)
        current_component = self._current_component(ticket)
        previous_component = self._previous_component(ticket, old_values, current_component)

        if self._did_change_sprint_of_container(ticket, old_values):
            self._add_markers_and_move_children(ticket, current_sprint_name, previous_sprint_name, author)
            return

        if self._did_field_change(Key.COMPONENT, old_values) and AgiloConfig(self.env).is_filtered_burndown_enabled():
            self._record_change_if_necessary(previous_sprint_name, -previous_value, previous_component, fieldname)
            self._record_change_if_necessary(previous_sprint_name, previous_value, current_component, fieldname)

        if self._did_field_change(Key.SPRINT, old_values):
            self._record_change_if_necessary(previous_sprint_name, -previous_value, current_component, fieldname)
            self._record_change_if_necessary(current_sprint_name, current_value, current_component, fieldname)
        else:
            value_delta = current_value - previous_value
            self._record_change_if_necessary(current_sprint_name, value_delta, current_component, fieldname)

    def _process_status_changed(self, ticket, comment, author, old_values):
        if not (ticket.is_writeable_field(Key.STORY_POINTS) and ticket[Key.STORY_POINTS]):
            return

        current_value = self._current_value(Key.STATUS, ticket)
        previous_value = self._previous_value(Key.STATUS, ticket, old_values, current_value)

        component = self._current_component(ticket)

        if previous_value != Status.CLOSED and current_value == Status.CLOSED:
            # closing the story, burn down the points
            self._record_change_if_necessary(self._current_sprint_name(ticket),
                -self._current_float_value(ticket, Key.STORY_POINTS),
                component, Key.STORY_POINTS)
        elif previous_value == Status.CLOSED and current_value != Status.CLOSED:
            # re-opening the story, restore the points
            self._record_change_if_necessary(self._current_sprint_name(ticket),
                self._current_float_value(ticket, Key.STORY_POINTS),
                component, Key.STORY_POINTS)

    # ITicketChangeListener method
    def ticket_changed(self, ticket, comment, author, old_values):
        self._process_value_changed(ticket, comment, author, old_values, Key.REMAINING_TIME)
        self._process_value_changed(ticket, comment, author, old_values, Key.STORY_POINTS)
        self._process_status_changed(ticket, comment, author, old_values)

    def _did_change_sprint_of_container(self, ticket, old_values):
        return not ticket.is_task_like()\
        and self._did_field_change(Key.SPRINT, old_values)

    def _add_markers_and_move_children(self, container, current_sprint_name, previous_sprint_name, author):
        # REFACT: The recursion between the changelistener and the ticketmover
        # might create duplicate markers. For instance, if
        # a BUG references a STORY which references a TICKET.
        # This is not harmful due to the 'SKIP' semantic of the marker
        self._add_marker_if_neccessary(previous_sprint_name)
        self._add_marker_if_neccessary(current_sprint_name)
        self._move_children(container, previous_sprint_name, current_sprint_name, author)
        self._add_marker_if_neccessary(previous_sprint_name)
        self._add_marker_if_neccessary(current_sprint_name)

    def _move_children(self, ticket, source_sprint_name, target_sprint_name, author):
        mover = TicketHierarchyMover(self.env, ticket, source_sprint_name, target_sprint_name, author)
        mover.execute()

    def _add_marker_if_neccessary(self, sprint_name):
        if sprint_name is None:
            return

        BurndownDataChange.create_aggregation_skip_marker(self.env, sprint_name).save()

    def _current_sprint_name(self, ticket):
        # Sprint name cannot be empty, because that would not be a valid primary key
        # and we prevent that in the sprint creation GUI
        return self._current_value(Key.SPRINT, ticket) or None

    def _current_float_value(self, ticket, fieldname=Key.REMAINING_TIME):
        return float(self._current_value(fieldname, ticket) or 0)

    def _current_component(self, ticket):
        return self._current_value(Key.COMPONENT, ticket)

    def _current_value(self, fieldname, ticket):
        if not ticket.is_writeable_field(fieldname) or not ticket[fieldname]:
            return None
        return ticket[fieldname]

    def _previous_sprint_name(self, ticket, old_values, current_sprint_name):
        # empty sprint_name is verboten
        return self._previous_value(Key.SPRINT, ticket, old_values, current_sprint_name) or None

    def _previous_component(self, ticket, old_values, current_component):
        return self._previous_value(Key.COMPONENT, ticket, old_values, current_component) or None

    def _previous_float_value(self, ticket, old_values, current_float_value, key=Key.REMAINING_TIME):
        return float(self._previous_value(key, ticket, old_values, current_float_value) or 0)

    def _previous_value(self, fieldname, ticket, old_values, current_value):
        if self._did_field_change(fieldname, old_values):
            return old_values[fieldname]
        elif self._did_field_change(Key.TYPE, old_values) and self._previous_type_had_field(fieldname, old_values):
            previous_value = self._previous_value_from_history(fieldname, ticket)
            if previous_value is not None:
                return previous_value
        return current_value

    def _previous_type_had_field(self, fieldname, old_values):
        previous_type = old_values[Key.TYPE]
        ticket_system = AgiloTicketSystem(self.env)
        return fieldname in ticket_system.get_ticket_fieldnames(previous_type)

    def _previous_value_from_history(self, fieldname, ticket):
        changelog = ticket.get_changelog()
        field_changes = filter(lambda entry: entry[2] == fieldname, changelog)
        if len(field_changes) == 0:
            return None
        return field_changes[-1][4]

    def _did_field_change(self, fieldname, old_values):
        return fieldname in old_values

    def _record_change_if_necessary(self, sprint_name, value_delta, component=None, fieldname=Key.REMAINING_TIME):
        if value_delta == 0:
            return
        if sprint_name is None:
            return
        self._record_value_change(sprint_name, value_delta, component, fieldname)

    # -------------------------------------------------------------------------
    #    TICKET DELETION
    # -------------------------------------------------------------------------

    # ITicketChangeListener method
    def ticket_deleted(self, ticket):
        component = self._current_component(ticket)

        if ticket.is_writeable_field(Key.REMAINING_TIME) and ticket[Key.REMAINING_TIME]:
            self._record_change_if_necessary(self._current_sprint_name(ticket),
                -self._current_float_value(ticket),
                component)

        if ticket.is_writeable_field(Key.STORY_POINTS) and ticket[Key.STORY_POINTS] \
            and self._current_value(Key.STATUS, ticket) != Status.CLOSED:
            self._record_change_if_necessary(self._current_sprint_name(ticket),
                -self._current_float_value(ticket, Key.STORY_POINTS),
                component, Key.STORY_POINTS)
