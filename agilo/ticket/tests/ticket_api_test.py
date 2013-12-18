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
#   
#   Author: 
#       - Andrea Tomasini <andrea.tomasini__at__agile42.com>


from agilo.utils import Type, Key
from agilo.utils.config import AgiloConfig
from agilo.test import AgiloTestCase
from agilo.ticket.api import FieldsWrapper, AgiloTicketSystem


class TestFieldsWrapper(AgiloTestCase):
    
    def test_safe_custom_fields(self):
        """Tests that the defined custom fields are safe"""
        ticket_custom = \
            AgiloConfig(self.env).get_section(AgiloConfig.TICKET_CUSTOM)
        custom_fields = ticket_custom.get_options_matching_re('^[^.]+$')
        tfw = FieldsWrapper(self.env, 
                            AgiloTicketSystem(self.env).get_ticket_fields(), 
                            Type.TASK)
        for f in tfw:
            if f[Key.NAME] in custom_fields:
                self.assert_true(f[Key.CUSTOM], 
                                "%s should be custom!!!" % f[Key.NAME])
    
    def test_fields_for_task(self):
        """Tests how the FieldsWrapper respond with a task type"""
        ticket_system = AgiloTicketSystem(self.env)
        tfw = FieldsWrapper(self.env, 
                            ticket_system.get_ticket_fields(), 
                            Type.TASK)
        
        expected_fields_for_task = AgiloConfig(self.env).TYPES.get(Type.TASK)
        # Try to check the keys
        field_wrapper_names = map(lambda field: field[Key.NAME], tfw)
        
        # it is added by the ticket system to store sprint
        # scope synchronous with milestone
        field_wrapper_names.remove(Key.MILESTONE)
        expected_fields_for_task.remove('id')
        if not ticket_system.is_trac_012():
            # in Trac 0.11, time fields are magic
            field_wrapper_names.append('changetime')
            field_wrapper_names.append('time')
        self.assert_equals(sorted(expected_fields_for_task), sorted(field_wrapper_names))


class TestTicketSystem(AgiloTestCase):
    """Tests the AgiloTicketSystem directly, making sure it is consistent with types"""
    
    def test_a_task_is_a_task(self):
        """Creates a task and make sure only the Task fields are loaded"""
        task = self.teh.create_ticket(Type.TASK, props={Key.REMAINING_TIME: '12'})
        fields_for_task = AgiloConfig(self.env).TYPES.get(Type.TASK)
        
        for f in task.fields:
            if not f[Key.NAME] == Key.MILESTONE:
                # Milestone is there if there is Sprint
                self.assert_true(f[Key.NAME] in fields_for_task,
                                "Field %s not in task fields..." % \
                                f[Key.NAME])
        
    def test_type_change(self):
        """Test that the ticket reacts to type changes"""
        task = self.teh.create_ticket(Type.TASK, props={Key.REMAINING_TIME: '12'})
        fields_for_type = AgiloConfig(self.env).TYPES
        
        for f in task.fields:
            if not f[Key.NAME] == Key.MILESTONE:
                # Milestone is there if there is Sprint
                self.assert_true(f[Key.NAME] in fields_for_type[Type.TASK],
                                "Field %s not in task fields..." % f[Key.NAME])
        
        # change the task to a story
        task[Key.TYPE] = Type.USER_STORY
        
        for f in task.fields:
            if not f[Key.NAME] == Key.MILESTONE:
                # Milestone is there if there is Sprint
                self.assert_true(f[Key.NAME] in fields_for_type[Type.USER_STORY],
                                "Field %s not in user story fields..." % f[Key.NAME])
    
    def test_agilo_properties(self):
        """Tests the TicketSystem for the agilo properties"""
        ats = AgiloTicketSystem(self.env)
        calc, allowed, sorting, showing = ats.get_agilo_properties(Type.TASK)
        
        # Tests are a bit hard but necessary, every time someone changes the 
        # default properties this will fail, needs to be updated
        self.assert_equals({}, calc, 
                         "Found calculated properties for task: %s" % calc)
        self.assert_equals({}, allowed,
                         "Found allowed link properties for task: %s" % allowed)
        self.assert_equals({}, sorting,
                         "Found sorting properties for task: %s" % sorting)
        self.assert_equals({}, showing,
                         "Found showing properties for task: %s" % showing)
        
        # Now tests a story
        calc, allowed, sorting, showing = ats.get_agilo_properties(Type.USER_STORY)
        
        # Tests are a bit hard but necessary, every time someone changes the 
        # default properties this will fail, needs to be updated
        self.assert_true(Key.TOTAL_REMAINING_TIME in calc and Key.ESTIMATED_REMAINING_TIME in calc, 
                         "Wrong calculated properties for story: %s" % calc)
        self.assert_true(Type.TASK in allowed,
                         "Wrong allowed link properties for story: %s" % allowed)
        self.assert_true(Type.TASK in sorting,
                         "Wrong sorting properties for story: %s" % sorting)
        self.assert_true(Type.TASK in showing,
                         "Wrong showing properties for story: %s" % showing)
        
    def test_non_existent_type(self):
        """Tests that if a type is not defined as agilo type will get all properties"""
        nonex = self.teh.create_ticket('nonex')
        all_fields = AgiloTicketSystem(self.env).get_ticket_fields()
        
        for f1, f2 in zip(nonex.fields, all_fields):
            self.assert_equals(f1, f2, "Error: %s != %s" % (f1, f2))
    
    def test_can_map_alias_to_trac_type(self):
        ticket_system = AgiloTicketSystem(self.env)
        self.assert_equals(Type.TASK, ticket_system.normalize_type(Type.TASK))
        self.assert_equals(Type.TASK, ticket_system.normalize_type('Task')) #Task alias
    
    def test_just_return_input_if_no_alias_was_found(self):
        ticket_system = AgiloTicketSystem(self.env)
        self.assert_none(ticket_system.normalize_type('nonexisting_type'))
    
