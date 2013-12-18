# -*- encoding: utf-8 -*-
#   Copyright 2008 Agile42 GmbH, Berlin (Germany)
#   Copyright 2007 Andrea Tomasini <andrea.tomasini__at__agile42.com>
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
#   Author: 
#       - Andrea Tomasini <andrea.tomasini__at__agile42.com>
#       - Felix Schwarz <felix.schwarz__at__agile42.com>

from datetime import datetime, time, timedelta

from trac.util.datefmt import utc, get_timezone, to_datetime

from agilo.api import ICommand
from agilo.scrum import RemainingTime, SprintController, SprintModelManager, TeamMetrics
from agilo.scrum.backlog import BacklogModelManager
from agilo.test import AgiloTestCase
from agilo.utils import Type, Key, Status
from agilo.utils.days_time import date_to_datetime, midnight, normalize_date, \
    now, tomorrow, yesterday

# prevent warnings about ticket_notify_email.txt not being found, importing
# AgiloTicketModule will register it as the correct TemplateProvider)
from agilo.ticket.web_ui import AgiloTicketModule

class SprintControllerTest(AgiloTestCase):
    
    def setUp(self):
        self.super()
        self.sprint = self.create_sprint_with_team('TestSprint')
        self.controller = SprintController(self.env)
        self.bmm = BacklogModelManager(self.env)
        self.team = self.teh.create_team('ControllerTeam')
    
    def create_sprint_with_team(self, sprint_name):
        team = self.teh.create_team(sprint_name + 'Team')
        self.teh.create_member(sprint_name + 'Member', team)
        milestone_name = sprint_name + 'Release'
        sprint = self.teh.create_sprint(sprint_name, milestone=milestone_name, 
                                        team=team)
        return sprint
    
    def build_sprint_backlog(self, sprint):
        def create(t_type, props):
            props[Key.SPRINT] = sprint.name
            return self.teh.create_ticket(t_type, props=props)
        
        s1 = create(Type.USER_STORY, {Key.STORY_POINTS: '3'})
        s1.link_to(create(Type.TASK, {Key.REMAINING_TIME: '4'}))
        s1.link_to(create(Type.TASK, {Key.REMAINING_TIME: '8'}))
        s1.link_to(create(Type.TASK, {Key.REMAINING_TIME: '3'}))
        
        s2 = create(Type.USER_STORY, {Key.STORY_POINTS: '5'})
        s2.link_to(create(Type.TASK, {Key.REMAINING_TIME: '2'}))
        s2.link_to(create(Type.TASK, {Key.REMAINING_TIME: '2'}))
        sprint_backlog = self.bmm.get(name="Sprint Backlog", 
                                      scope=sprint.name)
        return sprint_backlog
    
    def testCreateSprintCommand(self):
        """Tests the creation of a Sprint like a View would do"""
        sprint_start = normalize_date(now(tz=utc))
        cmd_create = SprintController.CreateSprintCommand(self.env,
                                                          name='AnotherTestSprint',
                                                          milestone='MyRelease',
                                                          team=self.team.name,
                                                          start=sprint_start,
                                                          duration=15)
        sprint = self.controller.process_command(cmd_create)
        self.assert_not_none(sprint)
        self.assert_equals('AnotherTestSprint', sprint.name)
        self.assert_equals('MyRelease', sprint.milestone)
        self.assert_equals('ControllerTeam', sprint.team.name)
        self.assert_equals(sprint_start, sprint.start)
        # Negative test, should not create the sprint cause it exists already
        cmd_create.sprint_name = 'TestSprint'
        self.assert_none(self.controller.process_command(cmd_create))
    
    def testSprintWithTimezoneDifference(self):
        """Tests the sprint creation and manipulation with Timezone
        differences"""
        # Create a Sprint from Berlin with Daylight risk in Summer
        berlin_tz = get_timezone('GMT +2:00') # 'Europe/Berlin'
        start_in_berlin = normalize_date(now(tz=berlin_tz))
        cmd_create = SprintController.CreateSprintCommand(self.env,
                                                          name='TimezoneSprint',
                                                          milestone='MyRelease',
                                                          team=self.team.name,
                                                          start=start_in_berlin,
                                                          duration=15)
        sprint = self.controller.process_command(cmd_create)
        # now reload the sprint and check if the date is still valid
        # and has been correctly saved... but we will read from San
        # Francisco
        sf_tz = get_timezone('GMT -7:00') # 'US/Pacific'
        # obvious, but you never know what pytz timezone does with the
        # daylight saving.
        self.assert_equals(start_in_berlin, 
                         start_in_berlin.astimezone(sf_tz))
        
        # check that the sprint.start is in UTC timezone
        self.assert_equals(timedelta(0), sprint.start.utcoffset())
        self.assert_equals(start_in_berlin, 
                         sprint.start.astimezone(berlin_tz))
        # now we read it as UTC and we create a SF timezone datetime
        start_in_sf = sprint.start.astimezone(sf_tz)
        # Python should compare the UTC value of the datetimes
        self.assert_equals(start_in_berlin, start_in_sf)
    
    def testGetSprintCommand(self):
        sprint = self._get_sprint('TestSprint')
        self.assert_not_none(sprint)
        self.assert_equals('TestSprint', sprint.name)
        self.assert_equals('TestSprintRelease', sprint.milestone)
        self.assert_equals('TestSprintTeam', sprint.team.name)
    
    def test_can_get_sprint_command_be_called_twice(self):
        cmd_get_sprint = SprintController.GetSprintCommand(self.env, sprint=self.sprint.name)
        cmd_get_sprint.native = True
        self.assert_equals(self.sprint, self.controller.process_command(cmd_get_sprint))
        self.assert_equals(self.sprint, self.controller.process_command(cmd_get_sprint))

    def testSaveSprintCommand(self):
        cmd_save = SprintController.SaveSprintCommand(self.env,
                                                      sprint=self.sprint.name,
                                                      milestone=self.sprint.milestone,
                                                      description='Saved by me',
                                                      start=self.sprint.start,
                                                      end=self.sprint.end)
        # process_cmd runs in a endless recursion
        self.assert_true(self.controller.process_command(cmd_save))
        self.assert_equals('Saved by me', self.sprint.description)
    
    def testListSprintsCommand(self):
        self.teh.create_sprint(name='AnotherSprint', milestone='AnotherMilestone')
        cmd_list = SprintController.ListSprintsCommand(self.env) # all of them
        data = self.controller.process_command(cmd_list)
        self.assert_equals(2, len(data))
        self.assert_true('TestSprint' in [s.name for s in data])
        # Now get only the one of AnotherMilestone
        cmd_list.criteria = {'milestone': 'AnotherMilestone'}
        data = self.controller.process_command(cmd_list)
        self.assert_equals(1, len(data))
        self.assert_contains('AnotherSprint', [s.name for s in data])
    
    def _delete_sprint(self, sprint_name):
        cmd_delete = SprintController.DeleteSprintCommand(self.env, sprint=sprint_name)
        self.controller.process_command(cmd_delete)
    
    def _get_sprint(self, sprint_name):
        cmd_get = SprintController.GetSprintCommand(self.env, sprint=sprint_name)
        return self.controller.process_command(cmd_get)
    
    def testDeleteSprintCommand(self):
        self._delete_sprint(self.sprint.name)
        self.assert_raises(Exception, self._get_sprint, self.sprint.name)
    
    def testCreateAndSaveValidation(self):
        params = {'name': 'Sprint', 'milestone': 'Milestone'}
        
        self.assert_raises(ICommand.NotValidError, 
                          SprintController.CreateSprintCommand, 
                          self.env, **params)
        
        # Now add all the needed params and make it work
        params['start'] = now(tz=utc)
        params['duration'] = 10
        # Nothing bad should happen
        SprintController.CreateSprintCommand(self.env, **params)
        # Now start to mess around with dates and params
        del params['duration']
        self.assert_raises(ICommand.NotValidError, 
                          SprintController.CreateSprintCommand, 
                          self.env, **params)
        params['duration'] = 'asfu' # is a string not convertible to int
        self.assert_raises(ICommand.NotValidError, 
                          SprintController.CreateSprintCommand, 
                          self.env, **params)
        params['duration'] = '10' # is a string but convertible
        del params['start']
        self.assert_raises(ICommand.NotValidError, 
                          SprintController.CreateSprintCommand, 
                          self.env, **params)
        params['start'] = now(tz=utc)
        # again ok
        self.assert_true('start' in params)
        self.assert_true('end' in params or 'duration' in params)
        SprintController.CreateSprintCommand(self.env, **params)
        # Now provide invalid dates
        params['end'] = 'ad-232-34534'
        self.assert_raises(ICommand.NotValidError, 
                          SprintController.CreateSprintCommand, 
                          self.env, **params)
    
    def testSprintTicketsStatistics(self):
        # create some tickets statistics...
        sprint = self.teh.create_sprint('StatsSprint')
        backlog = self.teh.create_backlog('StatsBacklog', 
                                          20, 1, 
                                          ticket_types=[
                                            Type.USER_STORY,
                                            Type.TASK], 
                                          scope=sprint.name)
        self.assert_equals(20, len(backlog))
        real_stats = {}
        for bi in backlog:
            t_type = bi[Key.TYPE]
            if t_type not in real_stats:
                real_stats[t_type] = (0, 0, 0)
            planned, in_progress, closed = real_stats[t_type]
            if bi[Key.STATUS] == Status.CLOSED:
                closed += 1
            else:
                planned += 1
            real_stats[t_type] = (planned, in_progress, closed)
        # now make some stats, should be all open
        cmd_stats = SprintController.GetTicketsStatisticsCommand(self.env,
                                                                 sprint=sprint.name)
        tickets = self.controller.process_command(cmd_stats)
        for t_type, stats in tickets.items():
            self.assert_equals(real_stats[t_type], tuple(stats))
        
        # now try to get global statistics, only the totals
        planned = reduce(lambda x,y:x+y, [p[0] for p in real_stats.values()], 0)
        closed = reduce(lambda x,y:x+y, [p[1] for p in real_stats.values()], 0)
        cmd_stats.totals = True
        totals = self.controller.process_command(cmd_stats)
        self.assert_equals(planned, totals[0])
        self.assert_equals(closed, totals[1])
    
    def _set_status_for_ticket(self, status, ticket):
        ticket[Key.STATUS] = status
        if status == 'closed':
            ticket[Key.RESOLUTION] = 'fixed'
        ticket.save_changes(None, None)
    
    def testTicketTotalsCountInProgressTicketsCorrectly(self):
        sprint = self.teh.create_sprint('FooSprint')
        task = self.teh.create_task(sprint=sprint.name)
        self._set_status_for_ticket(Status.ACCEPTED, task)
        cmd_stats = SprintController.GetTicketsStatisticsCommand(self.env, sprint=sprint, totals=True)
        stats_total = self.controller.process_command(cmd_stats)
        self.assert_equals((0, 1, 0), stats_total)
    
    def testTicketByTypeCountInProgressTicketsCorrectly(self):
        sprint = self.teh.create_sprint('FooSprint')
        task = self.teh.create_task(sprint=sprint.name)
        self._set_status_for_ticket(Status.ACCEPTED, task)
        cmd_stats = SprintController.GetTicketsStatisticsCommand(self.env, sprint=sprint, totals=False)
        stats_by_type = self.controller.process_command(cmd_stats)
        self.assert_equals({Type.TASK: (0, 1, 0)}, stats_by_type)
    
    def testGetSprintTicketsByAttribute(self):
        """Tests the listing of tickets by attribute from controller"""
        sprint = self.teh.create_sprint('StatsSprint')
        backlog = self.teh.create_backlog('StatsBacklog', 
                                          20, 1, 
                                          ticket_types=[
                                            Type.USER_STORY,
                                            Type.TASK], 
                                          scope=sprint.name)
        self.assert_equals(20, len(backlog))
        # Now check how many tasks are in there
        tasks = stories = 0
        for bi in backlog:
            if bi[Key.TYPE] == Type.TASK:
                tasks += 1
            else:
                stories += 1
        # Now get the tickets with property remaining_time
        cmd_rem_time = SprintController.ListTicketsHavingPropertiesCommand(self.env,
                                                                           sprint=sprint.name,
                                                                           properties=[Key.REMAINING_TIME])
        res = self.controller.process_command(cmd_rem_time)
        self.assert_equals(tasks, len(res))
        # now check the stories
        cmd_story_points = SprintController.ListTicketsHavingPropertiesCommand(self.env,
                                                                               sprint=sprint.name,
                                                                               properties=[Key.STORY_POINTS])
        res = self.controller.process_command(cmd_story_points)
        self.assert_equals(stories, len(res))
    
    def testGetTotalRemainingTime(self):
        """Tests the current remaining time of a given sprint"""
        def compute_remaining_time(backlog):
            total_rt = 0
            for bi in backlog:
                if bi[Key.TYPE] == Type.TASK:
                    total_rt += int(bi[Key.REMAINING_TIME] or 0)
            return total_rt
        
        def set_rtusp_ratio(sprint):
            metrics = TeamMetrics(self.env, sprint, sprint.team)
            metrics[Key.RT_USP_RATIO] = 2 # 16h for 8 usp
            metrics.save()
        
        def remove_link_to_tasks_from_one_story(backlog):
            rt_delta = 0
            for bi in backlog:
                if bi[Key.TYPE] == Type.USER_STORY:
                    story = bi.ticket
                    if len(story.get_outgoing()) > 0:
                        # When we remoev all tasks, we need to use the estimated
                        # remaining time for this story
                        estimated_remaining_time = int(story[Key.ESTIMATED_REMAINING_TIME] or 0)
                        rt_delta += estimated_remaining_time
                    for task in story.get_outgoing():
                        story.del_link_to(task)
                        # We don't add the task's remaining time to rt_delta 
                        # because we assume that this task was counted before.
                        # When a task becomes an orphan task, the total remaining
                        # time changes only because of the story.
                    break
            return rt_delta
        
        sprint = self.create_sprint_with_team('RemTimeSprint')
        backlog = self.build_sprint_backlog(sprint)
        total_rt = compute_remaining_time(backlog)
        cmd_total_rt = SprintController.GetTotalRemainingTimeCommand(self.env,
                                                                     sprint=sprint.name)
        total = self.controller.process_command(cmd_total_rt)
        self.assert_equals(total_rt, total)
        set_rtusp_ratio(sprint)
        total_rt += remove_link_to_tasks_from_one_story(backlog)
        total = self.controller.process_command(cmd_total_rt)
        self.assert_equals(total_rt, total)

    def testRemainingTimeMustIncludeTasksBelowBugs(self):
        """If bugs are allowed in a sprint backlog, all tasks below a bug must
        count for the remaining time."""
        sprint = self.create_sprint_with_team('RemTimeSprint')
        backlog = self.teh.create_backlog('StatsBacklog', 
                                          20, 1, 
                                          ticket_types=[
                                            Type.USER_STORY,
                                            Type.TASK], 
                                          scope=sprint.name)
        self.assert_equals(20, len(backlog))
        # Now check how many tasks are in there
        total_rt = total_sp = 0
        for bi in backlog:
            if bi[Key.TYPE] == Type.TASK:
                total_rt += int(bi[Key.REMAINING_TIME] or 0)
            else:
                total_sp += int(bi[Key.STORY_POINTS] or 0)
        cmd_total_rt = SprintController.GetTotalRemainingTimeCommand(self.env,
                                                                     sprint=sprint.name)
        remaining_time_before_bug = self.controller.process_command(cmd_total_rt)
        self.assert_equals(total_rt, remaining_time_before_bug)
        
        bug = self.teh.create_ticket(Type.BUG, 
                                     {Key.SPRINT: sprint.name})
        bug_task = self.teh.create_ticket(Type.TASK, 
                                          {Key.SPRINT: sprint.name,
                                           Key.REMAINING_TIME: "7"})
        self.assert_true(bug.link_to(bug_task))
        
        remaining_time_after_bug = self.controller.process_command(cmd_total_rt)
        
        self.assert_equals(remaining_time_before_bug + 7, 
                         remaining_time_after_bug)
    
    def _save_sprint(self, **kwargs):
        name = kwargs.get('old_sprint', kwargs['sprint'])
        sprint = self._get_sprint(name)
        for key in ('start', 'milestone'):
            if key not in kwargs:
                kwargs[key] = sprint[key]
        if 'duration' not in kwargs and 'end' not in kwargs:
            kwargs['end'] = sprint.end
        cmd = SprintController.SaveSprintCommand(self.env, **kwargs)
        return self.controller.process_command(cmd)
    
    def testCanRenameSprints(self):
        new_sprint_name = 'MyNewSprint'
        self._save_sprint(old_sprint=self.sprint.name, sprint=new_sprint_name)
        renamed_sprint = self._get_sprint(new_sprint_name)
        self.assert_not_none(renamed_sprint)
    
    def testCanEditDataOfExistingSprint(self):
        # Disable normalization of dates, so that works also on Friday
        self.teh.disable_sprint_date_normalization()
        new_sprint_end = date_to_datetime(tomorrow(), tz=utc)
        self._save_sprint(old_sprint=self.sprint.name, sprint=self.sprint.name, 
                          end=new_sprint_end)
        sprint = self._get_sprint(self.sprint.name)
        self.assert_equals(new_sprint_end, sprint.end)
    
    def testCanNotOverwriteExistingSprintByRename(self):
        self.assert_not_equals(tomorrow(utc), self.sprint.start)
        existing_name = 'existing'
        self.teh.create_sprint(existing_name, start=date_to_datetime(tomorrow(utc)))
        
        one_day_before = date_to_datetime(yesterday(), tz=utc)
        
        parameters = dict(old_sprint=self.sprint.name, sprint=existing_name, start=one_day_before)
        self.assert_raises(ICommand.NotValidError, self._save_sprint, **parameters)


