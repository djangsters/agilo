# -*- encoding: utf-8 -*-
#   Copyright 2011 Agilo Software GmbH All rights reserved
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use self file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#   Author: 
#       - Stefano Rago <stefano.rago__at__agilosoftware.com>

from agilo.utils.compat import json

from trac.tests.functional import tc

from agilo.utils import Type
from agilo.test import Usernames
from agilo.test.functional import AgiloFunctionalTestCase
from agilo.scrum.backlog.backlog_config import BacklogConfiguration
from agilo.scrum.backlog.controller import BacklogController

class BacklogRendererCanRenderTickets(AgiloFunctionalTestCase):
    testtype = 'twill'
    
    def setUp(self):
        self.super()
        self.tester.login_as(Usernames.admin)
        self.story1_id = self.tester.create_new_agilo_userstory("summary for story 1")
        self.story2_id = self.tester.create_new_agilo_userstory("summary for story 2")
        self.requirement1_id = self.tester.create_new_agilo_requirement("summary for requirement 1")
        self.story3_id = self.tester.create_referenced_ticket(self.requirement1_id,
                                                              Type.USER_STORY,
                                                              "summary for story 3")
        
    def runTest(self):
        self.tester.go_to_product_backlog()
        tc.tidy_ok()
        tc.find("id=\"ticketID-%s\"" % self.story1_id)
        tc.find("id=\"ticketID-%s\"" % self.story2_id)
        tc.find("id=\"ticketID-%s\"" % self.requirement1_id)
        tc.find("id=\"ticketID-%s\"" % self.story3_id)
    

class BacklogRendererHidesPlannedItems(AgiloFunctionalTestCase):
    testtype = 'twill'
    
    def setUp(self):
        self.super()
        self.tester.login_as(Usernames.admin)
        self.ids = self.tester.create_sprint_with_small_backlog()
        
    def runTest(self):
        story_id = self.ids[1]
        self.tester.go_to_product_backlog()
        tc.notfind("id=\"ticketID-%s\"" % story_id)
        

class BacklogRendererShowsPlannedItems(AgiloFunctionalTestCase):
    testtype = 'twill'
    
    def setUp(self):
        self.super()
        
        global_backlog_config = BacklogConfiguration(self.env, name='Product Backlog')
        global_backlog_config.ticket_types = [Type.REQUIREMENT, Type.USER_STORY]
        global_backlog_config.include_planned_items = True
        global_backlog_config.save()
        
        self.tester.login_as(Usernames.admin)
        self.ids = self.tester.create_sprint_with_small_backlog()
        
    def runTest(self):
        story_id = self.ids[1]
        self.tester.go_to_product_backlog()
        tc.find("id=\"ticketID-%s\"" % story_id)

class BacklogRendererCanHandleMultiLinkedTickets(AgiloFunctionalTestCase):
    testtype = 'twill'
    
    def setUp(self):
        self.super()
        self.tester.login_as(Usernames.admin)
        self.requirement1_id = self.tester.create_new_agilo_requirement("summary for requirement 1")
        self.requirement2_id = self.tester.create_new_agilo_requirement("summary for requirement 2")
        self.story1_id = self.tester.create_referenced_ticket(self.requirement1_id,
                                                              Type.USER_STORY,
                                                              "story with multiple parents")
        self.tester.link_tickets(self.requirement2_id, self.story1_id)
        
    def runTest(self):
        self.tester.go_to_product_backlog()
        tc.find("id=\"ticketID-%s\"" % self.story1_id)
        tc.find("id=\"ticketID-%s-%s\"" % (self.story1_id, self.requirement2_id))
        tc.find("multi-linked-item.*multi-linked-item")
        
