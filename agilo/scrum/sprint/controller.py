# -*- encoding: utf-8 -*-
#   Copyright 2007-2009 Agile42 GmbH - Andrea Tomasini
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
#       - Felix Schwarz <felix.schwarz_at_agile42.com>

from datetime import time, timedelta

from trac.util.datefmt import utc

from agilo.api import controller, validator
from agilo.api import ValueObject

from agilo.scrum.sprint.model import SprintModelManager, Sprint
from agilo.scrum.team.model import TeamModelManager
from agilo.ticket import TicketController
from agilo.utils import Key, Status, log
from agilo.utils.days_time import midnight, now

__all__ = ['SprintController']

class SprintController(controller.Controller):
    """Take care of processing any command related to a Sprint"""
    
    def __init__(self):
        """Initialize the component, sets some references to needed
        Model Managers"""
        self.sp_manager = SprintModelManager(self.env)
        self.tm_manager = TeamModelManager(self.env)
    
    
    class ListSprintsCommand(controller.ICommand):
        """Command to fetch a list of Sprints fulfilling certain 
        criteria"""
        parameters = {'criteria': validator.DictValidator, 
                      'order_by': validator.IterableValidator, 
                      'limit': validator.IntValidator}
        
        def _execute(self, sp_controller, date_converter, as_key):
            """Execute the listing command, returns a list of sprints, 
            if the set criteria is None, it returns all the sprints, 
            otherwise only the sprints matching the criteria"""
            result = []
            sprints = sp_controller.sp_manager.select(criteria=self.criteria,
                                                      order_by=self.order_by or \
                                                      ['start'],
                                                      limit=self.limit)
            for sprint in sprints:
                result.append(self.return_as_value_object(sprint, 
                                                  date_converter, 
                                                  as_key))
            return result
    
    
    class GetSprintCommand(controller.ICommand):
        """Command to get a sprint for a given name"""
        parameters = {'sprint': validator.MandatorySprintValidator}
        
        def _execute(self, sp_controller, date_converter, as_key):
            """Returns the sprint for the given name if existing or None"""
            return self.return_as_value_object(self.sprint, date_converter, as_key)
    
    
    class DeleteSprintCommand(GetSprintCommand):
        """Command to delete a sprint"""
        def _execute(self, sp_controller, date_converter, as_key):
            # AT: the delete on PersistentObject can still raise an
            # UnableToDeletePersistentObject Exception, that will be
            # caught by the Controller.process_command and wrapped
            # into a CommandError.
            if not sp_controller.sp_manager.delete(self.sprint):
                raise self.CommandError("Error deleting Sprint: %s" % \
                                        self.sprint)
    
    
    class CreateSprintCommand(controller.ICommand):
        """Command to create a new Sprint"""
        
        parameters = {'name': validator.NonExistantSprintNameValidator, 
                      'milestone': validator.MandatoryStringValidator, 
                      'start': validator.MandatoryUTCDatetimeValidator, 
                      'end': validator.UTCDatetimeValidator, 
                      'duration': validator.IntValidator, 
                      'team': validator.TeamValidator, 
                      'description': validator.StringValidator}
        
        def consistency_validation(self, env):
            """
            Validate the consistency of dates and duration together,
            the individual parameter format validation has already
            occurred, now we check the relation between them, in
            particular:
                start < end
                if end is not present, duration must be
                if duration is not present, end must be
            """
            if self.end and self.start and self.start >= self.end:
                self.not_valid("Start date after end date?", 
                               'Consistency error', self.start)
            if not self.end and not self.duration:
                self.not_valid("Either end or a duration must "\
                               "be specified", 'Consistency Error', 
                               self.end)
            if self.end is not None:
                self.duration = None

        def _prepare_params(self):
            """Prepares the params to be send to the model manager"""
            params = dict()
            params['save'] = getattr(self, 'save', True)
            
            for attr_name in ('name', 'description', 'milestone',
                              # We assume dates are valid and have been 
                              # converted by the validation.
                              'start', 'end', 
                              # Duration and team have been converted
                              # by the validators
                              'duration', 'team'):
                # There should always be either name or sprint, not
                # both, but to the manager we need to give a name
                value = getattr(self, attr_name, None)
                if attr_name == 'name':
                    if hasattr(value, 'name'):
                        value = value.name
                    elif not value:
                        value = getattr(self, 'sprint', None)
                params[attr_name] = value
            return params

        def _execute(self, sp_controller, date_converter, as_key):
            """Creates a new Sprint object, if there is the save 
            option, is also saving it, otherwise not"""
            params = self._prepare_params()
            sprint = sp_controller.sp_manager.create(**params)
            return self.return_as_value_object(sprint, date_converter, as_key)


    class SaveSprintCommand(controller.ICommand):
        # REFACT: Hand in the new name + a sprint, old_sprint is confusing
        parameters = {
                      'sprint': validator.SprintNameValidator,
                      'old_sprint': validator.SprintValidator,
                      'milestone': validator.MandatoryStringValidator, 
                      'start': validator.MandatoryUTCDatetimeValidator, 
                      'end': validator.UTCDatetimeValidator, 
                      'duration': validator.IntValidator, 
                      'team': validator.TeamValidator, 
                      'description': validator.StringValidator}
        
        def consistency_validation(self, env):
            """We need to check that either sprint or old_sprint are
            set and are valid sprints"""
            if self.sprint == self.old_sprint:
                self.old_sprint = None
            sprint_contains_sprint = isinstance(self.sprint, Sprint)
            old_sprint_contains_sprint = isinstance(self.old_sprint, Sprint)
            if not sprint_contains_sprint and not old_sprint_contains_sprint:
                self.not_valid("No valid sprint found", "sprint", 
                               (self.sprint, self.old_sprint))
            if sprint_contains_sprint and old_sprint_contains_sprint:
                self.not_valid("Sprint '%s' already exists.", "sprint", 
                               (self.old_sprint.name))
            # check that the duration and end date are not both
            # present in which case consider only the changed value
            if self.end is not None and self.duration is not None:
                sprint = self.old_sprint or self.sprint
                if self.end != sprint.end:
                    # It is changed, so remove the duration
                    self.duration = None
                elif self.duration != sprint.duration:
                    # it is changed, so remove the end
                    self.end = None
                else:
                    # nothing changed so remove both
                    self.duration = self.end = None
        
        def _sprint_with_new_name(self):
            # check if the sprint has been renamed or not
            if isinstance(self.sprint, Sprint):
                return self.sprint
            # We know it's actually a rename (check consistency validation) so 
            # self.sprint is just a name
            sprint = self.old_sprint
            new_sprint_name = self.sprint
            
            sprint.name = new_sprint_name
            return sprint
        
        def _execute(self, sp_controller, date_converter, as_key):
            sprint = self._sprint_with_new_name()
            for attr_name in self.parameters:
                if hasattr(sprint, attr_name):
                    sprint_attr_value = getattr(sprint, attr_name)
                    if not callable(sprint_attr_value):
                        value = getattr(self, attr_name)
                        if value:
                            setattr(sprint, attr_name, value)
            return sp_controller.sp_manager.save(sprint)
    
    
    class RetargetTicketsCommand(controller.ICommand):
        """Command to retarget all the open tickets from a Sprint to 
        another. Tickets to the specified sprint (all tickets with a 
        status different from 'closed' are considered as incomplete).
        If specified, 'author' will be used as username who did the 
        change.
        
        Will retarget all stories where nobody has worked on.
        Will not retarget stories automatically where somebody has 
        already worked on, as it needs to be looked at in the sprint 
        review / planning.
        """
        # REFACT: consider to either not move anything or also move stories that were not finished.
        # Andrea noted that in vanilla scrum you don't want automatic movement, as this encourages the team to do commitments that they can't keep.
        parameters = {'sprint': validator.MandatorySprintValidator, 
                      'retarget': validator.MandatorySprintValidator, 
                      'author': validator.StringValidator}

        def _has_at_least_a_closed_child(self, ticket, backlog_ids):
            for child in ticket.get_outgoing():
                if child[Key.STATUS] == Status.CLOSED and \
                    child.id in backlog_ids:
                        return True
                else:
                    return self._has_at_least_a_closed_child(child, backlog_ids)
            return False

        def _execute(self, sp_controller, date_converter, as_key):
            from agilo.scrum.backlog import BacklogModelManager
            bmm = BacklogModelManager(sp_controller.env)
            sprint_backlog = bmm.get(name=Key.SPRINT_BACKLOG, 
                                     scope=self.sprint.name)
            if sprint_backlog is not None:
                backlog_items = sprint_backlog.values()
                backlog_items_ids = [bi.ticket.id for bi in backlog_items]
                for bi in backlog_items:
                    if (bi[Key.STATUS] == Status.CLOSED) or \
                            self._has_at_least_a_closed_child(bi.ticket, backlog_items_ids):
                        # This container already had work on it started. Therefore we leave it in 
                        # this sprint to make clear that this is the sprint the story was started. 
                        # (to retain historical data)
                        
                        # In this case we just leave the ticket where it was
                        # No sense in deleting the BacklogItem, as it will be recreated anyway on the next load
                        # (Deleting the sprint from the ticket would delete the BacklogItem)
                        continue
                    elif (bi[Key.SPRINT] == self.sprint.name):
                        log.info(sp_controller.env,
                                 u'Retargeting ticket %d to sprint %s' % \
                                 (bi.ticket.id, self.retarget.name))
                        # changing the ticket is enough to move the backlog item to the
                        # new backlog as the BacklogUpdater will do that
                        bi.ticket[Key.SPRINT] = self.retarget.name
                        bi.ticket.save_changes(author=self.author,
                                               comment='Moved from sprint %s' % self.sprint.name)
                    else:
                        # This wasn't specifically planned and has not closed
                        # child left, therefore we can remove it
                        sprint_backlog.remove(bi)
    
    class GetTicketsStatisticsCommand(controller.ICommand):
        """
        Returns the ticket statistics for a given sprint, in the form
        of a dictionary with key the ticket types and as value a tuple
        with planned, in progress and closed. E.g.:
        
            {'story': (12, 2, 8), 'task': (40, 5, 24)}
        
        If the option totals is set to True, than only a tuple with
        the total tickets count is returned:
        
            (12, 3, 8) # open, in progress, closed
        
        """
        parameters = {'sprint': validator.MandatorySprintValidator, 
                      'totals': validator.BoolValidator}
        
        def _tickets(self, sp_controller):
            from agilo.scrum.backlog import BacklogModelManager
            backlog_manager = BacklogModelManager(sp_controller.env)
            backlog = backlog_manager.get(name=Key.SPRINT_BACKLOG, scope=self.sprint.name)
            fetched_tickets = [backlogitem.ticket for backlogitem in backlog]
            return fetched_tickets
        
        def _count_totals(self, tickets):
            nr_planned, nr_in_progress, nr_closed = (0, 0, 0)
            for ticket in tickets:
                if ticket[Key.STATUS] == Status.CLOSED:
                    nr_closed += 1
                elif ticket[Key.STATUS] == Status.NEW:
                    nr_planned += 1
                else:
                    nr_in_progress += 1
            return (nr_planned, nr_in_progress, nr_closed)
        
        def _use_non_mutable_iterables(self, ticket_data):
            for t_type, stats in ticket_data.items():
                ticket_data[t_type] = tuple(stats)
            return ticket_data
        
        def _count_tickets_by_type(self, tickets):
            ticket_data = dict()
            for ticket in tickets:
                t_type = ticket.get_type()
                stats_per_type = ticket_data.setdefault(t_type, [0, 0, 0])
                if ticket[Key.STATUS] == Status.CLOSED:
                    stats_per_type[2] += 1
                elif ticket[Key.STATUS] == Status.NEW:
                    stats_per_type[0] += 1
                else:
                    stats_per_type[1] += 1
            return self._use_non_mutable_iterables(ticket_data)
        
        def _execute(self, sp_controller, date_converter, as_key):
            fetched_tickets = self._tickets(sp_controller)
            if self.totals:
                return self._count_totals(fetched_tickets)
            else:
                return self._count_tickets_by_type(fetched_tickets)


    class ListTicketsHavingPropertiesCommand(TicketController.ListTicketsCommand):
        """
        Returns a list of all the tickets belonging to a Sprint, and
        having a specified list of properties.
        """
        parameters = {'sprint': validator.MandatorySprintValidator, 
                      'properties': validator.IterableValidator, 
                      'criteria': validator.DictValidator, 
                      'order_by': validator.IterableValidator, 
                      'limit': validator.IntValidator}
        
        def _execute(self, sp_controller, date_converter, as_key):
            """Execute the query on the TicketController"""
            if not self.criteria:
                self.criteria = {}
            self.with_attributes = self.properties
            self.criteria.update({'sprint': self.sprint.name})
            # Now return the superclass execute, giving it the right
            # controller
            return super(self.__class__, self)._execute(TicketController(sp_controller.env))
    
    class GetRemainingTimeSeriesForTicketsInSprintCommand(controller.ICommand):
        """This is some kind of 'abstract' super class for different commands.
        The public functional build_remaining_time_series_for_interval returns
        a dictionary (task -> [(day, remaining time)]) which is used by
        other commands to produce some aggregated views without replicating
        much of the tedious work every time.
        """
        parameters = {}
        
        def _get_tickets_with_attribute(self, tc, env, backlog, attribute):
            cmd = TicketController.FilterTicketsWithAttribute(env,
                      tickets=backlog, attribute_name=attribute)
            cmd.native = True
            return tc.process_command(cmd)

        def _get_orphan_tasks(self, tc, env, backlog):
            cmd = TicketController.FindOrphanTasks(env, 
                                                   tickets=backlog)
            cmd.native = True
            return tc.process_command(cmd)
        
        def _remaining_times_for(self, start, end, get_remaining_time, interval_duration):
            """Return a series of remaining times in the given interval 
            [start, end]. This function takes care of interpolating/aggregating
            values, there will be one data point per <interval_duration> (a
            timedelta instance).
            
            get_remaining_time is a callable which returns the remaining time
            as number for the passed datetime."""
            rt_series = []
            current_time = start
            while (current_time < end) or (start == end and current_time <= end):
                remaining_time = get_remaining_time(current_time)
                rt_series.append((current_time, remaining_time))
                current_time += interval_duration
            return rt_series
        
        def _get_remaining_time_series_for_ticket(self, start, end, today, 
                                             get_remaining_time, append_current_time, interval_duration=timedelta(days=1)):
            """Return the remaining time series for this ticket within the 
            specified interval. Today is the date of today so that his does not
            have to be computed every time (prevents tz-related errors).
            
            get_remaining_time is a callable which returns the remaining time
            as number for the passed datetime."""
            faked_start = midnight(start)
            rt_series = self._remaining_times_for(faked_start, end, get_remaining_time, interval_duration)
            if len(rt_series) > 0:
                rt_series[0] = (start, get_remaining_time(start))
            
            if append_current_time and (midnight(today) < end) and (start != end):
                # dates are used as keys later so we have to use a datetime
                # with exactly the same microsecond attribute!
                rt_series.append((today, get_remaining_time()))
            return rt_series
        
        def _get_remaining_time_series_for_task(self, env, start, end, today, 
                                                task, append_current_time, interval_duration):
            """Return the remaining time series for this task within the 
            specified interval. Today is the date of today so that his does not
            have to be computed every time (prevents tz-related errors)."""
            # TODO: Fixme - use some kind of ModelManager?
            from agilo.scrum import RemainingTime
            rt_store = RemainingTime(env, task)
            return self._get_remaining_time_series_for_ticket(start, end, today, 
                                     rt_store.get_remaining_time, append_current_time, interval_duration)
        
        def _get_remaining_times_series_for_tasks(self, env, tasks, start, end, 
                                                  today, append_current_time, interval_duration):
            rt_series_by_task = {}
            for task in tasks:
                series = self._get_remaining_time_series_for_task(env, start, 
                                                end, today, task, append_current_time, interval_duration)
                rt_series_by_task[task] = series
            return rt_series_by_task
        
        def _get_remaining_time_series_for_stories(self, stories, start, end, 
                                                   today, append_current_time, interval_duration):
            rt_series = {}
            for story in stories:
                # AT: this is not enough we have to check that the tasks linked
                # to the story are either planned for the current sprint or not
                # planned at all
                # FIXME (AT): one of our customer had a problem with some moved
                # stories from an old sprint, as those stories will not pass the
                # check, if the tasks are planned for the new Sprint, and will
                # get summed for the tasks remaining time as for the estimated
                # remaining time, making the total and the burndown look wrong.
                story_is_broken_down = (len([task for task in story.get_outgoing() if \
                                             task[Key.SPRINT] in (story[Key.SPRINT], '')]) > 0)
                # If a story has some tasks in other sprints, do not use
                # ESTIMATED_REMAINING_TIME - even if none of these tasks is 
                # planned for this sprint
                if not story_is_broken_down:
                    estimated_remaining_time = story[Key.ESTIMATED_REMAINING_TIME]
                    get_remaining = lambda x=None: estimated_remaining_time or 0
                    series = self._get_remaining_time_series_for_ticket(start, 
                                       end, today, get_remaining, append_current_time, interval_duration)
                    rt_series[story] = series
            return rt_series
        
        def _get_backlog(self, env, sprint):
            from agilo.scrum.backlog import BacklogModelManager
            backlog = BacklogModelManager(env).get(name=Key.SPRINT_BACKLOG, 
                                                   scope=sprint.name)
            return backlog
        
        def _get_tasks_for_story(self, env, sp_controller, 
                                 sprint_name, story, backlog):
            """Returns the list of tasks for the given story, that are in 
            the current sprint backlog"""
            cmd = SprintController.GetReferencedTasksInThisSprintCommand(env,
                          story=story, sprint=sprint_name, tickets=backlog)
            cmd.native = True
            tasks = sp_controller.process_command(cmd)
            return tasks
        
        def stories_and_tasks_for_sprint(self, env, sprint, controller):
            "Return a tuple (stories, list of all tasks) for the given sprint. "
            def tasks_for(story):
                return self._get_tasks_for_story(env, controller, sprint.name, story, backlog)
            
            tc = TicketController(env)
            # AT: we have to check if the command received tickets or
            # not. In case there are no tickets we will get the full
            # backlog
            backlog = self.tickets or self._get_backlog(env, sprint)
            stories = self._get_tickets_with_attribute(tc, env, backlog, 
                                                Key.ESTIMATED_REMAINING_TIME)
            orphan_tasks = self._get_orphan_tasks(tc, env, backlog)
            story_tasks = [tasks_for(story) for story in stories]
            all_tasks = orphan_tasks + reduce(lambda x, y: x+y, story_tasks, [])
            return stories, all_tasks
        
        def build_remaining_time_series_for_interval(self, env, start, end, 
                                     sprint, sp_controller, append_current_time, interval_duration):
            """Return a dictionary of tuples
                  ticket -> (datetime, remaining time)
               for the tickets in the given sprint.
            """
            stories, all_tasks = self.stories_and_tasks_for_sprint(env, sprint, sp_controller)
            
            today = now(tz=utc)
            rt_series_by_task = \
                self._get_remaining_times_series_for_tasks(env, all_tasks, 
                                               start, end, today, append_current_time, interval_duration)
            rt_series_by_story = \
                self._get_remaining_time_series_for_stories(stories, start, 
                                                      end, today, append_current_time, interval_duration)
            rt_series_by_task.update(rt_series_by_story)
            return rt_series_by_task
    
    
    class GetRemainingTimesCommand(GetRemainingTimeSeriesForTicketsInSprintCommand):
        """Returns a list of remaining time for each day of the sprint 
        until the end of the sprint.
        
        If cut_to_today is True (default), the list will not contain 
        any items for days in the future.
        
        If commitment is given, the remaining time for the first 
        sprint day is set to the specified commitment.
        
        If tickets are given, this command won't fetch the tickets for 
        the sprint but uses just this list of tickets (performance 
        optimization)."""
        # FIXME: (AT) To be able to decide when the remaining time belongs
        # to one day of the sprint or another, we need to know in which timezone
        # we are calculating the day. So it might be very unfortunate to assume
        # the days end in UTC timezone. I suggest we either pass through the
        # information or we send back all the entries by datetime.
        parameters = {'sprint': validator.MandatorySprintValidator, 
                      'cut_to_today': validator.BoolValidator, 
                      'commitment': validator.IntOrFloatValidator, 
                      'tickets': validator.IterableValidator}
        
        def is_filtered_backlog(self):
            return (getattr(self.tickets, 'filter_by', None) is not None)
        
        def _sort_chronologically_and_convert_to_objects(self, remaining_time_by_day):
            remaining_times = []
            for when in sorted(remaining_time_by_day.keys()):
                remaining_times.append(ValueObject(when=when, remaining_time=remaining_time_by_day[when]))
            return remaining_times
        
        def _sum_remaining_time_per_day(self, rt_series_by_task):
            remaining_time_by_day = {}
            for rt_series in rt_series_by_task.values():
                for when, remaining_time in rt_series:
                    remaining_time_by_day.setdefault(when, 0)
                    remaining_time_by_day[when] += remaining_time
            return remaining_time_by_day
        
        def _get_remaining_times_for_interval(self, env, start, end, sprint, 
                                              sp_controller, append_current_time, 
                                              interval_duration=timedelta(days=1)):
            rt_series_by_task = self.build_remaining_time_series_for_interval(env, start, end, 
                                    sprint, sp_controller, append_current_time, interval_duration)
            remaining_time_by_day = self._sum_remaining_time_per_day(rt_series_by_task)
            return self._sort_chronologically_and_convert_to_objects(remaining_time_by_day)
        
        def _inject_commitment(self, actual_burndown, commitment):
            if (commitment is not None) and not self.is_filtered_backlog():
                actual_burndown[0].remaining_time = commitment
        
        def _transform_to_old_structure(self, actual_burndown):
            old_structure = []
            for item in actual_burndown:
                old_structure.append(item.remaining_time)
            return old_structure
        
        def _execute(self, sp_controller, date_converter, as_key):
            # AT: I am not sure how much more readable the code is by duplicating
            # variables...
            commitment = self.commitment
            env = sp_controller.env
            today = now(tz=utc)
            sprint = self.sprint
            start = sprint.start
            end = sprint.end
            # FIXME: (AT) I am not sure that cut_to_today is True by default,
            # as stated in the comment of the method. As far as I can see it is
            # rather False by default, the validator checks for not None so if 
            # it would be None would be evaluated as False, and not as True
            if self.cut_to_today:
                end = min(end, midnight(today + timedelta(days=1)))
            actual_burndown = self._get_remaining_times_for_interval(env, 
                                 start, end, sprint, sp_controller, self.cut_to_today)
            self._inject_commitment(actual_burndown, commitment)
            return self._transform_to_old_structure(actual_burndown)
    
    
    class GetTotalRemainingTimeCommand(GetRemainingTimesCommand):
        """Returns the total current remaining time for this sprint, 
        summing up the remaining time of estimated tasks."""
        parameters = {'sprint': validator.MandatorySprintValidator,
                      'day': validator.UTCDatetimeValidator,
                      'commitment': validator.IntOrFloatValidator,
                      'tickets': validator.IterableValidator}
        
        def _execute(self, sp_controller, date_converter, as_key):
            today = now(tz=utc) 
            day = self.day or today
            actual_burndown = \
                self._get_remaining_times_for_interval(sp_controller.env, day, 
                        day, self.sprint, sp_controller, append_current_time=True)
            self._inject_commitment(actual_burndown, self.commitment)
            return sum(self._transform_to_old_structure(actual_burndown))
    
    
    class GetReferencedTasksInThisSprintCommand(controller.ICommand):
        """Returns the referenced tasks planned in this sprint related
        to the given story"""
        
        parameters = {'sprint': validator.MandatorySprintValidator,
                      'story': validator.MandatoryTicketValidator,
                      'tickets': validator.IterableValidator}
        
        def get_referenced_tickets(self, parent):
            linked_tickets = parent.get_outgoing()
            if self.tickets is not None:
                tickets_for_story = []
                linked_ids = [t.id for t in linked_tickets]
                for ticket_or_bi in self.tickets:
                    if not getattr(ticket_or_bi, 'is_visible', True):
                        continue
                    ticket = getattr(ticket_or_bi, 'ticket', ticket_or_bi)
                    if ticket.id in linked_ids:
                        tickets_for_story.append(ticket)
            else:
                tickets_for_story = linked_tickets
            return tickets_for_story
        
        def _execute(self, sp_controller, date_converter, as_key):
            """Return a list of tasks (tickets with remaining time) 
            which are referenced by 'story' and which are not planned 
            or planned for the given sprint. 
            If the tickets parameter was given, only return tasks 
            which are also in this list of tickets."""
            # FS: In case that we need to filter the backlog by an 
            # additional attribute ('component backlog'), we need to 
            # check bi.is_visible in order not to duplicate the whole 
            # filtering logic here. We already extended 
            # get_tickets_with_attribute to return only tickets that 
            # should be displayed. So we take advantage of this here 
            # by passing the backlog (all_tickets).
            tasks = []
            for ticket in self.get_referenced_tickets(self.story):
                if ticket.is_readable_field(Key.REMAINING_TIME) and \
                    ticket[Key.SPRINT] in (None, '', self.sprint.name):
                    tasks.append(ticket)
            return tasks
    
    
    class GetSprintOptionListCommand(ListSprintsCommand):
        """Returns 3 lists containing the sprints which have been 
        closed, the one currently running and finally the one still to 
        start. Normally used to prepare the field option group to show 
        the sprint grouped by status."""
        
        parameters = {'criteria': validator.DictValidator, 
                      'order_by': validator.IterableValidator, 
                      'limit': validator.IntValidator,
                      'sprint_names': validator.IterableValidator}
        
        def _execute(self, sp_controller, date_converter, as_key):
            """Returns 3 lists containing the sprints which have been 
            closed, the one currently running and finally the one 
            still to start. This method is normally used to prepare 
            the field option group to show the sprint grouped."""
            closed = list()
            running = list()
            to_start = list()
            sprint_names = getattr(self, "sprint_names", None)
            criteria = getattr(self, "criteria", None)
            if sprint_names:
                if not criteria:
                    criteria = {}
                criteria.update({'name': 'in %s' % sprint_names})
            # check the given sprints
            sprints = super(self.__class__, self)._execute(sp_controller,
                                                           date_converter,
                                                           as_key)
            for s in sprints:
                if s.is_currently_running:
                    running.append(s.name)
                elif s.is_closed:
                    closed.append(s.name)
                else:
                    to_start.append(s.name)
            return closed, running, to_start
    
    
    class GetResourceLoadForDevelopersInSprintCommand(GetRemainingTimeSeriesForTicketsInSprintCommand):
        """Return a list of developers with information about their 
        load (based on the remaining time of their accepted tasks) for 
        every day in the sprint."""
        
        parameters = {'sprint': validator.MandatorySprintValidator,
                      'tickets': validator.IterableValidator}
        
        def _extrapolate_load_data_for_single_developer(self, developer, end):
            if developer.load is not None:
                one_day = timedelta(days=1)
                
                dummy_load = developer.load[-1].copy()
                dummy_load.day = None
                dummy_load.is_overloaded = None
                dummy_load.is_working_day = None
                
                day = developer.load[-1].day
                while day < end:
                    day = min(day + one_day, end)
                    load_info = dummy_load.copy()
                    load_info.day = day
                    developer.load.append(load_info)
        
        def _extrapolate_load_data_for_developers(self, developers, 
                                                  end):
            """Extrapolate the load data for the rest of the sprint for all
            developers."""
            for developer in developers:
                self._extrapolate_load_data_for_single_developer(developer, end)
        
        def _create_new_developer(self, name, rt_series):
            developer = ValueObject(dict(name=name, load=[]))
            for day, foo in rt_series:
                day_load = ValueObject(dict(day=day, remaining_time=0, is_working_day=None, is_overloaded=None))
                developer.load.append(day_load)
            return developer
        
        def _add_remaining_time_for_day_to_developer_load(self, developer, day, time_per_developer):
            for load_data in developer.load:
                if load_data.day == day:
                    load_data.remaining_time += time_per_developer
                    return
            raise AssertionError('Day %s not found in load data' % day)
        
        def _map_remaining_time_to_developers(self, rt_series_by_task, start, end):
            """Given the remaining time for all tasks to consider, calculate the
            resource load for all involved developers."""
            all_developers = {}
            
            for ticket, rt_series in rt_series_by_task.items():
                developers = ticket.get_resource_list(include_owner=True)
                if len(developers) == 0:
                    developers.append(u'not assigned')
                
                for day, remaining_time in rt_series:
                    time_per_developer = float(remaining_time) / len(developers)
                    
                    for name in developers:
                        if name not in all_developers:
                            developer = self._create_new_developer(name, rt_series)
                            all_developers[name] = developer
                        
                        developer = all_developers[name]
                        self._add_remaining_time_for_day_to_developer_load(developer, day, time_per_developer)
            return all_developers
        
        def _calculate_capacity_for_developer(self, dev, hours_by_day):
            dev.calendar = hours_by_day
            day_sequence = sorted(hours_by_day.keys())
            capacity_hours = [hours_by_day[day] for day in day_sequence]
            dev.total_capacity = sum(capacity_hours)
            if dev.load is not None:
                for i, (day, load) in enumerate(zip(day_sequence, dev.load)):
                    remaining_capacity = sum(capacity_hours[i:])
                    load.is_overloaded = (load.remaining_time > remaining_capacity)
        
        def _add_capacity_info_for_single_developer(self, dev, member, start, end):
            if dev is None:
                dev = ValueObject(dict(name=member.name, load=None))
            dev.full_name = member.full_name
            dev.email = member.email
            
            hours_by_day = member.calendar.get_hours_for_interval(start, end)
            self._calculate_capacity_for_developer(dev, hours_by_day)
            return dev
        
        def _build_dummy_calendar(self, start, end):
            hours_by_day = dict()
            day = start.date()
            while day <= end.date():
                hours_by_day[day] = 6
                day += timedelta(days=1)
            return hours_by_day
        
        def _add_capacity_information(self, env, team_name, developers_by_name, start, end):
            # TODO:
            from agilo.scrum import TeamController
            cmd = TeamController.GetTeamCommand(env, team=team_name)
            cmd.native = True
            team = TeamController(env).process_command(cmd)
            for member in team.members:
                dev = developers_by_name.get(member.name)
                dev = self._add_capacity_info_for_single_developer(dev, member, start, end)
                developers_by_name[member.name] = dev
            
            for developer in developers_by_name.values():
                if developer.name == 'not assigned':
                    continue
                if not hasattr(developer, 'calendar'):
                    hours_by_day = self._build_dummy_calendar(start, end)
                    self._calculate_capacity_for_developer(developer, hours_by_day)
        
        def get_load_series_for_interval(self, env, start, end, sp_controller):
            sprint = self.sprint
            rt_series_by_task = \
                self.build_remaining_time_series_for_interval(env, start, end, 
                                     sprint, sp_controller, append_current_time=False, 
                                     interval_duration=timedelta(days=1))
            developers_by_name = \
                self._map_remaining_time_to_developers(rt_series_by_task,
                                                       start, end)
            if sprint.team is not None:
                self._add_capacity_information(env, sprint.team.name, 
                                               developers_by_name, start, end)
            developers = developers_by_name.values()
            self._extrapolate_load_data_for_developers(developers, end)
            return developers
        
        def _calculate_total_load_per_day(self, developers):
            totals_by_day = {}
            for developer in developers:
                if developer.load is not None:
                    for load in developer.load:
                        if load.day not in totals_by_day:
                            totals_by_day[load.day] = 0
                        totals_by_day[load.day] += load.remaining_time
            return [totals_by_day[day] for day in sorted(totals_by_day)]
        
        def _execute(self, sp_controller, date_converter, as_key):
            assert self.sprint.start != None
            assert self.sprint.end != None
            assert self.sprint.start <= self.sprint.end
            developers = self.get_load_series_for_interval(sp_controller.env, 
                            self.sprint.start, self.sprint.end, sp_controller)
            load_totals = self._calculate_total_load_per_day(developers)
            return ValueObject(developers=developers, load_totals=load_totals)
    
    
    class GetResourceStatsCommand(GetResourceLoadForDevelopersInSprintCommand):
        """Get the resources statistics for this Sprint, taking care
        of calculating the relative load, compared to the total 
        remaining time for the sprint"""
        
        def _execute(self, sp_controller, date_converter, as_key):
            env = sp_controller.env
            
            cmd = SprintController.GetTotalRemainingTimeCommand
            cmd_total_rt = cmd(env, sprint=self.sprint, 
                               tickets=self.tickets)
            total_remaining_time = sp_controller.process_command(cmd_total_rt)
            
            load_per_developer = {}
            if total_remaining_time > 0:
                today = now(tz=utc)
                developers = self.get_load_series_for_interval(env, today, today, sp_controller)
                
                for dev in developers:
                    if dev.load is not None:
                        remaining = dev.load[0].remaining_time
                        percentage = int(round(float(remaining) / \
                                               float(total_remaining_time) * \
                                               100))
                        load_per_developer[dev.name] = percentage
            
            return ValueObject(load_per_developer)
    
    
    class GetSprintIdealCapacityCommand(controller.ICommand):
        """Get the Sprint ideal capacity based on the assigned team, 
        without removing the Contingent planned for this sprint."""
        
        parameters = {'sprint': validator.MandatorySprintWithTeamValidator}
        
        def _calculate_capacity(self):
            capacity = 0
            for member in self.sprint.team.members:
                capacity_hours = member.calendar.get_hours_for_interval(self.sprint.start, 
                                                                        self.sprint.end)
                capacity += sum(capacity_hours.values())
            return capacity
        
        def _execute(self, sp_controller, date_converter, as_key):
            return {'capacity': self._calculate_capacity()}
    
    
    class GetSprintNetCapacityCommand(GetSprintIdealCapacityCommand):
        """Get the Sprint net capacity, removing also the already planned
        contingent for this sprint."""
        
        def _execute(self, sp_controller, date_converter, as_key):
            from agilo.scrum.contingent import ContingentController
            ideal_capacity = self._calculate_capacity()
            get_contingent_total = ContingentController.GetSprintContingentTotalsCommand(sp_controller.env,
                                                                                         sprint=self.sprint)
            contingent = ContingentController(sp_controller.env).process_command(get_contingent_total)
            net_capacity = ideal_capacity - contingent.amount
            return net_capacity
    
    # -------------------------------------------------------------------------
    # Commands for Burndown Chart
    
    class GetActualBurndownCommand(controller.ICommand):
        
        parameters = {'sprint': validator.MandatorySprintValidator,
                      'commitment': validator.IntOrFloatValidator,
                      'filter_by_component': validator.StringValidator,
                      'remaining_field': validator.StringValidator, }
        
        def _execute(self, sp_controller, date_converter, as_key):
            env = sp_controller.env
            end = min(self.sprint.end, now(tz=utc))

            from agilo.scrum.burndown.model import BurndownDataAggregator
            aggregator = BurndownDataAggregator(env, self.remaining_field)
            return aggregator.burndown_data_for_sprint(self.sprint,
                extend_until=end, filter_by_component=self.filter_by_component)