class SprintControllerTestForRemainingTimes(AgiloTestCase):
    # Most of the test cases were previously in sprint_test 
    # (agilo.scrum.sprint.tests) However, when we moved the 
    # functionality to a command, these test cases needed to be ported 
    # so that they test the command instead of the direct model 
    # implementation. Several things are still artifacts from that old 
    # test setup.
    
    def setUp(self):
        self.super()
        self.controller = SprintController(self.env)
        
        self.team = self.teh.create_team('Test team')
        # Preventing a RuleValidationException (Owner not Team Member)
        self.teh.create_member(name='tester', team=self.team)
        self.sprint = self.teh.create_sprint("Test Sprint", team=self.team)
        
        self.metrics = TeamMetrics(self.env, self.sprint, self.team)
        self.metrics[Key.RT_USP_RATIO] = 1.5
        self.metrics.save()
        
        self.bmm = BacklogModelManager(self.env)
        self.smm = SprintModelManager(self.env)
        
        self.sprint_backlog, self.story1, self.task1, self.task2 = \
            self._build_sprint_backlog_with_tasks(self.sprint)
    
    def _build_sprint_backlog_with_tasks(self, sprint):
        story_props = {Key.OWNER: 'tester',
                       Key.SPRINT: sprint.name,
                       Key.STORY_POINTS: "8"}
        story = self.teh.create_ticket(Type.USER_STORY, story_props)
        task1 = self.teh.create_ticket(Type.TASK, {Key.OWNER: 'tester',
                                                   Key.SPRINT: sprint.name,
                                                   Key.REMAINING_TIME: "8"})
        story.link_to(task1)
        
        task2 = self.teh.create_ticket(Type.TASK, {Key.OWNER: 'tester',
                                                   Key.SPRINT: sprint.name,
                                                   Key.REMAINING_TIME: "4"})
        story.link_to(task2)
        
        sprint_backlog = self.bmm.get(name="Sprint Backlog", scope=sprint.name)
        self.assert_equals(len(sprint_backlog), 3)
        return (sprint_backlog, story, task1, task2)
    
    def get_total_remaining_time(self, sprint_name, day, commitment=None):
        cmd_class = SprintController.GetTotalRemainingTimeCommand
        cmd = cmd_class(self.env, sprint=sprint_name, day=day, commitment=commitment)
        return self.controller.process_command(cmd)
    
    def test_can_calculate_remaining_time_for_a_specific_day(self):
        # Set remaining time for tasks at the end of the sprint
        sprint = self.sprint
        end = sprint.end
        rt1 = RemainingTime(self.env, self.task1)
        rt2 = RemainingTime(self.env, self.task2)
        rt1.set_remaining_time(2, day=end)
        rt2.set_remaining_time(1, day=end)
        self.assert_equals(2, RemainingTime(self.env, self.task1).get_remaining_time(end))
        self.assert_equals(1, RemainingTime(self.env, self.task2).get_remaining_time(end))
        self.assert_equals(3, self.get_total_remaining_time(sprint.name, end))
    
    def _create_remaining_time_series(self, ticket, start, time_series):
        rt = RemainingTime(self.env, ticket)
        for i, remaining_time in enumerate(time_series):
            day = start + (i * timedelta(days=1))
            rt.set_remaining_time(remaining_time, day=day)
    
    def test_can_calculate_total_remaining_time_for_start_of_sprint(self):
        start = self.sprint.start 
        self._create_remaining_time_series(self.task1, start,[12, 7.5, 3, 2.5, 0])
        self._create_remaining_time_series(self.task2, start, [8, 9, 4.5, 0, 3])
        
        total_remaining_time = self.get_total_remaining_time(self.sprint.name, start)
        self.assert_equals(12+8, total_remaining_time)
    
    def test_can_calculate_remaining_time_series_for_sprint(self):
        start = datetime(2009, 5, 11, tzinfo=utc)
        self.sprint.start = start
        self.sprint.end = datetime(2009, 5, 15, 18, 00, tzinfo=utc)
        self.smm.save(self.sprint)

        # check there is not time set right now
        series = self.get_remaining_times(self.sprint.name)
        self.assert_equals(0, sum(series))

        self._create_remaining_time_series(self.task1, start,[12, 7.5, 3, 2.5, 0])
        self._create_remaining_time_series(self.task2, start, [8, 9, 4.5, 0, 3])
        
        series = self.get_remaining_times(self.sprint.name)
        self.assert_equals([12+8, 7.5+9, 3+4.5, 2.5+0, 0+3], series)
    
    def  get_remaining_times(self, sprint_name=None, cut_to_today=False, commitment=None):
        if sprint_name is None:
            sprint_name = self.sprint.name
        cmd_class = SprintController.GetRemainingTimesCommand
        cmd = cmd_class(self.env, sprint=sprint_name, cut_to_today=cut_to_today,
                        commitment=commitment)
        return self.controller.process_command(cmd)
    
    def test_compute_remaining_time_for_sprint_even_if_story_has_no_remaining_time(self):
        self.task1[Key.REMAINING_TIME] = 0
        self.task2[Key.REMAINING_TIME] = 0
        self.task1.save_changes('foo', 'bar')
        self.task2.save_changes('foo', 'bar')
        # This raised an exception before because TOTAL_REMAINING_TIME was None
        self.get_remaining_times()
    
    def test_use_estimated_remaining_time(self):
        story_props = {Key.OWNER: 'tester',
                       Key.SPRINT: self.sprint.name, 
                       Key.STORY_POINTS: "5"}
        story2 = self.teh.create_ticket(Type.USER_STORY, story_props)
        self.assert_length(4, self.sprint_backlog)
        
        self.assert_equals(8, int(self.story1[Key.STORY_POINTS]))
        self.assert_equals(8 * 1.5, self.story1[Key.ESTIMATED_REMAINING_TIME])
        self.assert_equals(5 * 1.5, story2[Key.ESTIMATED_REMAINING_TIME])
        remaining_time = self.get_total_remaining_time(self.sprint.name, now(tz=utc))
        self.assert_equals((8+4) + 5 * 1.5, remaining_time)
    
    def _close_ticket_as_fixed(self, task):
        task[Key.STATUS] = Status.CLOSED
        task[Key.RESOLUTION] = Status.RES_FIXED
        task.save_changes(None, None)
    
    def test_remaining_time_correct_even_for_closed_stories(self):
        self.sprint.start = datetime.today() - timedelta(days=5)
        self.sprint.save()
        
        # Store some remaining time for yesterday
        yesterday_midnight = datetime.combine(yesterday(tz=utc), time(tzinfo=utc))
        RemainingTime(self.env, self.task1).set_remaining_time(3, yesterday_midnight)
        RemainingTime(self.env, self.task2).set_remaining_time(1, yesterday_midnight)
        
        self._close_ticket_as_fixed(self.task1)
        self._close_ticket_as_fixed(self.task2)
        self._close_ticket_as_fixed(self.story1)
        
        remaining_times = self.get_remaining_times(self.sprint.name, cut_to_today=True)
        # We have to use relative positioning from the end because we don't know
        # if the sprint will be extended due to a holiday.
        self.assert_equals([4, 0], remaining_times[-2:])
        
        # Check that the same holds true for retrieving a single day
        remaining_time = self.get_total_remaining_time(self.sprint.name, yesterday_midnight)
        self.assert_equals(4, remaining_time)
    
    def yesterday_midnight(self):
        return midnight(yesterday(tz=utc), tz=utc)
    
    def _create_historic_remaining_times(self):
        def set_remaining_time(task, day, remaining_time):
            remaining = RemainingTime(self.env, task)
            remaining.set_remaining_time(remaining_time, day=day)
        
        # 6 days before today so we are sure that the sprint started at least 
        # three days ago even if it was moved.
        self.sprint.start = now(tz=utc) - timedelta(days=6)
        self.smm.save(self.sprint)
        
        # We already burned some data on the first day of the sprint
        set_remaining_time(self.task1, self.sprint.start, 6)
        set_remaining_time(self.task2, self.sprint.start, 3)
        
        # Yesterday we burned some time already
        set_remaining_time(self.task1, self.yesterday_midnight(), 5)
    
    def test_remaining_time_of_first_sprint_day_equals_commitment(self):
        self._create_historic_remaining_times()
        # But now the remaining time went up again (fields are unchanged!)
        self.assert_equals(8+4, self.story1[Key.TOTAL_REMAINING_TIME])
        
        remaining_times = self.get_remaining_times(self.sprint.name, cut_to_today=True)
        # if no commitment is passed to the function, just return the remaining 
        # time
        self.assert_equals(6+3, remaining_times[0])
        
        remaining_times = self.get_remaining_times(self.sprint.name, 
                                                   cut_to_today=True, commitment=42)
        self.assert_equals(42, remaining_times[0])
        self.assert_equals([5+3, 8+4], remaining_times[-2:])
    
    def test_total_remaining_time_of_first_sprint_day_equals_commitment(self):
        self._create_historic_remaining_times()
        sprint = self.sprint
        self.assert_equals(5+3, self.get_total_remaining_time(sprint.name, self.yesterday_midnight()))
        self.assert_equals(42, self.get_total_remaining_time(sprint.name, sprint.start, commitment=42))