class BacklogRendererHonorsTicketPriority(AgiloFunctionalTestCase):
    testtype = 'twill'
    
    def setUp(self):
        self.super()
        self.tester.login_as(Usernames.admin)
        self.controller = BacklogController(self.env)
        self.backlog = self.teh.create_backlog('Product Backlog', num_of_items=20)

    def runTest(self):
        first_item = self.backlog[0]
        second_item = self.backlog[1]
        self.tester.go_to_product_backlog()
        tc.find("id=\"ticketID-%s\".*id=\"ticketID-%s\"" % (first_item.ticket.id, second_item.ticket.id))
        
        move_cmd = BacklogController.MoveBacklogItemCommand(self.env,
                                                            name='Product Backlog',
                                                            ticket=first_item,
                                                            to_pos=4)
        self.controller.process_command(move_cmd)
        self.tester.go_to_product_backlog()
        tc.find("id=\"ticketID-%s\".*id=\"ticketID-%s\"" % (second_item.ticket.id, first_item.ticket.id))

class BacklogRendererIncludesTotalsRow(AgiloFunctionalTestCase):
    testtype = 'twill'
    
    def setUp(self):
        self.super()
        self.tester.login_as(Usernames.admin)
        self.controller = BacklogController(self.env)
        self.backlog = self.teh.create_backlog('Product Backlog', num_of_items=20)

    def runTest(self):
        self.tester.go_to_product_backlog()
        tc.find("id=\"ticketID--2\"")

class BacklogRendererIncludesUnreferencedTicketsRow(AgiloFunctionalTestCase):
    testtype = 'twill'
    
    def setUp(self):
        self.super()
        self.tester.login_as(Usernames.admin)
        global_backlog_config = BacklogConfiguration(self.env, name='Product Backlog')
        global_backlog_config.ticket_types = [Type.REQUIREMENT, Type.USER_STORY, Type.TASK]
        global_backlog_config.save()

    def runTest(self):
        self.tester.create_new_agilo_ticket(Type.TASK, "task without parents")
        self.tester.go_to_product_backlog()
        tc.find("id=\"ticketID--1\".*unreferenced")

class BacklogRendererIncludesAllFieldsAsMetadata(AgiloFunctionalTestCase):
    testtype = 'twill'
    
    def setUp(self):
        self.super()
        self.tester.login_as(Usernames.admin)
        self.story_id = self.tester.create_new_agilo_ticket(Type.USER_STORY, "Story summary")
        self.story = self.teh.load_ticket(t_id=self.story_id)

    def runTest(self):
        self.tester.go_to_product_backlog()
        story_as_dict = self.story.as_dict()
        from agilo.ticket import AgiloTicketSystem
        if AgiloTicketSystem.is_trac_1_0():
            from trac.util.datefmt import to_utimestamp
            story_as_dict.update({'view_time': str(to_utimestamp(self.story.time_changed))})
        if story_as_dict.has_key('description'):
            del story_as_dict['description']
        data = json.dumps(story_as_dict)
        import trac.util
        escaped_data = trac.util.escape(data)
        page = tc.get_browser().get_html()
        self.assert_(str(escaped_data) in page, "Metadata error")
        
class BacklogRendererIncludesHiddenTicketsInFieldsCalculation(AgiloFunctionalTestCase):
    testtype = 'twill'
    
    def setUp(self):
        self.super()
        self.tester.login_as(Usernames.admin)

        global_backlog_config = BacklogConfiguration(self.env, name='Product Backlog')
        global_backlog_config.backlog_columns = ['total_remaining_time']
        global_backlog_config.save()
        self.assertTrue('task' not in global_backlog_config.ticket_types)
        
        self.expected_remaining_time = 3
        self.story_id = self.tester.create_new_agilo_ticket(Type.USER_STORY, "Story summary")
        self.task_id = self.tester.create_referenced_ticket(self.story_id, Type.TASK, 'Task summary', remaining_time=self.expected_remaining_time)
        self.task = self.teh.load_ticket(t_id=self.task_id)

    def runTest(self):
        self.tester.go_to_product_backlog()
        tc.find("id=\"ticketID-%s\"" % self.story_id)
        tc.notfind("id=\"ticketID-%s\"" % self.task_id)
        self.assertEqual(self.task['remaining_time'], str(self.expected_remaining_time))
        tc.find("<span class=\"total_remaining_time numeric\"[^>]*>3</span>")
        
    
if __name__ == '__main__':
    from agilo.test import run_all_tests
    run_all_tests(__file__)

