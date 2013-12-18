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
#        - Sebastian Schulze <sebastian.schulze__at__agile42.com>
#        - Andrea Tomasini <andrea.tomasini__at__agile42.com>

from datetime import timedelta, datetime, time

from trac.util.datefmt import get_timezone, localtz, parse_date, to_datetime, utc


from agilo.scrum.backlog import RemainingTime
from agilo.scrum.metrics import TeamMetrics
from agilo.scrum.team import TeamMemberModelManager, \
    TeamModelManager, TeamMemberCalendar, TeamController
from agilo.test import AgiloTestCase
from agilo.utils import Key, Type, Status
from agilo.utils.days_time import date_to_datetime, day_after_tomorrow, \
    midnight, now, one_day, today, tomorrow, yesterday
from agilo.utils.db import get_user_attribute_from_session, \
    set_user_attribute_in_session


class TestTeam(AgiloTestCase):
    """Tests for the team model class Team"""
    
    def setUp(self):
        self.super()
        self.tm = TeamModelManager(self.env)
        self.tmm = TeamMemberModelManager(self.env)
        self.controller = TeamController(self.env)
    
    def set_hours_for_day_on_team_member(self, hours, day, team_member):
        calendar = team_member.calendar
        calendar.set_hours_for_day(hours, day)
        calendar.save()
    
    def team_with_no_member(self):
        team = self.tm.create(name="Team#1")
        return team

    def team_with_one_member(self):
        team = self.team_with_no_member()
        member = self._add_member_to_team('Member#1', team)
        return team, member
    
    def team_with_two_members(self):
        team, member1 = self.team_with_one_member()
        member2 = self._add_member_to_team('Member#2', team)
        return team, member1, member2
    
    def _add_member_to_team(self, name, team):
        member = self.tmm.create(name=name, team=team)
        # just to make sure we have  a capacity, 1h/1h for ease of calculating test data
        member.capacity = [9] * 7
        member.save()
        return member
    
    
    def testCapacityHours(self):
        """Test the get_capacity_hours() method"""
        test_team = self.tm.create(name="Team#1")
        self.assert_true(test_team.exists)
        test_members = (self.tmm.create(name="Member#1", team=test_team),
                        self.tmm.create(name="Member#2", team=test_team, 
                                              default_capacity=[4,4,4,0,0,0,0]),
                        self.tmm.create(name="Member#3", team=test_team, 
                                              default_capacity=[0,0,0,2,2,0,0]))
        for tm in test_members:
            self.assert_not_none(tm.team)
            self.assert_equals(test_team, tm.team)
        
        # test the default constructor
        start_date = parse_date("2008-09-08T08:00:00")
        test_sprint =  self.teh.create_sprint(name="TestSprint", start=start_date, 
                                              duration=10)
        
        # test save and restore
        for member in test_members:
            self.assert_true(self.tmm.save(member))
        
        test_sprint.team = test_team
        test_sprint.save()
        
        weekly_hours = (5 * 6) + (4 + 4 + 4) + (2 + 2)
        self.assert_equals(weekly_hours, test_team.capacity().default_hours_of_capacity_per_week())
        
        sprint_hours = 2 * weekly_hours
        actual = test_team.capacity().hourly_capacities_in_sprint(test_sprint)
        capacity = sum(map(lambda each: each.capacity, actual))
        self.assert_almost_equals(sprint_hours, capacity, max_delta=.01)
    
    def testVelocityForSprint(self):
        """Tests the set velocity for a sprint as a team metric"""
        test_team = self.tm.create(name="Team#1")
        self.assert_true(test_team.save())
        self.tmm.create(name="Member#1", team=test_team).save()
        self.tmm.create(name="Member#2", team=test_team).save()
        self.tmm.create(name="Member#3", team=test_team).save()
        sprint = self.teh.create_sprint("TestSprint", team=test_team)
        us1 = self.teh.create_ticket(Type.USER_STORY, props={Key.STORY_POINTS: '5',
                                                             Key.SPRINT: sprint.name})
        us2 = self.teh.create_ticket(Type.USER_STORY, props={Key.STORY_POINTS: '8',
                                                             Key.SPRINT: sprint.name})
        us3 = self.teh.create_ticket(Type.USER_STORY, props={Key.STORY_POINTS: '13',
                                                             Key.SPRINT: sprint.name})
        # we have to use the TeamController here
        cmd_store = TeamController.StoreTeamVelocityCommand(self.env,
                                                            sprint=sprint,
                                                            team=test_team,
                                                            estimated=True)
        self.assert_equals(26, self.controller.process_command(cmd_store))
        # Now close a story and check the actual velocity
        cmd_get = TeamController.GetStoredTeamVelocityCommand(self.env,
                                                              sprint=sprint.name,
                                                              team=test_team,
                                                              estimated=True)
        us3[Key.STATUS] = Status.CLOSED
        us3.save_changes('tester', 'closed US3')
        self.assert_equals(26, self.controller.process_command(cmd_get))
        cmd_store.estimated = False
        self.assert_equals(13, self.controller.process_command(cmd_store))
        cmd_get.estimated = False
        self.assert_equals(13, self.controller.process_command(cmd_get))
    
    def test_team_commitment(self):
        """Tests store and retrieval of the team commitment of a sprint"""
        test_team = self.tm.create(name="Team#1")
        sprint = self.teh.create_sprint("TestSprint", team=test_team)
        self.assert_true(test_team.exists)
        # Set the initial USP/RT ratio to 2
        tm = TeamMetrics(self.env, sprint, test_team)
        tm[Key.RT_USP_RATIO] = 2
        tm.save()
        
        tm1 = self.tmm.create(name="Member#1", team=test_team)
        self.tmm.create(name="Member#2", team=test_team)
        self.tmm.create(name="Member#3", team=test_team)
        us1 = self.teh.create_ticket(Type.USER_STORY, props={Key.STORY_POINTS: '5',
                                                             Key.SPRINT: sprint.name})
        us2 = self.teh.create_ticket(Type.USER_STORY, props={Key.STORY_POINTS: '8',
                                                             Key.SPRINT: sprint.name})
        t1 = self.teh.create_ticket(Type.TASK, props={Key.REMAINING_TIME: '12',
                                                      Key.OWNER: tm1.name,
                                                      Key.SPRINT: sprint.name})
        # This task is not explicitly planned for the sprint, but because it is
        # linked should be calculated
        t2 = self.teh.create_ticket(Type.TASK, props={Key.REMAINING_TIME: '8',
                                                      Key.OWNER: tm1.name})
        # Make sure there is a remaining time entry on the first day of the sprint
        RemainingTime(self.env, t1).set_remaining_time(t1[Key.REMAINING_TIME], 
                                                       sprint.start)
        RemainingTime(self.env, t2).set_remaining_time(t2[Key.REMAINING_TIME], 
                                                       sprint.start)
        us1.link_to(t1)
        us1.link_to(t2)
        us2 = self.teh.load_ticket(ticket=us2)
        self.assert_equals(Type.USER_STORY, us2.get_type())
        self.assert_not_none(us2._calculated)
        # check the estimated remaining time for us2
        self.assert_equals(8 * 2, us2[Key.ESTIMATED_REMAINING_TIME])
        
        cmd_class = TeamController.CalculateAndStoreTeamCommitmentCommand
        cmd_store_commitment = cmd_class(self.env, sprint=sprint, team=test_team)
        commitment = TeamController(self.env).process_command(cmd_store_commitment)
        self.assert_equals(12 + 8 * 2, commitment)
        cmd_get_commitment = TeamController.GetTeamCommitmentCommand(self.env,
                                                                     sprint=sprint,
                                                                     team=test_team)
        self.assert_equals(commitment, 
                         self.controller.process_command(cmd_get_commitment))
    
    def test_get_team_metrics_command_returns_none_if_no_team_given(self):
        sprint_without_team = self.teh.create_sprint('FooSprint')
        cmd = TeamController.GetTeamCommitmentCommand(self.env, sprint=sprint_without_team)
        commitment = TeamController(self.env).process_command(cmd)
        self.assert_none(commitment)
    
    def test_can_return_hourly_capacity_on_specific_day(self):
        team, member1, member2 = self.team_with_two_members()
        
        capacities = team.capacity(member1.timezone()).hourly_capacities_for_day(today())
        self.assert_length(10, capacities)
        for capacity in capacities[:-1]:
            self.assert_equals(2, capacity.capacity)
    
    def test_last_entry_of_hourly_capacity_is_zero(self):
        team, member1, member2 = self.team_with_two_members()
        
        capacities = team.capacity(member1.timezone()).hourly_capacities_for_day(today())
        self.assert_equals(0, capacities[-1].capacity)
        
    
    def test_can_return_empty_list_if_no_capacity_is_there(self):
        team, member1, member2 = self.team_with_two_members()
        self.set_hours_for_day_on_team_member(0, today(), member1)
        self.set_hours_for_day_on_team_member(0, today(), member2)
        
        capacities = team.capacity(member1.timezone()).hourly_capacities_for_day(today())
        self.assert_length(0, capacities)
    
    def test_can_combine_different_timezones(self):
        team, member1, member2 = self.team_with_two_members()
        set_user_attribute_in_session(self.env, 'tz', 'GMT', member1.name)
        set_user_attribute_in_session(self.env, 'tz', 'GMT +1:00', member2.name)
        
        capacities = team.capacity(member1.timezone()).hourly_capacities_for_day(today())
        self.assert_length(11, capacities)
        self.assert_equals(1, capacities[0].capacity)
        self.assert_equals(1, capacities[-2].capacity)
    
    def test_can_cut_off_times_that_would_be_on_next_day(self):
        team, member1, member2 = self.team_with_two_members()
        set_user_attribute_in_session(self.env, 'tz', 'GMT', member1.name)
        set_user_attribute_in_session(self.env, 'tz', 'GMT -8:00', member2.name)
        viewer_timezone = member1.timezone()
        self.set_hours_for_day_on_team_member(0, yesterday(viewer_timezone), member2)
        # 15:00 at his place is 23:00 here, so two values should be lost
        
        day = today(tz=member1.timezone())
        capacities = team.capacity(viewer_timezone).hourly_capacities_for_day(day)
        self.assert_length(16, capacities)
        self.assert_equals(1, capacities[0].capacity)
        self.assert_equals(1, capacities[-2].capacity)
        last_hour_of_member1 = datetime.combine(day, time(23, tzinfo=member1.timezone()))
        self.assert_equals(last_hour_of_member1, capacities[-2].when)
    
    def test_cuts_off_times_that_would_be_on_previous_day(self):
        team, member1, member2 = self.team_with_two_members()
        set_user_attribute_in_session(self.env, 'tz', 'GMT', member1.name)
        set_user_attribute_in_session(self.env, 'tz', 'GMT +11:00', member2.name)
        
        viewer_timezone = utc
        # don't want to get values from tomorrow
        self.set_hours_for_day_on_team_member(0, tomorrow(viewer_timezone), member2)
        # 11:00 at his place is 0:00 here, so two values should be lost
        
        capacities = team.capacity(viewer_timezone).hourly_capacities_for_day(today())
        self.assert_length(17, capacities)
        self.assert_equals(1, capacities[0].capacity)
        self.assert_equals(1, capacities[-2].capacity)
        start_of_day_for_member1 = midnight(now(tz=viewer_timezone))
        self.assert_equals(start_of_day_for_member1, capacities[0].when)
    
    def test_cuts_off_times_that_would_be_on_previous_day_for_the_viewer(self):
        team, member1 = self.team_with_one_member()
        set_user_attribute_in_session(self.env, 'tz', 'GMT +11:00', member1.name)
        
        viewer_timezone = utc
        # don't want to get values from tomorrow
        self.set_hours_for_day_on_team_member(0, tomorrow(viewer_timezone), member1)
        # 11:00 at his place is 0:00 here, so two values should be lost
        
        capacities = team.capacity(viewer_timezone).hourly_capacities_for_day(today())
        self.assert_length(8, capacities)
        self.assert_equals(1, capacities[0].capacity)
        self.assert_equals(1, capacities[-2].capacity)
        start_of_day_for_member1 = midnight(now(tz=viewer_timezone))
        self.assert_equals(start_of_day_for_member1, capacities[0].when)
    
    def test_includes_times_from_previous_day_that_get_shifted_to_today_through_the_timezone_difference(self):
        team, member1, member2 = self.team_with_two_members()
        set_user_attribute_in_session(self.env, 'tz', 'GMT', member1.name)
        set_user_attribute_in_session(self.env, 'tz', 'GMT -7:00', member2.name)
        
        day = today(tz=member1.timezone())
        yesterday = day - timedelta(days=1)
        self.set_hours_for_day_on_team_member(9, yesterday, member2)
        # member2s last hour of yesterday should happen on today for member1
        capacities = team.capacity(member1.timezone()).hourly_capacities_for_day(day)
        member1_midnight = datetime.combine(day, time(0, tzinfo=member1.timezone()))
        self.assert_equals(member1_midnight, capacities[0].when)
        self.assert_equals(1, capacities[0].capacity)
    
    def test_includes_times_from_next_day_that_get_shifted_to_today_through_the_timezone_difference(self):
        team, member1, member2 = self.team_with_two_members()
        set_user_attribute_in_session(self.env, 'tz', 'GMT', member1.name)
        set_user_attribute_in_session(self.env, 'tz', 'GMT +10:00', member2.name)
        
        day = today(tz=member1.timezone())
        tomorrow = day + timedelta(days=1)
        self.set_hours_for_day_on_team_member(9, tomorrow, member2)
        # member2s first hour of tomorrow should happen on today for member1
        capacities = team.capacity(member1.timezone()).hourly_capacities_for_day(day)
        member1_last_hour = datetime.combine(day, time(23, tzinfo=member1.timezone()))
        self.assert_equals(member1_last_hour, capacities[-2].when)
        self.assert_equals(1, capacities[-2].capacity)
    
    def test_team_with_capacity_on_every_day_has_no_empty_days(self):
        team, member1 = self.team_with_one_member()
        member1.capacity = [1] * 7
        member1.save()
        start = now() - timedelta(days=7)
        end = now()
        self.assert_length(0, team.capacity().days_without_capacity_in_interval(start, end))
    
    def _create_team_with_weekends_off(self):
        team, member1 = self.team_with_one_member()
        member1.capacity = [1] * 5 + [0, 0]
        member1.save()
        return team
    
    def test_team_not_working_on_weekends_has_no_capacity_on_weekends(self):
        team = self._create_team_with_weekends_off()
        # exactly one week so we're sure that this interval covers two non-working days
        start = now() - timedelta(days=7)
        end = now()
        days_without_capacity = team.capacity().days_without_capacity_in_interval(start, end)
        self.assert_length(2, days_without_capacity)
        self.assert_equals(0, days_without_capacity[0].hour)
        self.assert_equals(0, days_without_capacity[0].minute)
    
    def test_days_without_capacity_respect_given_timestamp(self):
        team = self._create_team_with_weekends_off()
        end = now(utc)
        start = end - timedelta(days=7)
        bangkok_tz = get_timezone('GMT +7:00')
        days_without_capacity = team.capacity(bangkok_tz).days_without_capacity_in_interval(start, end)
        self.assert_equals(bangkok_tz, days_without_capacity[0].tzinfo)
    
    def test_days_without_capacity_include_last_day(self):
        team = self._create_team_with_weekends_off()
        end = datetime(2010, 5, 23, 3, 0, 0, tzinfo=localtz) # sunday
        start = end - timedelta(days=3)
        days_without_capacity = team.capacity().days_without_capacity_in_interval(start, end)
        self.assert_length(2, days_without_capacity)
    
    def _set_default_capacity_for_member(self, default_capacity, member):
        member.capacity = [default_capacity] * 7
        member.save()
    
    def test_can_return_capacity_series_for_interval(self):
        team, member1 = self.team_with_one_member()
        self._set_default_capacity_for_member(1, member1)
        # tomorrow -> date -> 0:00 on date -> removes everything on that day
        self.assert_length(2*9 + 2, team.capacity().hourly_capacities_in_interval(yesterday(), tomorrow()))
    
    def test_return_capacity_information_until_end_of_sprint_even_if_last_values_are_zero(self):
        self.teh.disable_sprint_date_normalization()
        team, member = self.team_with_one_member()
        self._set_default_capacity_for_member(0, member)
        sprint = self.teh.create_sprint('Foo Sprint')
        sprint.start = midnight(yesterday())
        sprint.end = midnight(day_after_tomorrow())
        
        capacities = team.capacity().hourly_capacities_in_sprint(sprint)
        # +1 because the last item is from 22:00-23:00
        self.assert_length(24*3+1, capacities)
    
    def test_can_sum_remaining_capacities_in_sprint(self):
        self.teh.disable_sprint_date_normalization()
        team, member = self.team_with_one_member()
        self._set_default_capacity_for_member(9*2, member)
        
        sprint =  self.teh.create_sprint(name="SprintWithContingent", team=team,
                                         start=midnight(yesterday()), 
                                         end=midnight(tomorrow()))
        summed = team.capacity().summed_hourly_capacities_in_sprint(sprint)
        # 2*9 (no. working hours), +8 (additional hours after zero), +1 (00:00-01:00 on the last day)
        self.assert_length(9*2+8+1, summed)
        self.assert_equals(2*(9*2), summed[0].capacity)
        self.assert_equals(0, summed[-1].capacity)
    
    def test_capacity_can_take_timezone_parameter(self):
        team, member = self.team_with_one_member()
        self._set_default_capacity_for_member(0, member)
        set_user_attribute_in_session(self.env, 'tz', 'GMT', member.name)
        self.set_hours_for_day_on_team_member(9, today(member.timezone()), member)
        
        viewer_timezone = get_timezone('GMT -12:00')
        capacitator = team.capacity(viewer_timezone)
        # Need to take the member timezone for start and end, to make sure that we really cut off all
        # workhours he has on the previous day - even though they would be on the current day when
        # viewed from the viewers timezone.
        hourly_capacities = capacitator.hourly_capacities_in_interval(today(tz=member.timezone()), tomorrow(tz=member.timezone()))
        self.assert_length(7, hourly_capacities)
    
    def test_contingents_are_removed_from_capacity(self):
        team, member = self.team_with_one_member()
        start = parse_date("2008-09-08T08:00:00")
        sprint =  self.teh.create_sprint(name="SprintWithContingent", start=start, duration=10, team=team)
        self.teh.add_contingent_to_sprint('Contingent', 100, sprint)
        self._set_default_capacity_for_member(9, member)
        
        capacities = team.capacity().hourly_capacities_in_sprint(sprint)
        capacity = sum(map(lambda each: each.capacity, capacities))
        self.assert_almost_equals(108 - 100, capacity, max_delta=.01)


    def test_will_contain_second_team_member_after_invalidating(self):
        team, member = self.team_with_one_member()
        self.assert_contains(member, team.members)
        member2 = self._add_member_to_team("member2", team)
        self.assert_not_contains(member2, team.members)
        team.invalidate_team_member_cache()
        self.assert_contains(member2, team.members)

    def test_can_invalidate_empty_cache(self):
        team = self.team_with_no_member()
        team.invalidate_team_member_cache()
        self.assert_length(0, team.members)