class GetResourceLoadForDevelopersInSprintCommandTest(AgiloTestCase):
    
    def setUp(self):
        self.super()
        self.bmm = BacklogModelManager(self.teh.get_env())
        self.team = self.teh.create_team('FooTeam')
        self.teh.create_member('tester', self.team)
        self.teh.create_member('Foo', self.team)
        self.sprint = self.teh.create_sprint('ResourceLoadSprint', team=self.team)
        self.build_sprint_backlog_with_tasks(self.sprint)
        self.controller = SprintController(self.env)
        self.metrics = self.sprint.get_team_metrics()
    
    def build_sprint_backlog_with_tasks(self, sprint):
        story_props = {Key.OWNER: 'tester',
                       Key.SPRINT: sprint.name,
                       Key.STORY_POINTS: "8"}
        story = self.teh.create_ticket(Type.USER_STORY, story_props)
        task1 = self.teh.create_ticket(Type.TASK, {Key.OWNER: 'tester',
                                                   Key.SPRINT: sprint.name,
                                                   Key.REMAINING_TIME: "8"})
        story.link_to(task1)
        
        task2 = self.teh.create_ticket(Type.TASK, {Key.OWNER: 'tester',
                                                   Key.SPRINT: sprint.name,
                                                   Key.REMAINING_TIME: "4"})
        story.link_to(task2)
        
        self.story1, self.task1, self.task2 = (story, task1, task2)
        self.sprint_backlog = self.bmm.get(name="Sprint Backlog", scope=sprint.name)
        self.assert_equals(len(self.sprint_backlog), 3)
    
    def find_developer(self, developers, name):
        for developer in developers:
            if developer.name == name:
                return developer
        raise AssertionError('No developer with name %s found' % name)
    
    def get_remaining_time_for(self, day, load):
        for item in load:
            if item.day.date() == day:
                return item.remaining_time
        raise AssertionError('No remaining time for %s found' % day)
    
    def get_remaining_time_for_tomorrow(self, load):
        tomorrow = now().astimezone(utc).date() + timedelta(days=1)
        return self.get_remaining_time_for(tomorrow, load)
    
    def _get_resource_load_for_developers(self):
        cmd = SprintController.GetResourceLoadForDevelopersInSprintCommand(self.env, sprint=self.sprint)
        data = self.controller.process_command(cmd)
        return data.developers
    
    def test_dont_break_if_no_team_assigned_to_sprint(self):
        self.sprint.team = None
        self.sprint.save()
        self._get_resource_load_for_developers()
    
    def test_load_series_is_calculated_for_single_developer_and_extrapolated_until_end_of_sprint(self):
        start = self.sprint.start
        end = self.sprint.end
        nr_sprint_days = (end.date() - start.date()).days + 1
        
        developers = self._get_resource_load_for_developers()
        dev = self.find_developer(developers, 'tester')
        # +1 because we add another item exactly at the end of the sprint
        self.assert_equals(nr_sprint_days + 1, len(dev.load))
        self.assert_equals(start, dev.load[0].day)
        self.assert_equals(0, dev.load[0].remaining_time)
        
        self.assert_equals(8+4, self.get_remaining_time_for_tomorrow(dev.load))
        
        self.assert_equals(end, dev.load[-1].day)
        self.assert_equals(8+4, dev.load[-1].remaining_time)
    
    def set_remaining_time(self, task, day, remaining):
        rt = RemainingTime(self.env, task)
        rt.set_remaining_time(remaining, day=day)
    
    def test_load_series_really_displays_remaining_time(self):
        # in all the other tests we don't have any remaining time changes so
        # check here that it really uses  the historic remaining times and not 
        # just the lastest one.
        day_before_yesterday = yesterday(tz=utc) - timedelta(days=1)
        self.set_remaining_time(self.task1, day_before_yesterday, 3)
        self.set_remaining_time(self.task2, yesterday(tz=utc), 2)
        
        developers = self._get_resource_load_for_developers()
        dev = self.find_developer(developers, 'tester')
        self.assert_equals(3+2, self.get_remaining_time_for(yesterday(tz=utc), dev.load))
    
    def test_load_for_tasks_without_owner_summed_up_for_not_assigned(self):
        self.task1[Key.OWNER] = ''
        self.task1.save_changes('someone', 'just saving')
        
        developers = self._get_resource_load_for_developers()
        dev = self.find_developer(developers, 'not assigned')
        self.assert_equals(8, self.get_remaining_time_for_tomorrow(dev.load))
        self.assert_false(hasattr(dev, 'calendar'))
    
    def test_split_load_for_task_with_multiple_resources(self):
        self.teh.create_member('Bar', self.team)
        self.teh.create_member('Baz', self.team)
        self.task1[Key.REMAINING_TIME] = '6'
        self.task1[Key.RESOURCES] = 'Foo, Bar, Baz'
        self.task1.save_changes('someone', 'just saving')
        # remove the estimated remaining time from the game to ease testing
        del self.metrics[Key.RT_USP_RATIO]
        load_per_resource_for_task1 = 6.0 / 4
        
        developers = self._get_resource_load_for_developers()
        
        def remaining_time(name):
            dev = self.find_developer(developers, name)
            return dev.load[-1].remaining_time
        self.assert_equals(load_per_resource_for_task1, remaining_time('Foo'))
        self.assert_equals(load_per_resource_for_task1, remaining_time('Bar'))
        self.assert_equals(load_per_resource_for_task1, remaining_time('Baz'))
        self.assert_equals(load_per_resource_for_task1+4, remaining_time('tester'))
    
    def test_split_load_among_resources_even_if_task_has_no_owner(self):
        self.teh.create_member('Bar', self.team)
        self.task1[Key.OWNER] = ''
        self.task1[Key.RESOURCES] = 'Foo, Bar'
        self.task1.save_changes("someone", "just saving")
        
        developers = self._get_resource_load_for_developers()
        
        def remaining_time(name):
            dev = self.find_developer(developers, name)
            return dev.load[-1].remaining_time
        
        load_per_resource_for_task1 = 8 / 2
        self.assert_equals(load_per_resource_for_task1, remaining_time('Foo'))
        self.assert_equals(load_per_resource_for_task1, remaining_time('Bar'))
    
    def test_resource_load_to_not_assigned_if_estimated_remaining_time_is_used(self):
        """Test that if the estimated remaining time for a story is used,
        the individual resources get their share for every ticket but the 
        difference is put to not assigned.
        Alternatively, one could compute a weighted load distribution among the
        owners but that seems to be too complicated and a bit to much magic."""
        story_props = {Key.SPRINT: self.sprint.name, Key.STORY_POINTS: "8"}
        self.teh.create_ticket(Type.USER_STORY, story_props)
        
        self.metrics[Key.RT_USP_RATIO] = 2
        self.metrics.save()
        
        developers = self._get_resource_load_for_developers()
        dev = self.find_developer(developers, 'not assigned')
        self.assert_equals(8 * 2, dev.load[-1].remaining_time)
    
    def test_exclude_tasks_for_other_sprints(self):
        sprint2 = self.teh.create_sprint("Second Sprint")
        self.task2[Key.SPRINT] = sprint2.name
        self.task2.save_changes("someone", "just saving")
        developers = self._get_resource_load_for_developers()
        dev = self.find_developer(developers, 'tester')
        # Task2 is not used anymore
        self.assert_equals(8, dev.load[-1].remaining_time)
    
    def test_include_remaining_time_from_unconnected_tasks(self):
        task_props = {Key.SPRINT: self.sprint.name, Key.REMAINING_TIME: "5",
                      Key.OWNER: 'Foo'}
        orphan_task = self.teh.create_ticket(Type.TASK, task_props)
        day_before_yesterday = now(tz=utc) - timedelta(days=2)
        RemainingTime(self.env, orphan_task).set_remaining_time(7, day_before_yesterday)
        self.assert_length(4, self.sprint_backlog)
        developers = self._get_resource_load_for_developers()
        dev = self.find_developer(developers, 'Foo')
        # Task2 is not used anymore
        self.assert_equals(5, dev.load[-1].remaining_time)
    
    def test_capacity_per_day_shows_real_capacity(self):
        # Regression test for #801
        self.sprint.start = datetime(2009, 6, 29, 9, 0, tzinfo=utc)
        self.sprint.end = datetime(2009, 7, 3, 18, 0, tzinfo=utc)
        self.sprint.save()
        foo = self.find_developer(self.team.members, 'Foo')
        foo.ts_mon = 0
        foo.ts_fri = 0
        foo.ts_sat = 0
        foo.ts_sun = 0
        foo.save()
        
        developers = self._get_resource_load_for_developers()
        foo = self.find_developer(developers, 'Foo')
        self.assert_equals(3*6, foo.total_capacity)



