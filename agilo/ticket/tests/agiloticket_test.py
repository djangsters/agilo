#!/usr/bin/env python
# -*- coding: utf-8 -*-
#   Copyright 2008 Agile42 GmbH - Andrea Tomasini
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
# Authors:
#     - Andrea Tomasini <andrea.tomasini__at__agile42.com>
#     - Felix Schwarz <felix.schwarz__at__agile42.com>

from trac.env import Option
from trac.ticket.model import Milestone
from trac.util.datefmt import to_timestamp

from agilo.test import AgiloTestCase, TestEnvHelper
from agilo.ticket.api import AgiloTicketSystem
from agilo.ticket.model import AgiloTicket, AgiloTicketModelManager
from agilo.utils import Key, Type
from agilo.utils.config import AgiloConfig
from agilo.utils.days_time import now


class AgiloTicketOwnerTest(AgiloTestCase):
    # Set the restrict_owner option in the config
    strict = True
    def test_owner_team_member_with_sprint_related_tickets(self):
        """
        Tests that the owner of a sprint related ticket, in case of restrict_owner
        option, is limited to the team members assigned to the sprint, in case the
        ticket has the Remaining Time property
        """
        teh = self.teh
        env = self.env
        self.assert_true(AgiloTicketSystem(env).restrict_owner)
        t = teh.create_team('A-Team')
        self.assert_true(t.save())
        s = teh.create_sprint('Test Me', team=t)
        self.assert_equals('Test Me', s.name)
        self.assert_equals(s.team, t)
        tm1 = teh.create_member('TM1', t)
        self.assert_true(tm1.save())
        tm2 = teh.create_member('TM2', t)
        self.assert_true(tm2.save())
        tm3 = teh.create_member('TM3')
        self.assert_true(tm3.save())
        
        self.assert_contains(tm1.name, [m.name for m in t.members])
        self.assert_contains(tm2.name, [m.name for m in t.members])
        
        # Now make a ticket that is dependent from the sprint
        task = teh.create_ticket(Type.TASK, 
                                 props={Key.REMAINING_TIME: '12.5',
                                        Key.OWNER: tm1.name,
                                        Key.SPRINT: s.name})
        self.assert_equals(s.name, task[Key.SPRINT])
        f = task.get_field(Key.OWNER)
        self.assert_true(tm1.name in f[Key.OPTIONS])
        self.assert_true(tm2.name in f[Key.OPTIONS])
        self.assert_false(tm3.name in f[Key.OPTIONS])
    
    
