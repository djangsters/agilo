#   Copyright 2007 Andrea Tomasini <andrea.tomasini_at_agile42.com>
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
#       - Andrea Tomasini <andrea.tomasini__at__agile42.com>

import re

import agilo.utils.filterwarnings

from trac.core import Component, implements
from trac.util.translation import _

from agilo.ticket.model import AgiloTicket
from agilo.scrum.sprint import SprintModelManager
from agilo.scrum.team import TeamMemberModelManager
from agilo.scrum.workflow.api import IRule, RuleValidationException
from agilo.utils import Key, Status, Type
from agilo.utils.log import debug, error


class SprintAndMilestoneSyncRule(Component):
    """"
    Synchronize the Sprint and Milestone fields of a ticket, to make sure that
    when the sprint is changed a compatible milestone is also set. In case the 
    milestone is changed, reset the sprint field
    """
    implements(IRule)
    
    def validate(self, ticket):
        """Sets the milestone for this ticket given the Sprint name"""
        if ticket is None or not isinstance(ticket, AgiloTicket) or Key.SPRINT not in ticket.fields_for_type:
            return
        
        sprint_name = ticket[Key.SPRINT]
        sprint_did_change = self._set_correct_milestone_for_sprint(ticket, sprint_name)
        if sprint_did_change:
            return
        self._ensure_milestone_fits_to_sprint(ticket, sprint_name)
    
    def _sprint(self, sprint_name):
        return SprintModelManager(self.env).get(name=sprint_name)
    
    def _milestone_name_from_ticket(self, ticket):
        # AT: we have to check in the values directly, or the ticket will reply 
        # using the sprint.milestone
        return ticket.values.get(Key.MILESTONE)
    
    def _set_correct_milestone_for_sprint(self, ticket, sprint_name):
        pulled_task_into_sprint = (sprint_name is not None and len(ticket._old) == 0)
        moved_task_between_sprints = (Key.SPRINT in ticket._old and ticket._old[Key.SPRINT] != sprint_name)
        sprint_did_change = pulled_task_into_sprint or moved_task_between_sprints
        if not sprint_did_change:
            return False
        
        # The sprint is changed and has priority on the Milestone
        sprint = self._sprint(sprint_name)
        ticket_milestone = self._milestone_name_from_ticket(ticket)
        if sprint and ticket_milestone != sprint.milestone:
            ticket[Key.MILESTONE] = sprint.milestone
        elif sprint in (None, '') and (Key.MILESTONE not in ticket.fields_for_type):
            # The idea is that unplanning a task resets also the milestone field.
            ticket.values[Key.MILESTONE] = None
            ticket._old[Key.MILESTONE] = ticket_milestone
        return True
    
    def _ensure_milestone_fits_to_sprint(self, ticket, sprint_name):
        milestone_name = self._milestone_name_from_ticket(ticket)
        pulled_task_into_milestone = milestone_name is not None and Key.MILESTONE in ticket._old
        moved_task_between_milestones = (Key.SPRINT in ticket._old and ticket._old[Key.SPRINT] != sprint_name)
        milestone_did_change = pulled_task_into_milestone or moved_task_between_milestones
        if not milestone_did_change:
            return
        # Now checks if the milestone is compatible with the current set sprint
        # otherwise reset the sprint value
        sp_manager = SprintModelManager(self.env)
        sprints = [s.name for s in sp_manager.select(criteria={'milestone': milestone_name})]
        if not ticket[Key.SPRINT] in sprints:
            # The milestone is changed, and the sprint not, probably is an high
            #level re-planning, so reset the Sprint. 
            ticket[Key.SPRINT] = None


class ResetOwnerAndResourcesRule(Component):
    """
    Reset the fields owner and resources of a ticket with the fields owner and
    resources. In case the owner is empty the first resource will be promoted to
    owner
    """
    implements(IRule)
    
    def validate(self, ticket):
        """Accept only tickets with owner and resources fields"""
        debug(self, "Called validate(%s)..." % ticket)
        if ticket is not None and isinstance(ticket, AgiloTicket) and \
                Key.OWNER in ticket.fields_for_type and \
                Key.RESOURCES in ticket.fields_for_type:
            owner = ticket[Key.OWNER]
            resources = ticket.get_resource_list()
            if (owner is None or owner.strip() == '') and \
                    len(resources) > 0:
                ticket[Key.OWNER] = resources[0]
                ticket[Key.RESOURCES] = ', '.join([r.strip() for r in resources[1:] if r.strip() != ''])
            elif owner is not None and owner.strip() in resources:
                resources.remove(owner.strip())
                ticket[Key.RESOURCES] = ', '.join([r.strip() for r in resources if r.strip() != ''])
    