class TestRetargetTicketOnSprintClose(AgiloTestCase):
    def setUp(self):
        self.super()
        self.old_sprint = self.teh.create_sprint("Sprint One")
        self.new_sprint = self.teh.create_sprint("New Sprint",  milestone=self.old_sprint.milestone)
        self.us1 = self.teh.create_ticket(Type.USER_STORY, props={Key.SPRINT: self.old_sprint.name})
        self.t1 = self.teh.create_ticket(Type.TASK, props={Key.SPRINT: self.old_sprint.name, 
                                                           Key.REMAINING_TIME: '12'})
        self.us1.link_to(self.t1)
        self.t2 = self.teh.create_ticket(Type.TASK, props={Key.SPRINT: self.old_sprint.name, 
                                                           Key.REMAINING_TIME: '12'})
        self.us1.link_to(self.t2)
        self.teh.move_changetime_to_the_past([self.us1, self.t1, self.t2])
        # build a sprint controller
        self.controller = SprintController(self.env)
        self.bmm = BacklogModelManager(self.env)
    
    def testRetargetIncompleteWork(self):
        """Tests the retargeting of incomplete work to another sprint"""
        
        def _remove_notification_fields(sprint_backlog):
            # Trac's notification module sets fields like 'new' and 'link' in 
            # the ticket to use them as template variables. This can cause 
            # errors when we save the same ticket afterwards because they are 
            # not custom fields so trac try to set a column with this name in
            # the main ticket table which fails.
            # This error only shows up when you run the full unit test suite, 
            # not only this test.
            for bi in sprint_backlog:
                ticket = bi.ticket
                ticket._old.pop('new', None)
                ticket._old.pop('link', None)
        
        # Check the story and the tasks are in the sprint backlog
        sb = self.bmm.get(name=Key.SPRINT_BACKLOG, scope=self.old_sprint.name)
        self.assert_length(3, sb)
        new_sb = self.bmm.get(name=Key.SPRINT_BACKLOG, scope=self.new_sprint.name)
        self.assert_length(0, new_sb)
        # Now re-target the story to self.new_sprint, should be there with both tasks
        cmd_retarget_old = self.controller.RetargetTicketsCommand(self.env,
                                                                  sprint=self.old_sprint.name,
                                                                  retarget=self.new_sprint.name)
        cmd_retarget_new = self.controller.RetargetTicketsCommand(self.env,
                                                                  sprint=self.new_sprint.name,
                                                                  retarget=self.old_sprint.name)
        self.controller.process_command(cmd_retarget_old)
        self.teh.move_changetime_to_the_past([self.us1, self.t1, self.t2])
        
        self.assert_length(0, sb)
        self.assert_length(3, new_sb)
        
        _remove_notification_fields(new_sb)
        # Now close one ticket and check if only 2 are retargeted
        self.t1[Key.STATUS] = Status.CLOSED
        self.t1.save_changes('tester', 'Closed t1')
        self.teh.move_changetime_to_the_past([self.t1])
        self.assert_equals(Status.CLOSED, self.t1[Key.STATUS])
        # closed ticket should still remain
        self.assert_contains(self.t1, new_sb)
        # self.t2 is now moved back to the old sprint
        self.controller.process_command(cmd_retarget_new)
        # sb contains t2 (closed) and us1 (because referenced from t2)
        self.assert_contains(self.t2, sb)
        self.assert_contains(self.us1, sb)
        self.assert_length(2, sb)
        self.assert_contains(self.t1, new_sb)
        self.assert_contains(self.us1, new_sb)
        self.assert_length(2, new_sb) # there should be t1 even if closed and us1
        
        # Now close the second task, but not the story, and verify that only the
        # story is moved
        self.teh.move_changetime_to_the_past([self.us1, self.t1, self.t2])
        self.t2[Key.STATUS] = Status.CLOSED
        self.t2.save_changes('tester', 'Closed t2')
        self.t1[Key.SPRINT] = self.old_sprint.name
        self.t1[Key.STATUS] = Status.CLOSED
        self.t1.save_changes('tester', 'Moved t1 back')
        self.teh.move_changetime_to_the_past([self.us1, self.t1, self.t2])
        self.assert_length(3, sb)
        
        # Only us1 is incomplete so it is moved to the new sprint again
        self.controller.process_command(cmd_retarget_old)
        # Now the sprint backlog always shows the tickets which are linked :-)
        self.assert_length(3, sb) # t1, t2 and the linked story
        self.assert_length(1, new_sb) # only the story
    
    def testDontMoveTasksWhichAreNotPlanedForTheClosedSprint(self):
        another_sprint = self.teh.create_sprint('Another sprint')
        self.t1[Key.SPRINT] = another_sprint.name
        self.t1.save_changes(None, None)
        self.teh.move_changetime_to_the_past([self.us1, self.t1, self.t2])
        
        sb = self.bmm.get(name=Key.SPRINT_BACKLOG, scope=self.old_sprint.name)
        self.assert_equals(2, len(sb))
        self.assert_contains(self.us1, sb)
        self.assert_contains(self.t2, sb)
        
        # We should test that it works even if we use the sprint's name as a
        # parameter.
        cmd_retarget_old = self.controller.RetargetTicketsCommand(self.env,
                                                                  sprint=self.old_sprint.name,
                                                                  retarget=self.new_sprint.name)
        self.controller.process_command(cmd_retarget_old)
        self.assert_length(0, sb)
        other_sb = self.bmm.get(name=Key.SPRINT_BACKLOG, scope=another_sprint.name)
        self.assert_length(1 + 1, other_sb) # The story is linked will pop out as well
    
    def test_do_not_move_parent_which_is_not_explicitly_planned_for_sprint(self):
        self.us1[Key.SPRINT] = None
        self.us1.save_changes(None, None)
        self.teh.move_changetime_to_the_past([self.us1, self.t1, self.t2])
        # Tasks are removed from the sprint backlog by the burndown changelistener
        self.t1[Key.SPRINT] = self.old_sprint.name
        self.t1.save_changes(None, None)
        self.t2[Key.SPRINT] = self.old_sprint.name
        self.t2.save_changes(None, None)
        self.teh.move_changetime_to_the_past([self.us1, self.t1, self.t2])
        
        sb = self.bmm.get(name=Key.SPRINT_BACKLOG, scope=self.old_sprint.name)
        self.assert_length(3, sb)
        
        cmd_retarget_old = self.controller.RetargetTicketsCommand(self.env,
                                                                  sprint=self.old_sprint.name,
                                                                  retarget=self.new_sprint.name)
        self.controller.process_command(cmd_retarget_old)
        # the length of the sprint should be 0 as also the story shouldn't
        # belong anymore to the Backlog because wasn't explicitly planned
        us1 = self.teh.load_ticket(t_id=self.us1.id)
        self.assert_equals('', us1[Key.SPRINT])
        self.assert_length(0, sb)

    
    def testDontCloseStoriesAutomaticallyOnSprintClose(self):
        """
        Test that stories without tasks are not closed automatically if they
        don't contain any tasks. This is not useful because from the fact that
        all tasks fro a story/bug are closed you can not derive that the story
        is done. Closing a story should be conscious act done by a team member.
        """
        self.t1[Key.STATUS] = Status.CLOSED
        self.t1.save_changes(None, None)
        self.t2[Key.STATUS] = Status.CLOSED
        self.t2.save_changes(None, None)
        self.teh.move_changetime_to_the_past([self.us1, self.t1, self.t2])
        
        cmd_retarget_old = self.controller.RetargetTicketsCommand(self.env,
                                                                  sprint=self.old_sprint.name,
                                                                  retarget=self.new_sprint.name)
        self.controller.process_command(cmd_retarget_old)
        us1 = self.teh.load_ticket(t_id=self.us1.id)
        self.assert_not_equals(Status.CLOSED, us1[Key.STATUS])


if __name__ == '__main__':
    from agilo.test.testfinder import run_unit_tests
    run_unit_tests(__file__)
