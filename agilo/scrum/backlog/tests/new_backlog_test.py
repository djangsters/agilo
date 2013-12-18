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

from agilo.utils import Key, Type
from agilo.test.testcase import AgiloTestCase
from agilo.scrum.backlog.model import Backlog, BacklogModelManager
from agilo.ticket.model import AgiloTicket


class NewBacklogTest(AgiloTestCase):
    """Tests the new Backlog model"""
    
    def setUp(self):
        self.super()
        self.r1 = self.teh.create_ticket(Type.REQUIREMENT)
        self.r2 = self.teh.create_ticket(Type.REQUIREMENT)
        self.us1 = self.teh.create_ticket(Type.USER_STORY)
        self.us2 = self.teh.create_ticket(Type.USER_STORY)
        self.us3 = self.teh.create_ticket(Type.USER_STORY)
        self.t1 = self.teh.create_ticket(Type.TASK)
        self.t2 = self.teh.create_ticket(Type.TASK)
        self.r1.link_to(self.us1)
        self.r2.link_to(self.us2)
        self.r2.link_to(self.us3)
        self.tickets = [self.r1, self.r2, 
                        self.us1, self.us2, self.us3,
                        self.t1, self.t2]
        # The tickets should have no milestone nor story set :-)
        for t in self.tickets:
            self.assert_equals('', t[Key.MILESTONE])
            
        # Now create a Backlog item for each and reload it, we need a backlog
        self.pb = Backlog(self.env, Key.PRODUCT_BACKLOG)
        self.assert_not_none(self.pb, "Product Backlog not loaded...")
        self.assert_not_equals(0, len(self.pb.config.ticket_types))
        self.assert_equals(Key.PRODUCT_BACKLOG, self.pb.name, 
                           "Backlog name not matching... %s" % self.pb.name)
        self.assert_equals(5, len(self.pb))
        self.milestone = self.teh.create_milestone("BacklogMilestone")
        self.sprint = self.teh.create_sprint("BacklogTestSprint",
                                             milestone="BacklogMilestone")
        self.sb = Backlog(self.env, Key.SPRINT_BACKLOG, scope=self.sprint.name)
        self.assert_equals(0, len(self.sb))
        self.assert_not_none(self.sb, "Sprint Backlog not loaded...")
        self.assert_not_equals(0, len(self.sb.config.ticket_types))
        # a BacklogItemModelManager
        self.bimm = BacklogModelManager.BacklogItemModelManager(self.env)
        
    def test_can_create_backlog_items(self):
        # Now let's create Backlog items for all of the ticket above
        backlog_items = []
        for t in self.tickets:
            backlog_items.append(self.bimm.create_or_get(self.env, 
                                                         backlog_name=self.pb.name,
                                                         ticket=t))
        for bi, t in zip(backlog_items, self.tickets):
            self.assert_true(isinstance(bi.ticket, AgiloTicket), 
                             "Got %s instead" % type(bi.ticket))
            self.assert_not_none(bi, "BacklogItem not created")
            self.assert_equals(bi.ticket[Key.SUMMARY], t[Key.SUMMARY])
            self.assert_equals(bi.ticket[Key.TYPE], t[Key.TYPE])
    
    def test_can_load_backlog_items_from_db(self):
        backlog_items = []
        for ticket in self.tickets:
            item = self.bimm.create_or_get(self.env, backlog_name=self.pb.name, ticket=ticket)
            backlog_items.append(item)
        loaded_items = self.bimm.select()
        self.assert_not_none(loaded_items, "No backlog items loaded_items...")
        for bi in loaded_items:
            self.assert_contains(bi, backlog_items)
    
    def test_product_backlog_loads_items(self):
        """Tests that the Product Backlog is loading all the Backlog Items"""
        # Now there is not Backlog Item created, but because the ProductBacklog
        # is a global backlog you expect it to load all the ticket with no
        # explicitly set scope
        pb_tickets = [t for t in self.tickets if \
                      t.get_type() in self.pb.config.ticket_types]
        self.assert_equals(len(pb_tickets), len(self.pb))
        for backlog_item in self.pb:
            self.assert_contains(backlog_item.ticket, pb_tickets)
    
    def test_product_backlog_is_not_loading_planned_items(self):
        # Now let's create a sprint and plan one story for that sprint, it
        # shouldn't appear anymore in the Product Backlog
        pb_tickets = [t for t in self.tickets if \
                      t.get_type() in self.pb.config.ticket_types]
        self.us1[Key.SPRINT] = self.sprint.name
        self.us1.save_changes('tester', 'Planned for sprint...')
        self.assert_equals(len(pb_tickets) - 1, len(self.pb))
        for bi in self.pb:
            self.assert_not_equals(self.us1, bi.ticket)
    
    def test_sprint_backlog_loads_stories_planned(self):
        """Tests that the Sprint Backlog loads the stories planned for the
        sprint as well as the parent tickets"""
        # check that planned stories are appearing and not planned stories are
        # not
        self.us1[Key.SPRINT] = self.sprint.name
        self.us1.save_changes('tester', 'Planned for sprint...')
        self.us2[Key.SPRINT] = self.sprint.name
        self.us2.save_changes('tester', 'Planned for sprint...')
        # the Sprint Backlog should contain the 2 stories and the 2
        # parent requirements
        self.assert_equals(2 + 2, len(self.sb))
        for bi in self.sb:
            self.assert_not_equals(self.us3, bi.ticket)
        backlog_tickets = [bi.ticket for bi in self.sb]
        self.assert_contains(self.us1, backlog_tickets)
        self.assert_contains(self.us2, backlog_tickets)
    
    def test_product_backlog_only_loads_allowed_items(self):
        for item in self.pb:
            self.assert_contains(item.ticket.get_type(), self.pb.config.ticket_types)
    
    def test_sprint_backlog_only_loads_allowed_items(self):
        for item in self.sb:
            self.assert_contains(item.ticket.get_type(), self.sb.config.ticket_types)
    
    def test_sprint_backlog_loads_items_planned_and_parents(self):
        """Tests that the Sprint Backlog loads all the items explicitly planned
        as well as their parents"""
        self.assert_equals(0, len(self.sb))
        self.us1[Key.SPRINT] = self.sprint.name
        self.us1.save_changes('tester', 'Planned for sprint...')
        # now create a task a link it to us2
        task = self.teh.create_task()
        self.us2.link_to(task)
        # now we plan the task for the sprint, this should load also us2 being
        # the task parent, as well as r2 being the parent of the us2, beside us1
        # and its own parent requirement, being r1
        task[Key.SPRINT] = self.sprint.name
        task.save_changes('tester', 'Planned for sprint...')
        self.assert_length(2 + 3, self.sb)
        # now check that the right items are inside
        self.assert_contains(self.us1, self.sb)
        self.assert_contains(task, self.sb)
        # this is checking that also us2 is in the sb as linked
        self.assert_contains(self.us2, self.sb)
        # now the requirements as well
        self.assert_contains(self.r1, self.sb)
        self.assert_contains(self.r2, self.sb)
    
    def test_changing_backlog_item_ticket(self):
        """Tests that it is possible to change a BacklogItem ticket"""
        story = self.teh.create_ticket(Type.USER_STORY)
        task = self.teh.create_task()
        bi_story = self.bimm.create(backlog_name=self.pb.name, ticket=story)
        bi_story.ticket = task
        self.assert_true(bi_story.save())
   
    def test_backlog_items_are_not_saved_after_first_initialization(self):
        """Tests that once the new ticket have been wrapped into a BacklogItem
        they are also stored in the DB"""
        # this just loads the backlog once
        pb_tickets = [t for t in self.tickets if \
                      t.get_type() in self.pb.config.ticket_types]
        self.assert_equals(len(pb_tickets),
                           len(self.pb))
        for t in pb_tickets:
            self.assert_none(self.bimm.get(backlog_name=self.pb.name,
                                           scope=self.pb.scope,
                                           ticket=t))
    
    def test_prevent_double_insertion_of_backlog_items(self):
        self.sb.add(self.t1)
        self.sb.add(self.t1)
        self.assert_length(1, self.sb._select_backlog_items())

    def test_backlog_query_return_existing_backlog_items(self):
        # first load the backlog and store the backlog items
        pb_tickets = [t for t in self.tickets if \
                      t.get_type() in self.pb.config.ticket_types]
        self.assert_equals(len(pb_tickets), len(self.pb))
        self.pb.set_ticket_positions([t.id for t in self.tickets])
        # this should have created backlog items for all the tickets
        bi_from_db = self.bimm.select(criteria={'backlog_name': self.pb.config.name,
                                                'scope': self.pb.scope})
        self.assert_equals(len(pb_tickets), len(bi_from_db))
        for bi in self.pb:
            self.assert_contains(bi, bi_from_db)
        
    def test_backlog_items_can_be_moved_to_head(self):
        story = self.teh.create_ticket(Type.USER_STORY)
        self.pb.insert(0, story)
        story_bi = self.bimm.get(backlog_name=self.pb.name,
                                 scope=self.pb.scope,
                                 ticket=story)
        self.assert_not_none(story_bi)
        self.assert_equals(0, story_bi.pos)
        self.assert_true(story in self.pb, "Backlog: %s" % self.pb)
        self.assert_equals(story, self.pb[0].ticket)
        self.assert_equals(0, self.pb[0].pos)
    
    def test_backlog_items_can_be_moved_in_the_middle(self):
        """Tests that BacklogItems can be moved to tail position"""
        story = self.teh.create_ticket(Type.USER_STORY)
        self.pb.insert(3, story)
        story_bi = self.bimm.get(backlog_name=self.pb.name,
                                 scope=self.pb.scope,
                                 ticket=story)
        self.assert_not_none(story_bi)
        self.assert_equals(3, story_bi.pos)
        self.assert_true(story in self.pb, "Backlog: %s" % self.pb)
        self.assert_equals(3, self.pb.index(story))
        self.assert_equals(story, self.pb[3].ticket)
        self.assert_equals(3, self.pb[3].pos)
        
    def test_backlog_items_are_added_in_last_position(self):
        story = self.teh.create_ticket(Type.USER_STORY)
        self.assert_contains(story, self.pb)
        self.assert_equals(self.pb[-1].ticket, story)
    
    def test_backlog_item_index(self):
        """Tests the index method of the backlog"""
        item = self.pb[3]
        self.assert_equals(3, self.pb.index(item))
        # test that raises a ValueError if the item doesn't belong to the
        # backlog
        task = self.teh.create_task()
        self.assert_raises(ValueError, lambda: self.pb.index(task))
    
    def test_backlog_includes_only_configured_types(self):
        task = self.teh.create_task()
        story = self.teh.create_story()
        # Neither the task nor the story have been planned, so the task
        # shouldn't be in the Product Backlog, and not in the Sprint
        # Backlog yet, the Story should be in the Product Backlog only.
        self.assert_not_contains(task, self.pb)
        self.assert_contains(story, self.pb)
        self.assert_not_contains(task, self.sb)
        self.assert_not_contains(story, self.sb)
        # now set the sprint to the story, and check that is not in the PB but
        # in the SB
        story[Key.SPRINT] = self.sprint.name
        story.save_changes('tester', 'planned for sprint')
        self.assert_not_contains(task, self.pb)
        self.assert_not_contains(story, self.pb)
        self.assert_not_contains(task, self.sb)
        self.assert_contains(story, self.sb)

    def test_backlog_is_updated_when_sprint_attribute_on_ticket_is_changed(self):
        self.assert_length(0, self.sb)
        task = self.teh.create_task(sprint=self.sprint.name)
        self.assert_equals(self.sprint.name, task[Key.SPRINT])
        self.assert_equals(self.sprint.name, self.sb.scope)
        self.assert_length(1, self.sb)
        self.assert_contains(task, self.sb)
        # now remove it
        task[Key.SPRINT] = ''
        task.save_changes(author='Tester', comment='removed from sprint')
        self.assert_not_contains(task, self.sb)
        self.assert_length(0, self.sb)

    def test_backlog_item_position_equals_its_index(self):
        for item in self.pb:
            if item.pos is not None:
                self.assert_equals(self.pb.index(item), item.pos)