class TestAgiloTicket(AgiloTestCase):
    
    def test_can_set_basic_properties_before_creating_agilo_ticket(self):
        ticket = AgiloTicket(self.env)
        ticket[Key.TYPE] = "story"
        ticket[Key.SUMMARY] = "This is an AgiloTicket"
        ticket[Key.DESCRIPTION] = "This is the description of the ticket..."
        ticket_id = ticket.insert()
        
        story = AgiloTicket(self.env, ticket_id)
        for attribute_name in (Key.TYPE, Key.SUMMARY, Key.DESCRIPTION):
            self.assert_equals(ticket[attribute_name], story[attribute_name])
    
    def test_can_use_numbers_for_ticket_properties(self):
        task = AgiloTicket(self.env, t_type=Type.TASK)
        # trac tries to strip() ticket properties so AgiloTicket needs convert
        # the value to a str
        task[Key.REMAINING_TIME] = 5
        task[Key.SUMMARY] = u'Should work with unicode values: äöüß'
    
    def test_do_not_stringify_none_for_ticket_properties(self):
        task = AgiloTicket(self.env, t_type=Type.TASK)
        task[Key.REMAINING_TIME] = None
        task.insert()
        task[Key.REMAINING_TIME] = 3
        self.assert_none(task._old[Key.REMAINING_TIME])
    
    def _matching_properties(self, agilo_ticket):
        # returns true if the ticket properties match the defined
        # ticket type properties
        match = True
        config_fields = AgiloConfig(self.env).TYPES.get(agilo_ticket.get_type(), [])
        #print "Config Fields: %s" % config_fields
        for f in agilo_ticket.fields:
            if f.has_key(Key.SKIP):
                #print "Field: %s, Skip: %s Match: %s" % (f[Key.NAME], f[Key.SKIP], match)
                match = match and (f[Key.SKIP] != (f[Key.NAME] in config_fields))
        return match
        
    def test_correct_handling_of_ticket_types(self):    
        story = AgiloTicket(self.env, t_type=Type.USER_STORY)
        story[Key.SUMMARY] = "This is a story..."
        story[Key.DESCRIPTION] = "A very nice one..."
        self.assert_true(self._matching_properties(story))
        story.insert()
        self.assert_true(self._matching_properties(story))
        
        # Not existing type should show all the properties
        nonex = AgiloTicket(self.env, t_type="nonex")
        nonex[Key.SUMMARY] = "This is a story..."
        nonex[Key.DESCRIPTION] = "A very nice one..."
        nonex.insert()
        self.assert_true(self._matching_properties(nonex))
        
        # Setting type on the fly should work
        task = AgiloTicket(self.env, t_type=Type.TASK)
        task[Key.SUMMARY] = "This should be a task"
        self.assert_true(self._matching_properties(task))
        task.insert()
        self.assert_true(self._matching_properties(task))
    
    def test_new_agilo_tickets_dont_have_a_resolution_by_default(self):
        # This bug was triggered by declaring the default resolution option in
        # trac's TicketModule so we make sure that the option is always known
        # when running this test
        Option('ticket', 'default_resolution', 'fixed', '')
        ticket = AgiloTicket(self.env, t_type=Type.TASK)
        self.assert_equals('', ticket[Key.RESOLUTION])
    
    def test_story_has_total_remaining_time_and_estimated_remaining_time_by_default(self):
        story = AgiloTicket(self.env, t_type=Type.USER_STORY)
        self.assert_equals([Key.TOTAL_REMAINING_TIME, Key.ESTIMATED_REMAINING_TIME], 
                           story.get_calculated_fields_names())
    
    def test_sync_milestone_attribute_with_sprint_automatically(self):
        milestone = self.teh.create_milestone('Test Milestone')
        sprint = self.teh.create_sprint('Test', start=now(), duration=20, milestone=milestone)
        
        task = self.teh.create_task(summary='Foo', sprint=sprint.name)
        self.assert_equals(Type.TASK, task[Key.TYPE])
        self.assert_equals(milestone.name, task[Key.MILESTONE])
        self.assert_equals(sprint.milestone, task[Key.MILESTONE])
        
        task[Key.MILESTONE] = 'Another One'
        task.save_changes('tester', 'changed milestone')
        self.assert_equals('Another One', task[Key.MILESTONE])
        self.assert_equals('', task[Key.SPRINT])
        self.teh.move_changetime_to_the_past([task])
        # Now reset it to the Sprint1
        task[Key.SPRINT] = sprint.name
        task.save_changes('tester', 'changed sprint back')
        self.assert_equals(milestone.name, task[Key.MILESTONE])
        self.assert_equals(sprint.milestone, task[Key.MILESTONE])
    
    def test_milestone_for_task_is_deleted_when_task_gets_removed_from_sprint(self):
        sprint = self.teh.create_sprint('fnord')
        task = self.teh.create_task(sprint=sprint)
        self.assert_equals(sprint.milestone, task[Key.MILESTONE])
        
        task[Key.SPRINT] = None
        task.save_changes(None, None)
        self.assert_equals('', task[Key.MILESTONE])
        self.assert_equals('', AgiloTicket(self.env, tkt_id=task.id)[Key.MILESTONE])
    
    def test_ticket_offers_sprints_as_options(self):
        # Added when Trac 0.12 was released as TicketSystem in 0.12 does not
        # call _get_custom_fields anymore due to internal changes.
        sprint = self.teh.create_sprint('ASprint')
        task = self.teh.create_task()
        
        sprint_field = [field for field in task.fields if field[Key.NAME] == Key.SPRINT][0]
        self.assert_equals([sprint.name], sprint_field['options'])
    
    def test_resource_list_when_no_resource_field_present(self):
        story = AgiloTicket(self.env, t_type=Type.USER_STORY)
        self.assert_equals('', story[Key.RESOURCES])
        self.assert_equals(0, len(story.get_resource_list()))
    
    def test_resource_list_can_include_owner(self):
        story = AgiloTicket(self.env, t_type=Type.USER_STORY)
        story[Key.OWNER] = 'Foo'
        self.assert_equals(0, len(story.get_resource_list()))
        self.assert_equals(['Foo'], story.get_resource_list(include_owner=True))
        story[Key.OWNER] = ''
        self.assert_equals(0, len(story.get_resource_list(include_owner=True)))
    
    def test_resource_list_with_owner_and_resources(self):
        story = AgiloTicket(self.env, t_type=Type.USER_STORY)
        story[Key.OWNER] = 'Foo'
        story[Key.RESOURCES] = 'Bar, Baz'
        self.assert_equals(['Foo', 'Bar', 'Baz'], 
                         story.get_resource_list(include_owner=True))
    
    def test_owner_is_only_listed_once_in_resource_list(self):
        story = AgiloTicket(self.env, t_type=Type.USER_STORY)
        story[Key.OWNER] = 'Foo Bar'
        story[Key.RESOURCES] = 'Foo Bar'
        self.assert_equals(['Foo Bar'], story.get_resource_list(include_owner=True))
    
    def test_split_resource_string_for_resource_list(self):
        task = AgiloTicket(self.env, t_type=Type.TASK)
        task[Key.RESOURCES] = 'foo,bar,baz'
        self.assert_equals(['foo', 'bar', 'baz'], task.get_resource_list())
    
    def test_strip_usernames_for_resource_list(self):
        task = AgiloTicket(self.env, t_type=Type.TASK)
        task[Key.RESOURCES] = '  foo, bar,baz  '
        self.assert_equals(['foo', 'bar', 'baz'], task.get_resource_list())
    
    def test_empty_resource_list_for_empty_resource_string(self):
        task = AgiloTicket(self.env, t_type=Type.TASK)
        task[Key.RESOURCES] = ''
        self.assert_equals([], task.get_resource_list())
        
        task[Key.RESOURCES] = '   '
        self.assert_equals([], task.get_resource_list())
        
        task[Key.RESOURCES] = ' ,  , ,  '
        self.assert_equals([], task.get_resource_list())
        
    def test_get_field_with_field_name(self):
        """Tests the method get_field of a ticket, that returns the field dictionary"""
        task = AgiloTicket(self.env, t_type=Type.TASK)
        f = task.get_field(Key.REMAINING_TIME)
        self.assert_not_none(f)
        self.assert_equals(Key.REMAINING_TIME, f[Key.NAME])
        
        us = AgiloTicket(self.env, t_type=Type.USER_STORY)
        f = us.get_field(Key.STORY_POINTS)
        self.assert_not_none(f)
        self.assert_equals(Key.STORY_POINTS, f[Key.NAME])
        
        # Now calculated fields
        c = us.get_field(Key.TOTAL_REMAINING_TIME)
        self.assert_not_none(c)
        self.assert_equals(Key.TOTAL_REMAINING_TIME, c[Key.NAME])
    
    def test_changing_type_restore_correct_fields(self):
        """Tests that changing a ticket type restores the correct fields for
        that type"""
        t = AgiloTicket(self.env, t_type=Type.TASK)
        self.assert_true(self._matching_properties(t))
        # Now change that to a story
        t[Key.TYPE] = Type.USER_STORY
        self.assert_true(self._matching_properties(t))
        # Now reload config and change to bug
        ac = AgiloConfig(self.env)
        ac.reload()
        t[Key.TYPE] = Type.BUG
        self.assert_true(self._matching_properties(t))
        # Now add a field on the fly and see if it is adapting to it
        agilo_types = ac.get_section(ac.AGILO_TYPES)
        ticket_custom = ac.get_section(ac.TICKET_CUSTOM)
        ticket_custom.change_option('customer', 'text')
        ticket_custom.change_option('customer.label', 'Customer')
        fields = agilo_types.get_list(Type.BUG)
        fields.append('customer')
        # notice the save to force the reload of the config
        agilo_types.change_option('story', ','.join(fields), save=True)
        t[Key.TYPE] = Type.USER_STORY
        self.assert_true('customer' in t.fields_for_type, \
                        "No 'customer' in %s" % t.fields_for_type)
        t['customer'] = 'My Own Customer'
        self.assert_true(self._matching_properties(t))
        t.insert()
        self.assert_true(self._matching_properties(t))
        self.assert_equals('My Own Customer', t['customer'])
        
    def test_saving_of_custom_properties_works_on_model(self):
        """Tests that the custom properties are saved on insert"""
        us = AgiloTicket(self.env)
        us[Key.TYPE] = Type.USER_STORY
        us[Key.SUMMARY] = "This is a story with 5 points"
        us[Key.DESCRIPTION] = "As a user..."
        # Now a custom property
        us[Key.STORY_POINTS] = '5'
        us_id = us.insert()
        # Now reload the story
        same_us = AgiloTicket(self.env, tkt_id=us_id)
        self.assert_equals(Type.USER_STORY, same_us[Key.TYPE])
        self.assert_equals('5', same_us[Key.STORY_POINTS])
        
    def _set_default_type(self, new_value):
        agilo_config = AgiloConfig(self.env)
        old_value = agilo_config.get('default_type', 'ticket')
        agilo_config.change_option('default_type', new_value, 
                                   section='ticket', save=True)
        return old_value
    
    def test_new_ticket_uses_default_type_if_none_given(self):
        # This is the unit test covering bug #611 (see also regression test
        # TestOnlyTasksFieldsAreShownInPreview)
        def field_names(ticket):
            return [f['name'] for f in ticket.fields]
        
        old_default_type = self._set_default_type(Type.TASK)
        try:
            story = AgiloTicket(self.env, t_type=Type.USER_STORY)
            self.assert_equals(Type.USER_STORY, story[Key.TYPE])
            self.assert_true(Key.STORY_POINTS in field_names(story))
            self.assert_false(Key.REMAINING_TIME in field_names(story))
            self.assert_false(Key.BUSINESS_VALUE in field_names(story))
            
            ticket = AgiloTicket(self.env)
            self.assert_equals(Type.TASK, ticket[Key.TYPE])
            self.assert_true(Key.REMAINING_TIME in field_names(ticket))
            self.assert_false(Key.STORY_POINTS in field_names(ticket))
            self.assert_false(Key.BUSINESS_VALUE in field_names(ticket))
        finally:
            self._set_default_type(old_default_type)
    
    def test_ticket_knows_if_it_is_task_like(self):
        task = AgiloTicket(self.env, t_type=Type.TASK)
        self.assert_true(task.is_readable_field(Key.REMAINING_TIME))
        self.assert_true(task.is_task_like())
    
    def test_ticket_knows_if_not_task_like(self):
        story = AgiloTicket(self.env, t_type=Type.USER_STORY)
        self.assert_false(story.is_readable_field(Key.REMAINING_TIME))
        self.assert_false(story.is_task_like())
    
    def test_ticket_is_task_like_if_it_has_remaining_time_field(self):
        self.teh.add_field_for_type(Key.REMAINING_TIME, Type.USER_STORY)
        story = AgiloTicket(self.env, t_type=Type.USER_STORY)
        self.assert_true(story.is_readable_field(Key.REMAINING_TIME))
        self.assert_true(story.is_task_like())
    
    def test_tickets_know_when_they_were_changed(self):
        task = self.teh.create_task()
        self.assert_time_equals(now(), task.time_changed)
        self.assert_time_equals(now(), task.values['changetime'])
    
    def test_tickets_know_when_they_were_created(self):
        task = self.teh.create_task()
        self.assert_time_equals(now(), task.time_created)
        self.assert_time_equals(now(), task.values['time'])
    
    def test_can_serialize_task_to_dict(self):
        task = AgiloTicket(self.env, t_type=Type.TASK)
        self.assertNotEqual('fixed', task[Key.RESOLUTION])
        task[Key.SUMMARY] = 'My Summary'
        task.insert()
        expected = {
            # required
            Key.ID: task.id,
            Key.TYPE: Type.TASK,
            Key.SUMMARY: 'My Summary',
            Key.DESCRIPTION: '',
            Key.STATUS: '',
            Key.RESOLUTION: '',
            Key.REPORTER: '',
            Key.OWNER: '',
            # type specific
            Key.SPRINT: '',
            Key.REMAINING_TIME: '',
            Key.RESOURCES: '',
            
            # Key.Options is not used in order to reduce required data to 
            # transfer for a backlog load.
            
            'outgoing_links': [],
            'incoming_links': [],
            'time_of_last_change': to_timestamp(task.time_changed),
            'ts': str(task.time_changed),
        }
        if AgiloTicketSystem.is_trac_1_0():
            from trac.util.datefmt import to_utimestamp
            expected.update({'view_time': str(to_utimestamp(task.time_changed))})

        self.assert_equals(expected, task.as_dict())
    
    def test_can_serialize_calculated_fields(self):
        story = AgiloTicket(self.env, t_type=Type.USER_STORY)
        task = AgiloTicket(self.env, t_type=Type.TASK)
        task[Key.REMAINING_TIME] = '5'
        story.link_to(task)
        story.insert()
        self.assert_equals(5, story.as_dict()[Key.TOTAL_REMAINING_TIME])
    
    def test_can_serialize_links(self):
        task = AgiloTicket(self.env, t_type=Type.TASK)
        task.insert()
        story = AgiloTicket(self.env, t_type=Type.USER_STORY)
        story.link_to(task)
        story.insert()
        self.assert_equals([task.id], story.as_dict()['outgoing_links'])
        self.assert_equals([story.id], task.as_dict()['incoming_links'])
    
    def test_throws_exception_if_not_persisted_ticket_should_be_serialized(self):
        task = AgiloTicket(self.env, t_type=Type.TASK)
        self.assert_raises(ValueError, task.as_dict)
    
    def test_always_serialize_id_as_int(self):
        task = AgiloTicket(self.env, t_type=Type.TASK)
        task.insert()
        
        task_id = task.id
        task = AgiloTicket(self.env, str(task_id))
        self.assert_equals(task_id, task.as_dict()['id'])