class OwnerIsATeamMemberRule(Component):
    """
    Checks if the owner and all resources of a ticket are also Team Members, 
    only for tickets with reamining_time property set.
    """
    
    implements(IRule)
    
    def check_team_membership(self, ticket, sprint, person, is_owner=False):
        from trac.ticket.api import TicketSystem
        if person not in [None, '', TicketSystem.default_owner.default]:
            err_string = is_owner and 'owner' or 'resource'
            tmmm = TeamMemberModelManager(self.env)
            teammember = tmmm.get(name=person)
            sprint_team_name = sprint.team.name
            if (teammember == None) or (teammember.team == None) or \
                (teammember.team.name != sprint_team_name):
                name = person
                error(self, "Rule didn't validate...")
                msg = _(u"The %s '%s' of ticket #%s doesn't belong to the team '%s' assigned to this sprint.")
                raise RuleValidationException(msg % (err_string, name, ticket.id, sprint_team_name))
    
    def validate(self, ticket):
        """Validate the ticket against the defined rules"""
        debug(self, "Called validate(%s)..." % ticket)
        if ticket is not None and isinstance(ticket, AgiloTicket) and \
                Key.REMAINING_TIME in ticket.fields_for_type:
            
            sprint_name = ticket[Key.SPRINT]
            if sprint_name not in (None, ''):
                sprint = SprintModelManager(self.env).get(name=sprint_name)
                if sprint and sprint.team is not None:
                    owner = ticket[Key.OWNER]
                    self.check_team_membership(ticket, sprint, owner, is_owner=True)
                    for r in ticket.get_resource_list():
                        self.check_team_membership(ticket, sprint, r)


class CloseTicketWithRemainingTimeZeroRule(Component):
    """
    Closes tickets supporting remaining_time as a key when it is set to 0, 
    set the remaining_time to 0 when tickets are closed as fixed
    """
    implements(IRule)
    
    def get_old_attribute(self, ticket, key, default=None):
        if getattr(ticket, '_old', None) is None:
            return None
        return ticket._old.get(key, default)
    
    def old_status(self, ticket):
        return self.get_old_attribute(ticket, Key.STATUS, Status.NEW)
    
    def old_remaining_time(self, ticket):
        return self.get_old_attribute(ticket, Key.REMAINING_TIME)
    
    def status_did_change(self, ticket):
        old_status = self.old_status(ticket)
        if old_status is None:
            return False
        return (old_status != ticket[Key.STATUS])
    
    def remaining_time_did_change(self, ticket):
        if self.old_remaining_time(ticket) is None:
            return False
        return (self.old_remaining_time(ticket) != ticket[Key.REMAINING_TIME])
    
    def parse_remaining_time(self, ticket):
        try:
            return float(ticket[Key.REMAINING_TIME])
        except (TypeError, ValueError):
            pass #Not a number
        return None
    
    def validate(self, ticket):
        """Accepts only tickets with remaining_time field"""
        debug(self, "Called validate(%s)..." % ticket)
        if ticket is not None and isinstance(ticket, AgiloTicket) and \
                ticket.is_writeable_field(Key.REMAINING_TIME):
            
            remaining_time = self.parse_remaining_time(ticket)
            if (not self.status_did_change(ticket)) and (not self.remaining_time_did_change(ticket)):
                return
            elif remaining_time is None:
                return
            
            ticket_was_closed = (self.old_status(ticket) == Status.CLOSED)
            ticket_is_now_closed = (ticket[Key.STATUS] == Status.CLOSED)
            if self.status_did_change(ticket) and ticket_is_now_closed and remaining_time != 0:
                ticket[Key.REMAINING_TIME] = '0'
            elif self.remaining_time_did_change(ticket) and (not ticket_was_closed) and remaining_time == 0:
                ticket[Key.STATUS] = Status.CLOSED
                ticket[Key.RESOLUTION] = Status.RES_FIXED


class CleanLettersFromRemainingTimeRule(Component):
    """
    Clean letters from the remaining time field. Otherwise several calculations
    may fail later (e.g. calculation of total remaining time) 
    """
    implements(IRule)
    
    extract_numbers_regex = re.compile('^\w*?(\d+(?:\.\d+)?)\w*?$')
    
    def validate(self, ticket):
        """Accept only tickets with remaining time field"""
        debug(self, "Called validate(%s)..." % ticket)
        if ticket is not None and isinstance(ticket, AgiloTicket) and \
                ticket.is_writeable_field(Key.REMAINING_TIME):
            remaining_time = ticket[Key.REMAINING_TIME] or ''
            match = self.extract_numbers_regex.match(remaining_time)
            if match != None:
                time_as_number = match.group(1)
                ticket[Key.REMAINING_TIME] = time_as_number
            else:
                ticket[Key.REMAINING_TIME] = None


class SetStoryInProgressWhenAtLeastOneTask(Component):
    """
    Sets story linked to tasks as 'in progress' when at least one of the tasks
    is in progress (which means is accepted by a Team Member)
    """
    implements(IRule)
    
    def validate(self, ticket):
        """Accept tickets which have story as parents and have remaninig time"""
        debug(self, "Called validate(%s)..." % ticket)
        if ticket is not None and isinstance(ticket, AgiloTicket) and \
                ticket.is_writeable_field(Key.REMAINING_TIME) and \
                ticket[Key.STATUS] == Status.ACCEPTED and \
                len(ticket.get_incoming()) > 0:
            # The ticket is a task or similar and has parents
            for p in ticket.get_incoming():
                if p.get_type() == Type.USER_STORY and \
                        p[Key.STATUS] != Status.ACCEPTED:
                    p[Key.STATUS] = Status.ACCEPTED
                    p.save_changes('agilo', 'Updated status, related task in progress')