class TestTeamMember(AgiloTestCase):
    
    def setUp(self):
        self.super()
        self.tmm = TeamMemberModelManager(self.teh.get_env())
    
    def testTimeSheet(self):
        """Tests the accessor and mutator methods for attribute "time_sheet"."""
        test_ts_1 = [1.5, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0]
        test_ts_2 = [7.3, 6.0, 5.0, 4.0, 3.0, 2.0, 1.0]
        # test the default constructor, capacity should return decimals
        team_member = self.tmm.create(name="Team Member #1", default_capacity=test_ts_1)
        self.assert_equals(team_member.capacity, test_ts_1)
        self.tmm.get_cache().invalidate()
        team_member = self.tmm.get(name="Team Member #1")
        self.assert_equals(team_member.capacity, test_ts_1)
        
        team_member.capacity = test_ts_2
        self.assert_equals(team_member.capacity, test_ts_2)
        self.assert_true(self.tmm.save(team_member))
        team_member = self.tmm.get(name="Team Member #1")
        self.assert_equals(team_member.capacity, test_ts_2)
    
    def test_set_get_session_attribute(self):
        team_member = self.tmm.create(name="test_member")
        env = self.teh.get_env()
        set_user_attribute_in_session(env, 'test', 'Test', team_member.name)
        self.assert_equals('Test', get_user_attribute_from_session(env, 'test', team_member.name))
    
    def test_set_get_full_name(self):
        team_member = self.tmm.create(name="test_member")
        team_member.full_name = 'Test Member'
        self.assert_equals('Test Member', team_member.full_name)
    
    def test_team_member_in_team(self):
        team = self.teh.create_team(name="Test Team")
        tm1 = self.tmm.create(name="tm1", team=team)
        self.assert_true(tm1.exists)
        tm2 = self.tmm.create(name="tm2", team=team)
        self.assert_true(tm2.exists)
        tm3 = self.tmm.create(name="tm3")
        self.assert_true(tm3.exists)
        # Check members of the team using the __cmp__ of persistent object
        self.assert_equals(2, len(team.members))
        self.assert_true(tm1 in team.members)
        self.assert_true(tm2 in team.members)
        self.assert_false(tm3 in team.members)
    
    def test_set_get_email(self):
        team_member = self.tmm.create(name="test_member")
        team_member.email = "test.member@test.com"
        self.assert_equals('test.member@test.com', team_member.email)
    
    def test_can_load_name_and_email_from_session_attributes(self):
        # Create a team member in the session simulating registration
        full_name = "Team Member Test"
        email = "team@member.test"
        
        set_user_attribute_in_session(self.env, 'name', full_name, 'tm')
        set_user_attribute_in_session(self.env, 'email', email, 'tm')
        
        tm = self.tmm.create(name='tm')
        self.assert_equals(full_name, tm.full_name)
        self.assert_equals(email, tm.email)
    
    def test_can_access_timezone_in_session_table(self):
        timezone_name = "GMT +7:00"
        timezone_offset = timedelta(hours=7)
        timezone = get_timezone(timezone_name)
        self.assert_equals(timezone_offset, timezone.utcoffset(None))
        
        set_user_attribute_in_session(self.env, 'tz', timezone_name, 'tm')
        
        member = self.tmm.create(name='tm')
        self.assert_equals(timezone_offset, member.timezone().utcoffset(None))
    
    def test_falls_back_to_server_timezone_if_none_is_set_in_session_table(self):
        member = self.tmm.create(name='tm')
        local_timezone_offset = localtz.utcoffset(now())
        self.assert_equals(local_timezone_offset, member.timezone().utcoffset(now()))
    
    def test_falls_back_to_server_timezone_if_garbage_is_set_in_session_table(self):
        set_user_attribute_in_session(self.env, 'tz', "fnord", 'tm')
        member = self.tmm.create(name='tm')
        local_timezone_offset = localtz.utcoffset(now())
        self.assert_equals(local_timezone_offset, member.timezone().utcoffset(now()))
    
    def test_knows_hour_at_which_work_starts_and_ends(self):
        member = self.tmm.create(name='tm')
        self.assert_equals(9, member.time_workday_starts().hour)
        self.assert_equals(18, member.time_workday_ends().hour)
    
    def test_knows_number_of_hours_of_workday(self):
        member = self.tmm.create(name='tm')
        self.assert_equals(9, member.number_of_working_hours_on_workday())
    

