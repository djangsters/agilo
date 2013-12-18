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
#     - Andrea Tomasini
#     - Felix Schwarz

import re

from trac.resource import ResourceNotFound

from agilo.test import AgiloTestCase
from agilo.ticket.links import LinkOption
from agilo.ticket.links.model import LinksConfiguration
from agilo.ticket.model import AgiloTicket
from agilo.utils import Key, Type
from agilo.utils.config import AgiloConfig


class TestOperationOnLinksInAgiloTicket(AgiloTestCase):
    
    def _reset_links_configuration(self):
        # Reinitialize the link configuration
        lc = LinksConfiguration(self.teh.env)
        lc._initialized = False
        lc.initialize()
    
    def setUp(self):
        self.super()
        config = AgiloConfig(self.env)
        # Adding properties for multiple calculated property testing
        # The problem is that at this point the linkConfiguration as been
        # already initialized so we will need to do it again manually
        config.change_option('actual_time', 'text', 
                             section=AgiloConfig.TICKET_CUSTOM)
        config.change_option(Type.TASK, 
                             'sprint, remaining_time, actual_time, estimated_time, owner, drp_resources',
                             section=AgiloConfig.AGILO_TYPES)
        config.change_option('story.calculate', 
                             'total_remaining_time=sum:get_outgoing.remaining_time, total_actual_time=sum:get_outgoing.actual_time',
                             section=AgiloConfig.AGILO_LINKS)
        config.save()
        
        self.assert_true(config.is_agilo_enabled)
        self.assert_true('actual_time' in config.get_list(Type.TASK, section=AgiloConfig.AGILO_TYPES))
        self.assert_true('actual_time' in config.get_fields_for_type().get(Type.TASK))
        self.assert_equals(config.get('story.calculate', section=AgiloConfig.AGILO_LINKS), 
                         'total_remaining_time=sum:get_outgoing.remaining_time, total_actual_time=sum:get_outgoing.actual_time')
        self._reset_links_configuration()
        # Creates tickets
        self.t1 = self.teh.create_ticket(Type.USER_STORY)
        self.t2 = self.teh.create_ticket(Type.TASK, 
                                         props={Key.REMAINING_TIME: u'20', 
                                                Key.RESOURCES: u'Tim, Tom'})
        self.t3 = self.teh.create_ticket(Type.TASK, 
                                         props={Key.REMAINING_TIME: u'10', 
                                                Key.RESOURCES: u'Tim, Tom'})
        # Now actual_time should be a valid field for Task...
        self.assert_not_none(self.t2.get_field('actual_time'))
        
    def testCreateAndDeleteLink(self):
        """Creates a link between t1 and t2 and deletes it afterwards"""
        #Creates the link
        self.assert_false(self.t1.is_linked_to(self.t2))
        self.assert_false(self.t2.is_linked_from(self.t2))
        self.assert_true(self.t1.link_to(self.t2))
        self.assert_true(self.t2.is_linked_from(self.t1))
        self.assert_true(self.t1.is_linked_to(self.t2))
        #Link again and check if it return false
        self.assert_false(self.t1.link_to(self.t2))
        self.assert_true(self.t2.is_linked_from(self.t1))
        self.assert_true(self.t1.is_linked_to(self.t2))
        # Delete it
        self.assert_true(self.t1.del_link_to(self.t2))
        # Check if they are still linked
        self.assert_false(self.t2.is_linked_from(self.t1))
        self.assert_false(self.t1.is_linked_to(self.t2))
        
    def testCalculatedProperties(self):
        """Test the calculated property for remaining_time on the aggregated tickets"""
        # Creates first a third AgiloTicket
        self.assert_true(self.t1.link_to(self.t3))
        self.assert_true(self.t3.is_linked_from(self.t1))
        self.assert_true(self.t1.is_linked_to(self.t3))
        # Creates the link also with self.t2
        self.assert_true(self.t1.link_to(self.t2))
        self.assert_true(self.t2.is_linked_from(self.t1))
        self.assert_true(self.t1.is_linked_to(self.t2))
        # Now get the remaining_time that is configured as a calculated property
        expected = int(self.t2[Key.REMAINING_TIME]) + int(self.t3[Key.REMAINING_TIME])
        self.assert_equals(expected, self.t1['total_remaining_time'])
        # Change one of the ticket value and ask again for the property
        self.t2[Key.REMAINING_TIME] = u'10'
        self.t2.save_changes('The Tester', 'Changed remaining time to 10...')
        # Now get the remaining_time that is configured as a calculated property
        expected = int(self.t2[Key.REMAINING_TIME]) + int(self.t3[Key.REMAINING_TIME])
        self.assert_equals(expected, self.t1['total_remaining_time'])
    
    def testMultipleCalculatedProperties(self):
        """Tests multiple calculated properties on the same link-type"""
        # Creates first a third AgiloTicket
        self.assert_true(self.t1.link_to(self.t3))
        self.assert_true(self.t3.is_linked_from(self.t1))
        self.assert_true(self.t1.is_linked_to(self.t3))
        # Creates the link also with self.t2
        self.assert_true(self.t1.link_to(self.t2))
        self.assert_true(self.t2.is_linked_from(self.t1))
        self.assert_true(self.t1.is_linked_to(self.t2))
        # Sets the actual_time as a property for t2 and t3
        self.assert_true('actual_time' in self.t2.fields_for_type)
        self.assertNotEquals(None, self.t2.get_field('actual_time'))
        self.t2['actual_time'] = u'8'
        self.t2.save_changes('The Tester', 'Changed actual time to 8...')
        self.t3['actual_time'] = u'4'
        self.t3.save_changes('The Tester', 'Changed actual time to 4...')
        self.assert_equals(self.t1['total_remaining_time'], 
                         int(self.t2[Key.REMAINING_TIME]) + int(self.t3[Key.REMAINING_TIME]))
        expected_actual_time = int(self.t2['actual_time']) + int(self.t3['actual_time'])
        self.assert_equals(expected_actual_time, self.t1['total_actual_time'])
    
    def testLinkOnDeletedTicket(self):
        """Tests the deletion of a link after a deleted ticket"""
        # Creates the link also with self.t2
        self.assert_true(self.t1.link_to(self.t2))
        self.assert_true(self.t2.is_linked_from(self.t1))
        self.assert_true(self.t1.is_linked_to(self.t2))
        # Now delete the ticket and check propagation
        self.t1.delete()
        self.assert_false(self.t2.is_linked_from(self.t1))

    def _add_cascading_delete_configuration(self, delete_pairs):
        """Adds cascading delete option to the environment configuration"""
        #delete_pairs has to be a comma separated list of type pairs
        env = self.teh.get_env()
        config_section = 'agilo-links'
        config_key = LinkOption.DELETE
        env.config.set(config_section, config_key, delete_pairs)
        env.config.save()

    def test_ticket_is_deleted_when_linked_to_ticket_is_deleted(self):
        self._add_cascading_delete_configuration('story-task')
        self.assert_true(self.t1.link_to(self.t2))
        self.assert_true(self.t1.is_linked_to(self.t2))
        self.teh.delete_ticket(self.t1.id)
        self.assert_raises(ResourceNotFound, self.teh.load_ticket, self.t1)
        self.assert_raises(ResourceNotFound, self.teh.load_ticket, self.t2)

    def test_ticket_is_not_deleted_when_linked_from_ticket_is_deleted(self):
        self._add_cascading_delete_configuration('story-task')
        self.assert_true(self.t1.link_to(self.t2))
        self.assert_true(self.t1.is_linked_to(self.t2))
        self.teh.delete_ticket(self.t2.id)
        self.assert_raises(ResourceNotFound, self.teh.load_ticket, self.t2)
        self.assert_equals(self.t1.id, self.teh.load_ticket(ticket=self.t1).id)
        
    def testIsLinked(self):
        """Tests the linking control, via all possible methods"""
        self.assert_false(self.t1.is_linked_to(self.t2))
        self.assert_false(self.t2.is_linked_from(self.t1))
        # Create the link
        self.assert_true(self.t1.link_to(self.t2))
        self.assert_true(self.t1.is_linked_to(self.t2))
        self.assert_true(self.t2.is_linked_from(self.t1))
        # Delete link and test if is not linked anymore
        self.assert_true(self.t1.del_link_to(self.t2))
        self.assert_false(self.t1.is_linked_to(self.t2))
        self.assert_false(self.t2.is_linked_from(self.t1))
        
    def testBuildDict(self):
        """Test the build dictionary with the list of links"""
        self.assert_equals(len(self.t1.get_outgoing()), len(self.t1.get_outgoing_dict()))
        self.assert_equals(len(self.t2.get_outgoing()), len(self.t2.get_outgoing_dict()))
        self.assert_equals(len(self.t1.get_incoming()), len(self.t1.get_incoming_dict()))
        self.assert_equals(len(self.t2.get_incoming()), len(self.t2.get_incoming_dict()))
        
    def testCreateNewLinkedTicket(self):
        """Test the creation of a new linked ticket"""
        # Get db and handle the transaction
        db = self.teh.get_env().get_db_cnx()
        new = AgiloTicket(self.teh.get_env())
        new[Key.SUMMARY] = 'This is a new ticket, never saved'
        new[Key.DESCRIPTION] = 'This will be created and linked in one shot ;-)'
        new[Key.TYPE] = Type.TASK
        self.assert_true(new.link_from(self.t1, db))
        self.assert_not_none(new.insert(db=db))
        # Now commit the link and the insert
        db.commit()
        # Check that has been linked
        self.assert_true(new.is_linked_from(self.t1))
        self.assert_true(self.t1.is_linked_to(new))
        
        # Now test the autoinsert and link of the agilo ticket
        new2 = AgiloTicket(self.teh.get_env(), t_type=Type.TASK)
        new2[Key.SUMMARY] = "This is a linked new ticket"
        new2[Key.DESCRIPTION] = "description"
        self.assert_true(self.t1.link_to(new2))
        self.assert_true(new2.is_linked_from(self.t1))
        self.assert_true(self.t1.is_linked_to(new2))
        
        # Now test the link failure
        self.assert_false(new2.link_from(self.t1))
    
    def _build_requirement(self, business_value=None):
        props=None
        if business_value is not None:
            props = {Key.BUSINESS_VALUE: str(business_value)}
        requirement = self.teh.create_ticket(Type.REQUIREMENT, props=props)
        return requirement
    
    def _build_requirement_with_two_stories(self, business_value=None, 
                                        points_story1=None, points_story2=None):
        requirement = self._build_requirement(business_value)
        props = {Key.STORY_PRIORITY: 'Mandatory'} 
        if points_story1 is not None:
            props[Key.STORY_POINTS] = str(points_story1)
        story1 = self.teh.create_ticket(Type.USER_STORY, props=props)
        if points_story2 is not None:
            props[Key.STORY_POINTS] = str(points_story2)
        story2 = self.teh.create_ticket(Type.USER_STORY, props=props)
        self.assert_true(requirement.link_to(story1))
        self.assert_true(requirement.link_to(story2))
        return requirement, story1, story2
    
    def test_calculation_of_total_story_points(self):
        requirement = self._build_requirement_with_two_stories(500, 16, 4)[0]
        self.assert_equals(20, requirement["total_story_points"])
        self.assert_equals(500, int(requirement[Key.BUSINESS_VALUE]))
        self.assert_true(requirement.exists)
        self.assertNotEqual(0, requirement.id)
        all_calculated = LinksConfiguration(self.teh.get_env()).get_calculated()
        self.assert_true('total_story_points' in all_calculated)
        self.assert_true('total_remaining_time' in all_calculated)
        self.assert_true('total_actual_time' in all_calculated)
        self.assert_true(Key.ROIF in all_calculated)
        self.assert_true(Key.ROIF in requirement.get_calculated_fields_names())
        self.assert_equals(500, int(requirement[Key.BUSINESS_VALUE]))
        self.assert_equals(25, int(requirement[Key.ROIF]))
    
    def test_total_story_point_calculation_without_stories(self):
        requirement = self._build_requirement_with_two_stories(500)[0]
        self.assert_true("total_story_points" in requirement.get_calculated_fields_names())
        self.assert_none(requirement['total_story_points'])
    
    def test_calculation_of_story_points_as_float(self):
        requirement = self._build_requirement_with_two_stories(500, 2.5, 2.5)[0]
        self.assert_equals(5, requirement["total_story_points"])
    
    def test_roif_calculation_without_stories(self):
        requirement = self._build_requirement(500)
        self.assert_true(Key.ROIF in requirement.get_calculated_fields_names())
        self.assert_none(requirement[Key.ROIF])
    
    def test_roif_calculation_with_zero_story_points(self):
        requirement = self._build_requirement_with_two_stories(500, 0, 0)[0]
        self.assert_true(Key.ROIF in requirement.get_calculated_fields_names())
        self.assert_none(requirement[Key.ROIF])
    
    def test_roif_calculation_only_mandatory_stories(self):
        requirement, story1, story2 = self._build_requirement_with_two_stories(500, 40, 10)
        story1[Key.STORY_PRIORITY] = 'Mandatory'
        story2[Key.STORY_PRIORITY] = 'Exciter'
        self.assert_true(Key.ROIF in requirement.get_calculated_fields_names())
        self.assert_equals(float("12.5"), requirement[Key.ROIF])
    
    def _change_roif_definition(self, acceptable_user_story_priorities):
        env = self.teh.get_env()
        config = env.config
        config_section = 'agilo-links'
        config_key = '%s.%s' % (Type.REQUIREMENT, LinkOption.CALCULATE)
        calc_option = config.get(config_section, config_key)
        calc_option_without_roif_definition = re.sub(r'\s*,?\s*roif=[^,]+(,|$)', '\1', calc_option)
        
        conditionstring = ":".join(acceptable_user_story_priorities)
        new_sum_definition = 'new_roif_sum=sum:get_outgoing.%s|%s=%s' % (Key.STORY_POINTS, Key.STORY_PRIORITY, conditionstring)
        roif_definition = 'roif=div:%s;new_roif_sum' % Key.BUSINESS_VALUE
        new_calc_option = '%s,%s,%s' % (new_sum_definition, roif_definition, calc_option_without_roif_definition)
        
        config.set(config_section, config_key, new_calc_option)
        config.save()
        self._reset_links_configuration()
    
    def test_roif_calculation_no_exciter_stories(self):
        self._change_roif_definition(['Mandatory', 'Linear'])
        requirement, story1, story2 = self._build_requirement_with_two_stories(500, 40, 10)
        story1[Key.STORY_PRIORITY] = 'Exciter'
        story2[Key.STORY_PRIORITY] = 'Linear'
        self.assert_true(Key.ROIF in requirement.get_calculated_fields_names())
        self.assert_equals(50, requirement[Key.ROIF])
    
    def test_roif_calculation_all_stories(self):
        self._change_roif_definition(['Mandatory', 'Linear', 'Exciter'])
        requirement, story1, story2 = self._build_requirement_with_two_stories(500, 40, 10)
        story1[Key.STORY_PRIORITY] = 'Mandatory'
        story2[Key.STORY_PRIORITY] = 'Exciter'
        self.assert_true(Key.ROIF in requirement.get_calculated_fields_names())
        self.assert_equals(10, requirement[Key.ROIF])
    
    def test_missing_agilo_links_allow(self):
        """Tests robustness of config in case the 'allow' parameter is missing"""
        env = self.teh.get_env()
        env.config.remove('agilo-links', 'allow')
        lc = LinksConfiguration(env)
        # Force initialization
        lc._initialized = False
        lc.initialize()