class TestTicketModelManager(AgiloTestCase):
    """Tests AgiloTicket ModelManager, in particular the select method"""
    def setUp(self):
        self.super()
        self.manager = AgiloTicketModelManager(self.env)
        
    def test_create_ticket(self):
        """Tests the creation of a ticket using the ModelManager"""
        t = self.manager.create(summary="This is a ticket")
        self.assert_true(t.exists, "Ticket not existing...")
        self.assert_equals("This is a ticket", t[Key.SUMMARY])
        # Create without saving
        t2 = self.manager.create(summary="Not saved", save=False)
        self.assert_false(t2.exists, "The ticket has been saved!")
        self.assert_equals("Not saved", t2[Key.SUMMARY])
        # Now add something and change the summary
        t2[Key.DESCRIPTION] = "changed"
        t2[Key.SUMMARY] = "Now saved"
        self.manager.save(t2)
        self.assert_true(t2.exists)
        self.assert_equals("changed", t2[Key.DESCRIPTION])
        self.assert_equals("Now saved", t2[Key.SUMMARY])
    
    def test_ticket_caching(self):
        """Tests the ticket caching"""
        t1 = self.manager.create(summary="Ticket #1", 
                                 t_type=Type.USER_STORY)
        t1_dupe = self.manager.get(tkt_id=t1.id)
        self.assert_equals(t1, t1_dupe)
        
    def test_select_tickets(self):
        """Tests the select method to get tickets"""
        milestone = self.teh.create_milestone('Test')
        sprint = self.teh.create_sprint('Test', milestone=milestone)
        t1 = self.manager.create(summary="Ticket #1", 
                                 t_type=Type.USER_STORY,
                                 sprint=sprint.name)
        t2 = self.manager.create(summary="Ticket #2",
                                 t_type=Type.TASK)
        # Now the plan select should return both tickets
        tickets = self.manager.select()
        self.assert_true(t1 in tickets, "T1 is not in tickets!?")
        self.assert_true(t2 in tickets, "T2 is not in tickets!?")
        # Now selects all tickets planned for sprint Test
        self.assert_equals(sprint.name, t1[Key.SPRINT])
        tickets = self.manager.select(criteria={Key.SPRINT: 'Test'})
        self.assert_true(t1 in tickets, "T1 is not in ticket!?")
        self.assert_false(t2 in tickets, "T2 is in tickets and should not?!")
        # Now selects all tickets planned for milestone Test
        self.assert_equals('Test', t1[Key.MILESTONE])
        tickets = self.manager.select(criteria={Key.MILESTONE: 'Test'})
        self.assert_true(t1 in tickets, "T1 is not in tickets!?")
        self.assert_false(t2 in tickets, "T2 is in tickets and should not?!")
        # Now tests the select with a limit to 1
        tickets = self.manager.select(limit=1)
        self.assert_equals(1, len(tickets))
        tickets = self.manager.select(limit=2)
        self.assert_equals(2, len(tickets))
        # Now select all the tickets that have been created before now
        tickets = self.manager.select(criteria={'changetime': '<=%s' % \
                                                t1.time_created})
        self.assert_equals(2, len(tickets))
        # Now try out the order by
        tickets = self.manager.select(order_by=['-sprint'])
        self.assert_equals(tickets[0], t1)
        self.assert_equals(tickets[1], t2)

    def test_criteria_not_split_if_no_type(self):
        """Tests the splitting of the criteria in the selct query when
        containing the paramater ticket type"""
        criteria = {'summary': 'test', Key.REMAINING_TIME: '2',
                    'id': 'not in (1, 2, 3)'}
        self.assert_none(self.manager._split_ticket_type(criteria))

    def test_criteria_split_if_type(self):
        """Tests the splitting of the criteria in the selct query when
        containing the paramater ticket type"""
        criteria = {'summary': 'test', Key.REMAINING_TIME: '2',
                    'type': "in ('story', 'task')"}
        res = self.manager._split_ticket_type(criteria)
        self.assert_not_none(res)
        self.assert_equals('story', res[0].value)
        self.assert_equals('=', res[0].operator)
        self.assert_equals(('task', 'story'), res[1].value)
        self.assert_equals('in', res[1].operator)


if __name__ == '__main__':
    from agilo.test.testfinder import run_all_tests
    run_all_tests(__file__)