class TestTeamMemberCalendar(AgiloTestCase):
    """Tests the team member calendar object"""
    def setUp(self):
        self.super()
        self.tm = self.teh.create_member(name='TM1')
        self.tm.capacity = [6,6,6,6,6,0,0]
        self.assert_true(self.tm.save())
        self.tmc = self.tm.calendar
    
    def testCalendarForTeamMember(self):
        """Tests the calendar for a TeamMember"""
        today = to_datetime(datetime(2008, 9, 1)).date()
        self.tmc.set_hours_for_day(4, today)
        self.assert_equals(self.tmc.get_hours_for_day(today), 4)
        self.assert_equals(self.tmc.get_hours_for_day(today + one_day), 6)
        # Now save and check if is still there
        self.assert_true(self.tmc.save())
        # reload
        tmc2 = TeamMemberCalendar(self.teh.get_env(), self.tm)
        self.assert_equals(tmc2.get_hours_for_day(today), 4)
        self.assert_equals(tmc2.get_hours_for_day(today + one_day), 6)
    
    def testCalendarForTeamMemberInterval(self):
        """Tests the calendar returned for a given interval of time"""
        self.tmc.set_hours_for_day(5, today())
        cal = self.tmc.get_hours_for_interval(today() - (3 * one_day),
                                              today() + (3 * one_day))
        self.assert_equals(cal[today()], 5)
        self.assert_equals(len(cal), 7)
    
    def test_can_return_list_of_capacities(self):
        self.tmc.set_hours_for_day(23, today()) # just to ensure there is some
        capacities = self.tmc.hourly_capacities_for_day(today())
        self.assert_length(self.tm.number_of_working_hours_on_workday(), capacities)
    
    def test_can_return_correct_capacities_per_hour(self):
        capacity = 6
        self.tmc.set_hours_for_day(capacity, today())
        capacities = self.tmc.hourly_capacities_for_day(today())
        
        work_hours = self.tm.number_of_working_hours_on_workday()
        capacity_per_hour = capacity / float(work_hours)
        for capacity in capacities:
            self.assert_almost_equals(capacity_per_hour, capacity.capacity, max_delta=0.01)
    
    def test_hours_will_increase_monotoneously_in_capacities(self):
        self.tmc.set_hours_for_day(23, today()) # just something
        capacities = self.tmc.hourly_capacities_for_day(today())
        start_time = capacities[0].when
        for index, capacity in enumerate(capacities):
            self.assert_equals(start_time.hour + index, capacity.when.hour)
    
    def test_capacities_have_correct_timezone(self):
        self.tmc.set_hours_for_day(23, today()) # just something
        capacities = self.tmc.hourly_capacities_for_day(today())
        start_time = capacities[0].when
        self.assert_equals(self.tm.timezone(), start_time.tzinfo)
    
    def test_returns_no_capacity_if_capacity_is_zero(self):
        self.tmc.set_hours_for_day(0, today()) # just something
        capacities = self.tmc.hourly_capacities_for_day(today())
        self.assert_length(0, capacities)
    

if __name__ == '__main__':
    from agilo.test.testfinder import run_unit_tests
    run_unit_tests(__file__)

