# -*- encoding: utf-8 -*-
#   Copyright 2008 Agile42 GmbH, Berlin (Germany)
#   Copyright 2007 Andrea Tomasini <andrea.tomasini_at_agile42.com>
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
#       - Andrea Tomasini <andrea.tomasini_at_agile42.com>
#       - Felix Schwarz <felix.schwarz__at__agile42.com>

from datetime import datetime, timedelta

from trac.resource import Resource
from trac.util.datefmt import parse_date, to_timestamp, utc

from agilo.scrum.metrics import TeamMetrics
from agilo.scrum.sprint import Sprint, SprintModelManager
from agilo.scrum.team import TeamMemberModelManager
from agilo.test import AgiloTestCase
from agilo.utils import Key, Type, Realm
from agilo.utils.config import AgiloConfig
from agilo.utils.days_time import count_working_days, normalize_date, now


class TestSprint(AgiloTestCase):
    """
    Tests the Sprint object
    """
    def setUp(self):
        self.super()
        self.start = normalize_date(now())
        duration = timedelta(days=20)
        self.end = normalize_date(self.start + duration)
        self.manager = SprintModelManager(self.env)
        self.tmm = TeamMemberModelManager(self.env)
    
    def testSprintCreationWithDates(self):
        """Tests the Sprint creation with the start and end date"""
        sprint = self.manager.create(name="Test Sprint", start=self.start, end=self.end)
        self.assert_equals(sprint.duration, count_working_days(self.start.date(), self.end.date()))
        # Now save the sprint and reload it from the DB
        # AT: With the manager the sprint is already saved
        # self.manager.save(sprint)
        sprint = self.manager.get(name="Test Sprint")
        self.assert_equals(sprint.duration, count_working_days(self.start.date(), self.end.date()))
        self.assert_equals(self.end, sprint.end)
        self.assert_equals(self.start, sprint.start)
        # Now add a description and test the reload
        sprint.description = 'This is a test Sprint'
        self.manager.save(sprint)
        # clear the cache so we are sure it will be reloaded from the DB
        self.manager.get_cache().invalidate()
        sprint = self.manager.get(name="Test Sprint")
        self.assert_equals(sprint.description, 'This is a test Sprint')
    
    def testSprintUpdateDuration(self):
        """
        Tests the Sprint update of the duration in case start, or end, 
        or duration are changed
        """
        sprint = self.manager.create(name="Test Sprint", start=self.start, end=self.end)
        self.assert_equals(sprint.duration, count_working_days(sprint.start.date(), sprint.end.date()))
        # Now change the start date +1
        sprint.start = sprint.start + timedelta(days=1)
        self.assert_equals(sprint.duration, count_working_days(sprint.start.date(), sprint.end.date()))
        # Now move the end -1
        sprint.end = sprint.end - timedelta(days=1)
        self.assert_equals(sprint.duration, count_working_days(sprint.start.date(), sprint.end.date()))
    
    def testSprintCreateWithStartDuration(self):
        """
        Test the creation of a sprint setting the start date and the
        duration in working days
        """
        sprint = self.teh.create_sprint(name="Test Sprint",
                                           start=self.start, 
                                           end=self.end)
        another_sprint = self.teh.create_sprint(name="Another Sprint",
                                                   start=self.start,
                                                   duration=sprint.duration)
        # Check they have the same end date...
        self.assert_equals(sprint.end.date(), another_sprint.end.date())
        # Now, save and load and check that the data are set correctly
        # FIXME: where is the check mentioned in the above comment?
        # Now change the end and see if the duration change as well
        another_sprint.end = another_sprint.end + timedelta(days=1)
        self.assert_true(another_sprint.duration > sprint.duration)

    def testSprintSelect(self):
        """Test the Sprint select function"""
        self.manager.create(name="Test Sprint 1",
                                  start=self.start,
                                  end=self.end)
        self.manager.create(name="Test Sprint 2",
                                  start=self.start,
                                  end=self.end)
        self.manager.create(name="Test Sprint 3",
                                  start=parse_date("2008-06-10"),
                                  end=parse_date("2008-06-30"))
        # Now test the select
        sprints = self.manager.select(criteria={'end': '> %d' % to_timestamp(now())})
        self.assert_equals(len(sprints), 2)
        sprints = self.manager.select()
        self.assert_equals(len(sprints), 3)

    def testDeleteSprint(self):
        """Tests the deletion of a Sprint"""
        sprint1 = self.manager.create(name="Test Sprint 1", 
                                            start=self.start, 
                                            end=self.end)
        self.assert_true(sprint1.exists)
        self.assert_true(self.manager.delete(sprint1))
        # Now make sure is not there anymore
        self.manager.get(name="Test Sprint 1")
    
    def testRenameSprint(self):
        """Tests the Sprint rename"""
        name = 'Test sprint name'
        sprint = self.manager.create(name=name, start=self.start, end=self.end)
        self.assert_true(sprint.exists)
        self.assert_equals(sprint.name, name)
        
        # create a ticket for this sprint
        t = self.teh.create_ticket(Type.USER_STORY, props={Key.SPRINT: name})
        # reload ticket
        self.assert_equals(t[Key.SPRINT], name)
        # create a metrics object
        team = self.teh.create_team(name='Testteam')
        metrics = TeamMetrics(self.env, sprint, team)
        metrics['test'] = 1.0
        metrics.save()

        # Rename the sprint
        new_name = 'New sprint name'
        sprint.name = new_name
        self.assert_true(self.manager.save(sprint))
        self.assert_equals(sprint.name, new_name)
        # Remove the sprint from the cache and reload it again
        self.manager.get_cache().invalidate(model_instance=sprint)
        # check new name after reload
        sprint = self.manager.get(name=new_name)
        self.assert_equals(sprint.name, new_name)

        t = self.teh.load_ticket(t_id=t.id)
        # sprint in ticket and metrics should be renamed as well
        self.assert_equals(t[Key.SPRINT], new_name)
        metrics = TeamMetrics(self.env, sprint, team)
        self.assert_equals(metrics.sprint, sprint)
        self.assert_equals(metrics['test'], 1.0)
        
        # Rename the sprint with some not allowed characters
        new_name = "That's my sprint!"
        sprint.name = new_name
        self.assert_true(sprint.save())
        self.assert_equals(sprint.name, new_name)

        # check new name after reload
        sprint = Sprint(self.env, name=new_name)
        self.assert_equals(sprint.name, new_name)

    def testAssignTeamToSprint(self):
        """Tests the assignment of a team to a Sprint"""
        team = self.teh.create_team(name="The Team")
        self.teh.create_member(name="Team Member 1", team=team)
        self.teh.create_member(name="Team Member 2", team=team)
        # Now create a Sprint
        s = self.manager.create(name="Test S", team=team)
        
        self.assert_equals(team.name, s.team.name)
        for i, member in enumerate(team.members):
            self.assert_equals(member.name, s.team.members[i].name)
    
    def testSprintClosedAndIsCurrentlyRunning(self):
        """Tests the is_closed and is_started"""
        start = now() - timedelta(days=3) # no risk to get a weekend
        s = self.teh.create_sprint("Test", start=start)
        self.assert_true(s.is_currently_running)
        self.assert_false(s.is_closed)
        s.start += timedelta(days=5) # Move 5 to make sure that we will overcome also a normalization over a weekend
        self.assert_false(s.is_currently_running, "%s <= %s  < %s" % \
                         (s.start, start, s.end))
        self.assert_false(s.is_closed)
        
        # check functions for an old, closed sprint
        s.start = parse_date("2008-01-01")
        s.end = parse_date("2008-01-31")
        self.assert_false(s.is_currently_running)
        self.assert_true(s.is_closed)
    
    def testSprintIsNotCurrentlyRunningAfterSprintEnd(self):
        today = now()
        sprint_start = today - timedelta(days=20)
        sprint = self.teh.create_sprint("Test", start=sprint_start)
        sprint.end = today - timedelta(days=10)
        # Sprint ended ten days before today
        self.assert_false(sprint.is_currently_running)
        self.assert_true(sprint.is_closed)
    
    def testLoadSprintWhichHasNoStartDate(self):
        self.manager.create(name='foo')
        sprint = self.manager.get(name='foo')
        self.assert_true(sprint.exists)
        self.assert_equals('foo', sprint.name)
    
    def testCanDisableSprintStartDateNormalization(self):
        config = AgiloConfig(self.env).get_section(AgiloConfig.AGILO_GENERAL)
        option_name = 'sprints_can_start_or_end_on_weekends'
        self.assert_false(config.get_bool(option_name))
        config.change_option(option_name, True, save=True)
        self.assert_true(AgiloConfig(self.env).sprints_can_start_or_end_on_weekends)
        
        start = datetime(2009, 05, 30, tzinfo=utc)
        sprint = self.teh.create_sprint('Foo', start=start)
        self.assert_equals(start, sprint.start)
        self.assert_equals(utc, sprint.start.tzinfo)
    
    def testManagerAttributeIsNotSerialized(self):
        sprint = self.teh.create_sprint('Foo Sprint')
        sprint_dict = sprint.as_dict()
        self.assert_false('manager' in sprint_dict)
    
    def test_can_build_resource(self):
        sprint = self.teh.create_sprint('Foo Sprint')
        self.assert_equals(Resource(Realm.SPRINT, sprint.name), sprint.resource())
    
    def test_can_build_by_duration_without_normalization(self):
        self.teh.disable_sprint_date_normalization()
        some_friday = datetime(day=30, month=4, year=2010)
        self.assert_equals(4, some_friday.weekday())
        
        sprint = self.teh.create_sprint('Foo Sprint', start=some_friday, duration=4)
        sprint_length = (sprint.end - sprint.start).days
        self.assert_equals(3, sprint_length)
    


if __name__ == '__main__':
    from agilo.test.testfinder import run_unit_tests
    run_unit_tests(__file__)

