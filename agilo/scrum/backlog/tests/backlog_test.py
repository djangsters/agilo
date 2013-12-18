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

from datetime import timedelta

from trac.util.datefmt import to_datetime
from trac.ticket.model import Milestone

from agilo.scrum import SprintController
from agilo.scrum.backlog.controller import BacklogController
from agilo.scrum.backlog.model import Backlog, BacklogModelManager, \
    BacklogUpdater, MissingOrInvalidScopeError
from agilo.scrum.backlog.backlog_config import BacklogConfiguration
from agilo.scrum.metrics.model import TeamMetrics
from agilo.test import AgiloTestCase
from agilo.utils import Type, Key, BacklogType, Status
from agilo.utils.days_time import now


def print_backlog(backlog):
    """Print the backlog with properties for debugging"""
    for bi in backlog:
        print ">>> #%d(%s), bv: %s, sp: %s, rt: %s" % \
               (bi.id, bi.ticket.get_type(),
                bi[Key.BUSINESS_VALUE],
                bi[Key.STORY_PRIORITY],
                bi[Key.REMAINING_TIME]) 
        

class TestBacklog(AgiloTestCase):
    """Tests for the Backlog class"""
    
    def setUp(self):
        self.super()
        self.bmm = BacklogModelManager(self.env)
        # Creates and It's me backlog
        its_me = self.teh.create_sprint("It's me")
        self.assert_true(its_me.exists)

    def _create_sprint_backlog(self):
        """Creates stories and tasks for a Sprint Backlog and returns the Backlog"""
        sprint = self.teh.create_sprint("Test")
        s1 = self.teh.create_ticket(Type.USER_STORY, 
                                    props={Key.STORY_POINTS: '3', 
                                           Key.SPRINT: sprint.name})
        self.assert_true(s1.link_to(self.teh.create_ticket(Type.TASK, 
                                                           props={Key.REMAINING_TIME: '4',
                                                                  Key.SPRINT: sprint.name})))
        self.assert_true(s1.link_to(self.teh.create_ticket(Type.TASK,
                                                           props={Key.REMAINING_TIME: '8',
                                                                  Key.SPRINT: sprint.name})))
        self.assert_true(s1.link_to(self.teh.create_ticket(Type.TASK, 
                                                           props={Key.REMAINING_TIME: '4'})))
        s2 = self.teh.create_ticket(Type.USER_STORY, props={Key.STORY_POINTS: '5', 
                                                            Key.SPRINT: sprint.name})
        self.assert_true(s2.link_to(self.teh.create_ticket(Type.TASK, 
                                                           props={Key.REMAINING_TIME: '2',
                                                                  Key.SPRINT: sprint.name})))
        self.assert_true(s2.link_to(self.teh.create_ticket(Type.TASK, 
                                                           props={Key.REMAINING_TIME: '3'})))
        sprint_backlog = self.bmm.get(name="Sprint Backlog", scope=sprint.name)
        self.assert_contains(s1, sprint_backlog)
        self.assert_contains(s2, sprint_backlog)
        self.assert_length(5, sprint_backlog)
        return sprint_backlog
    
    def _create_product_backlog(self):
        """Creates Requirements and Stories for a Product Backlog and returns the Backlog"""
        def _create_story(props):
            """Creates a ticket of type story and returns it"""
            return self.teh.create_ticket(Type.USER_STORY, props=props)
        
        r1 = self.teh.create_ticket(Type.REQUIREMENT, props={Key.BUSINESS_VALUE: '3000'})
        self.assert_true(r1.link_to(_create_story({Key.STORY_PRIORITY: 'Linear'})))
        self.assert_true(r1.link_to(_create_story({Key.STORY_PRIORITY: 'Exciter'})))
        self.assert_true(r1.link_to(_create_story({Key.STORY_PRIORITY: 'Mandatory'})))
        r2 = self.teh.create_ticket(Type.REQUIREMENT, props={Key.BUSINESS_VALUE: '1200'})
        self.assert_true(r2.link_to(_create_story({Key.STORY_PRIORITY: 'Mandatory'})))
        self.assert_true(r2.link_to(_create_story({Key.STORY_PRIORITY: 'Exciter'})))
        r3 = self.teh.create_ticket(Type.REQUIREMENT, props={Key.BUSINESS_VALUE: '2000'})
        self.assert_true(r3.link_to(_create_story({Key.STORY_PRIORITY: 'Mandatory'})))
        r4 = self.teh.create_ticket(Type.REQUIREMENT, props={Key.BUSINESS_VALUE: '800'})
        self.assert_true(r4.link_to(_create_story({Key.STORY_PRIORITY: 'Linear'})))
        r5 = self.teh.create_ticket(Type.REQUIREMENT, props={Key.BUSINESS_VALUE: '3000'})
        self.assert_true(r5.link_to(_create_story({Key.STORY_PRIORITY: 'Exciter'})))
        self.assert_true(r5.link_to(_create_story({Key.STORY_PRIORITY: 'Mandatory'})))
        product_backlog = self.bmm.get(name="Product Backlog")
        self.assert_equals(len(product_backlog), 14)
        return product_backlog
    
    def testBacklogAsDictDecorator(self):
        """Tests that the Backlog car return itself with the Dict
        Decorator"""
    
    def testBacklogCreation(self):
        """Tests the creation of a Backlog"""
        global_backlog = BacklogConfiguration(self.env, name="Global Backlog")
        global_backlog.ticket_types = [Type.REQUIREMENT]
        global_backlog.save()
        # Now reload the same backlog and check that the type and order are kept
        b1 = self.bmm.get(name="Global Backlog")
        self.assert_equals(b1.ticket_types, [Type.REQUIREMENT])
    
    def testProductBacklogItems(self):
        """Tests the creation of a Global Backlog and add some Items to it"""
        backlog = BacklogConfiguration(self.env, name="Global Backlog")
        backlog.ticket_types = [Type.REQUIREMENT]
        backlog.save()
        # Create some tickets and add them to the Backlog
        b = self.bmm.get(name="Global Backlog")
        b.add(self.teh.create_ticket(Type.REQUIREMENT, props={Key.BUSINESS_VALUE: '3000'}))
        b.add(self.teh.create_ticket(Type.REQUIREMENT, props={Key.BUSINESS_VALUE: '1200'}))
        b.add(self.teh.create_ticket(Type.REQUIREMENT, props={Key.BUSINESS_VALUE: '2000'}))
        b.add(self.teh.create_ticket(Type.REQUIREMENT, props={Key.BUSINESS_VALUE: '800'}))
        b.add(self.teh.create_ticket(Type.REQUIREMENT, props={Key.BUSINESS_VALUE: '3000'}))
        # Now test that the ticket are sorted by the defined Key
        ref = 3000
        self.assert_equals(5, len(b), 'Wrong number of tickets in this (%s) Backlog!' % \
                                      len(b))
        # Now load it again, and verify that the order is still ok
        b1 = self.bmm.get(name="Global Backlog")
        self.assert_true(len(b1) > 0, 'There is no ticket associated to this Backlog!')

    def testMoveItemInBacklog(self):
        """Test the movement of an item into the backlog, change the position"""
        backlog = BacklogConfiguration(self.env, name="Global Backlog")
        backlog.ticket_types=[Type.REQUIREMENT]
        backlog.save()
        # Create some tickets and add them to the Backlog
        b = self.bmm.get(name="Global Backlog")
        b.add(self.teh.create_ticket(Type.REQUIREMENT, props={Key.BUSINESS_VALUE: '3000'}))
        b.add(self.teh.create_ticket(Type.REQUIREMENT, props={Key.BUSINESS_VALUE: '1200'}))
        b.add(self.teh.create_ticket(Type.REQUIREMENT, props={Key.BUSINESS_VALUE: '2000'}))
        b.add(self.teh.create_ticket(Type.REQUIREMENT, props={Key.BUSINESS_VALUE: '800'}))
        b.add(self.teh.create_ticket(Type.REQUIREMENT, props={Key.BUSINESS_VALUE: '3000'}))
        b1 = self.bmm.get(name="Global Backlog")
        t2000 = None
        for b in b1:
            #print "b: %s" % type(b)
            if int(b.ticket[Key.BUSINESS_VALUE]) == 2000:
                t2000 = b
                break
        self.assert_not_none(t2000)
        new_pos = b1.insert(0, t2000)
        self.assert_equals(new_pos, 0)
        # Now try to move a normal ticket and not a BacklogItem
        t2000 = self.teh.load_ticket(t_id=t2000.ticket.id)
        b1.insert(1, t2000)
        self.assert_equals(t2000, b1[1].ticket)

    def testBacklogPositionPersistence(self):
        """Tests the Backlog position persistence of items, after being saved and reloaded"""
        backlog = BacklogConfiguration(self.env, name="Global Backlog")
        backlog.ticket_types=[Type.REQUIREMENT]
        backlog.save()

        # Create some tickets and add them to the Backlog
        b = self.bmm.get(name="Global Backlog")
        b.add(self.teh.create_ticket(Type.REQUIREMENT, props={Key.BUSINESS_VALUE: '3000'}))
        b.add(self.teh.create_ticket(Type.REQUIREMENT, props={Key.BUSINESS_VALUE: '1200'}))
        b.add(self.teh.create_ticket(Type.REQUIREMENT, props={Key.BUSINESS_VALUE: '2000'}))
        # Now reload the backlog, move the item in pos 2 to 1, save and reload
        b1 = self.bmm.get(name="Global Backlog")
        self.assert_equals(3, len(b1))
        t1200 = b1[1]
        b1.insert(0, t1200)
        # reload the backlgo and verify that the item is in position 0
        b2 = self.bmm.get(name='Global Backlog')
        self.assert_equals(t1200.ticket.id, b2[0].ticket.id)
        self.assert_equals(0, b2[0].pos)
        
    def testBacklogWithItemNotAdded(self):
        """Tests the Backlog with Items that have not been explicitly added"""
        backlog = BacklogConfiguration(self.env, name="Global Backlog")
        backlog.ticket_types=[Type.REQUIREMENT]
        backlog.save()
        # Create some tickets and add them to the Backlog
        b = self.bmm.get(name="Global Backlog")
        t1 = self.teh.create_ticket(Type.REQUIREMENT, props={Key.BUSINESS_VALUE: '3000'})
        t_no = self.teh.create_ticket(Type.USER_STORY, props={Key.STORY_POINTS: '13'})
        t2 = self.teh.create_ticket(Type.REQUIREMENT, props={Key.BUSINESS_VALUE: '1200'})
        b1 = self.bmm.get(name="Global Backlog")
        # Test that a belonging ticket is really belonging
        self.assert_contains(t2, b1)
        # Test if the external ticket, has been loaded into the Backlog
        self.assert_contains(t1, b1)
        # Test that the t_no, User Story is also not in the Backlog
        self.assert_not_contains(t_no, b1)
    
    def testBacklogWithHierarchicalItems(self):
        """Tests the Backlog with multiple hierarchical types"""
        # Create 2 requirements and link 2 stories each
        r1 = self.teh.create_ticket(Type.REQUIREMENT, props={Key.BUSINESS_VALUE: '2000'})
        self.assert_true(r1.link_to(self.teh.create_ticket(Type.USER_STORY, 
                                                          props={Key.STORY_PRIORITY: 'Linear'})))
        self.assert_true(r1.link_to(self.teh.create_ticket(Type.USER_STORY, 
                                                          props={Key.STORY_PRIORITY: 'Mandatory'})))
        r2 = self.teh.create_ticket(Type.REQUIREMENT, props={Key.BUSINESS_VALUE: '3000'})
        self.assert_true(r2.link_to(self.teh.create_ticket(Type.USER_STORY, 
                                                          props={Key.STORY_PRIORITY: 'Exciter'})))
        self.assert_true(r2.link_to(self.teh.create_ticket(Type.USER_STORY, 
                                                          props={Key.STORY_PRIORITY: 'Linear'})))
        # Now create a Backlog with both type and lets' verify that the tickets are there
        backlog = BacklogConfiguration(self.env, name="Global Backlog")
        backlog.ticket_types=[Type.REQUIREMENT, Type.USER_STORY]
        backlog.save()
        b = self.bmm.get(name="Global Backlog")
        self.assert_equals(6, len(b))
        self.assert_contains(r1, b)
        for at in r1.get_outgoing():
            self.assert_contains(at, b)
        self.assert_contains(r1, b)
        for at in r2.get_outgoing():
            self.assert_contains(at, b)
        
    def testBacklogForSprint(self):
        """Tests a Backlog associated to a Sprint"""
        # Creates a Milestone
        m = Milestone(self.env)
        m.name = "Milestone 1"
        m.insert()
        # Create a Sprint
        sprint = self.teh.create_sprint( 
                        name="Sprint 1", 
                        start=to_datetime(t=None), 
                        duration=20,
                        milestone=m.name)
        # Create some tickets
        # s1(s) -> t1(s)
        #       -> t2(s)
        #       -> t3
        # s2    -> t4(s)
        #       -> t5 
        s1 = self.teh.create_ticket(Type.USER_STORY, props={Key.STORY_POINTS: '3', 
                                                            Key.SPRINT: sprint.name})
        self.assert_equals(s1[Key.SPRINT], sprint.name)
        self.assert_true(s1.link_to(self.teh.create_ticket(Type.TASK, props={Key.REMAINING_TIME: '4',
                                                                             Key.SPRINT: sprint.name})))
        self.assert_true(s1.link_to(self.teh.create_ticket(Type.TASK, props={Key.REMAINING_TIME: '8',
                                                                             Key.SPRINT: sprint.name})))
        self.assert_true(s1.link_to(self.teh.create_ticket(Type.TASK, props={Key.REMAINING_TIME: '4'})))
        s2 = self.teh.create_ticket(Type.USER_STORY, props={Key.STORY_POINTS: '5'})
        self.assert_true(s2.link_to(self.teh.create_ticket(Type.TASK, props={Key.REMAINING_TIME: '2',
                                                                             Key.SPRINT: sprint.name})))
        self.assert_true(s2.link_to(self.teh.create_ticket(Type.TASK, props={Key.REMAINING_TIME: '3'})))
        # Creates the Backlog bound to the Sprint
        backlog = BacklogConfiguration(self.env, name="Sprint-Backlog", type=BacklogType.SPRINT)
        backlog.ticket_types=[Type.USER_STORY, Type.TASK]
        backlog.save()
        # The Backlog should contains only the items planned for the Sprint, and with parents
        # planned for the Sprint too
        backlog = self.bmm.get(name="Sprint-Backlog", scope=sprint.name)
        self.assert_length(5, backlog)
        
    def testBacklogForMultipleSprint(self):
        """Tests a Backlog associated to a Sprint with multiple sprints"""
        # Creates a Milestone
        m = Milestone(self.env)
        m.name = "Milestone 1"
        m.insert()
        # Create 2 Sprints
        sprint1 = self.teh.create_sprint(
                         name="Sprint 1", 
                         start=to_datetime(t=None), 
                         duration=20,
                         milestone=m.name)
        sprint2 = self.teh.create_sprint( 
                         name="Sprint 2", 
                         start=to_datetime(t=None), 
                         duration=20,
                         milestone=m.name)
        # Create some tickets
        s1 = self.teh.create_ticket(Type.USER_STORY, 
                                    props={Key.STORY_POINTS: '3', 
                                           Key.SPRINT: sprint1.name})
        self.assert_true(s1.link_to(self.teh.create_ticket(Type.TASK, 
                                                           props={Key.REMAINING_TIME: '4',
                                                                  Key.SPRINT: sprint1.name})))
        self.assert_true(s1.link_to(self.teh.create_ticket(Type.TASK,
                                                           props={Key.REMAINING_TIME: '8',
                                                                  Key.SPRINT: sprint1.name})))
        self.assert_true(s1.link_to(self.teh.create_ticket(Type.TASK, 
                                                           props={Key.REMAINING_TIME: '4'})))
        s2 = self.teh.create_ticket(Type.USER_STORY, props={Key.STORY_POINTS: '5', 
                                                            Key.SPRINT: sprint2.name})
        self.assert_true(s2.link_to(self.teh.create_ticket(Type.TASK, 
                                                           props={Key.REMAINING_TIME: '2',
                                                                  Key.SPRINT: sprint2.name})))
        self.assert_true(s2.link_to(self.teh.create_ticket(Type.TASK, 
                                                           props={Key.REMAINING_TIME: '3'})))
        # Creates the Backlog bound to the Sprint
        backlog = BacklogConfiguration(self.env, name="Sprint-Backlog", type=BacklogType.SPRINT)
        backlog.ticket_types = [Type.USER_STORY, Type.TASK]
        backlog.save()
        # The Backlog should contains only the items planned for the Sprint, and with parents
        # planned for the Sprint too
        backlog1 =  self.bmm.get(name="Sprint-Backlog", scope=sprint1.name)
        self.assert_length(3, backlog1)
        backlog2 =  self.bmm.get(name="Sprint-Backlog", scope=sprint2.name)
        self.assert_length(2, backlog2)
    
    def testGlobalBacklogWithStrictOption(self):
        """Tests a global backlog with the Strict option"""
        backlog = BacklogConfiguration(self.env, name="Bug-Backlog")
        backlog.ticket_types=[Type.BUG, Type.TASK]
        backlog.save()
        # Build a hierarchy of Bug tasks
        b1 = self.teh.create_ticket(Type.BUG)
        t1 = self.teh.create_ticket(Type.TASK, 
                                    props={Key.REMAINING_TIME: '3'})
        t2 = self.teh.create_ticket(Type.TASK, 
                                    props={Key.REMAINING_TIME: '7'})
        # Link the Bug only with one task
        self.assert_true(b1.link_to(t1))
        self.assert_equals('', b1[Key.SPRINT])
        # Standard trac fields must not be None (see property change rendering
        # for ticket preview)
        self.assert_equals('', b1[Key.MILESTONE])
        self.assert_equals(Type.BUG, b1[Key.TYPE])
        self.assert_equals('', t1[Key.SPRINT])
        self.assert_equals('', t1[Key.MILESTONE])
        self.assert_equals('', t2[Key.SPRINT])
        self.assert_equals('', t2[Key.MILESTONE])
        
        # Now load the backlog, and check that even with strict
        # a global backlog shows all the tickets
        b = self.bmm.get(name="Bug-Backlog")
        if len(b) != 3:
            print_backlog(b)
            self.fail("Backlog count wrong! %s != 3" % \
                       len(b))
        # Now links also the second task
        self.assert_true(b1.link_to(t2))
        # Now reload the backlog and check if the second task is there too
        self.assert_length(3, b)
        # Now plan the a task for a sprint so that should disappear from the
        # backlog
        s = self.teh.create_sprint("Test")
        t1[Key.SPRINT] = s.name
        self.assert_true(t1.save_changes('Tester', 'Planned...'))
        self.assert_length(2, b)
    
    def testScopedBacklogWithClosedTicket(self):
        """Tests if a scoped backlog loads also closed tickets"""
        
        sprint1 = self.teh.create_sprint("Sprint Scoped")
        sprint1.save()
        # Creates the Backlog bound to a scope (Sprint)
        backlog = BacklogConfiguration(self.env, name="Scoped-Backlog", type=BacklogType.SPRINT)
        backlog.ticket_types = [Type.USER_STORY, Type.TASK]
        backlog.save()
        # Create 1 ticket
        task = self.teh.create_ticket(Type.TASK, 
                                      props={Key.REMAINING_TIME: '12',
                                             Key.SPRINT: sprint1.name})
        # Force reload
        backlog = self.bmm.get(name="Scoped-Backlog", 
                               scope=sprint1.name)
        self.assert_true(task in backlog)
        self.assert_equals(len(backlog), 1)
        task[Key.STATUS] = Status.CLOSED
        task.save_changes('tester', 'Changed Status')
        # Now should still be there even if closed, because the backlog is scoped
        self.assert_true(task in backlog)
        self.assert_equals(len(backlog), 1)
        
    def testDeleteBacklog(self):
        """Tests the deletion of a Backlog"""
        backlog = BacklogConfiguration(self.env, name="Delete-Backlog") 
        backlog.ticket_types=[Type.USER_STORY, Type.TASK]
        backlog.save()
        # Test that the backlog exists
        try:
            b2 = self.bmm.get(name="Delete-Backlog")
            self.assert_true(b2.delete())
        except Exception, e:
            print "Error: %s" % unicode(e)
            self.fail("Not able to load backlog!!!")
        try:
            b2 = self.bmm.get(self.env, "Delete-Backlog")
            self.fail("The Backlog was not deleted!!!")
        except:
            self.assert_true(True)
        
    def testRemoveFromBacklogsWhenClosed(self):
        """Test the remove from a backlog when the ticket gets closed and the
        backlog is global"""
        s = self.teh.create_sprint('Test')
        t1 = self.teh.create_ticket(Type.USER_STORY, props={Key.STORY_POINTS: '8'})
        t2 = self.teh.create_ticket(Type.USER_STORY, props={Key.STORY_POINTS: '5', Key.SPRINT: s.name})
        b1 = BacklogConfiguration(self.env, name="Backlog")
        b1.ticket_types = [Type.USER_STORY]
        b1.save()
        b1 = self.bmm.get(name="Backlog")
        self.assert_equals(len(b1), 1)
        self.assert_true(t1 in b1)
        self.assert_false(t2 in b1)
        b2 = BacklogConfiguration(self.env, name="Scoped", type=BacklogType.SPRINT)
        b2.ticket_types = [Type.USER_STORY]
        b2.save()
        b2 = self.bmm.get(name="Scoped", scope=s.name)
        self.assert_equals(len(b2), 1)
        self.assert_true(t2 in b2)
        self.assert_false(t1 in b2)
        # Now close the tickets, should go away from the b1 and remain in b2
        t1[Key.STATUS] = t2[Key.STATUS] = Status.CLOSED
        t1.save_changes('tester', 'closed t1 ticket...')
        t2.save_changes('tester', 'closed t2 ticket...')
        self.assert_false(t1 in b1)
        self.assert_false(t2 in b1)
        self.assert_false(t1 in b2)
        self.assert_true(t2 in b2)
        # Now remove directly a BacklogItem
        for bi in b1:
            bi[Key.STATUS] = Status.CLOSED
            bi.save()
            self.assert_false(bi in b1, "Ticket %s still in backlog!!!" % bi)

    def testTicketsUpdateFromBacklog(self): 
        """Tests that updating multiple tickets updates""" 
        sprint_backlog = self._create_sprint_backlog() 
        old_values = {} 
        for item in sprint_backlog: 
            if item[Key.TYPE] == Type.TASK: 
                rem_time = int(item[Key.REMAINING_TIME] or 0) 
                old_values[item[Key.ID]] = str(rem_time) 
                item[Key.REMAINING_TIME] = str(rem_time + 1)
                item.save()

        # Now save the backlog and check that the tickets really got 
        # updated 
        for item in sprint_backlog: 
            if item[Key.TYPE] == Type.TASK: 
                self.assert_equals(int(old_values[item[Key.ID]]) + 1,
                                   int(item[Key.REMAINING_TIME])) 
                # reload the ticket so we are sure it is saved in the 
                # db. 
                temp_ticket = self.teh.load_ticket(item.ticket) 
                self.assert_equals(int(old_values[item[Key.ID]]) + 1,
                                   int(temp_ticket[Key.REMAINING_TIME])) 

    def testLoadingBacklogWithQuotesInNameDoesNotBlowUp(self):
        # This is a regression test for badly quoted SQL
        Backlog(self.env, Key.SPRINT_BACKLOG, scope="It's me")
    
    def testLoadingBacklogWithQuotesInScopeDoesNotBlowUp(self):
        # This is a regression test for badly quoted SQL
        Backlog(self.env, Key.SPRINT_BACKLOG, scope="It's me")
    
    def testLoadingReleaseBacklogWithQuotesInMilestoneNameDoesNotBlowUp(self):
        # This is a regression test for badly quoted SQL
        release_backlog = 'Release Backlog'
        milestone = self.teh.create_milestone("It's me")
        self.assert_true(milestone.exists)
        backlog = BacklogConfiguration(self.env, name=release_backlog, type=BacklogType.MILESTONE)
        backlog.save()
        self.bmm.get(name=release_backlog, scope="It's me")
    
    def testLoadingReleaseBacklogWithQuotesInSprintNameDoesNotBlowUp(self):
        # This is a regression test for badly quoted SQL
        release_backlog = 'Release Backlog'
        self.teh.create_milestone('1.0')
        rb = BacklogConfiguration(self.env, release_backlog, type=BacklogType.MILESTONE)
        rb.save()
        Backlog(self.env, release_backlog, scope='1.0')
    
    def testCanRemoveTicketFromBacklogEvenIfSprintNameHasQuotes(self):
        # This is a regression test for badly quoted SQL
        task = self.teh.create_ticket(Type.TASK, {Key.SUMMARY: 'foo'})
        BacklogUpdater(self.env).ticket_changed(task, None, None, {Key.SPRINT: "It's me"})
    


class GlobalBacklogAddingAndRemovingTicketsTest(AgiloTestCase):
    
    def setUp(self):
        self.super()
        
        self.backlog_name = "JumpingTickets"
        self.backlog = self.teh.create_backlog_without_tickets(name=self.backlog_name, type=BacklogType.GLOBAL, 
            ticket_types=[Type.REQUIREMENT, Type.USER_STORY])
        self.requirement = self.teh.create_ticket(Type.REQUIREMENT, {Key.SUMMARY: 'req1', Key.MILESTONE: 'milestone1'})
        self.story = self.teh.create_ticket(Type.USER_STORY, {Key.SUMMARY: 'story'})
        self.requirement.link_to(self.story) # always pulls requiremnt into the global backlog
        BacklogController.set_ticket_positions(self.env, name=self.backlog_name, scope=BacklogType.GLOBAL, 
            positions=[self.requirement.id, self.story.id])
    
    def test_backlog_updater_will_not_move_position_of_ticket_that_is_pulled_in_by_its_child(self):
        self.assert_equals(self.requirement, self.backlog[0], "should be first item")
        
        self.requirement[Key.SUMMARY] = 'fnord'
        self.requirement.save_changes(None, None)
        
        self.assert_equals(self.requirement, self.backlog[0], "shouldn't loose position in backlog")
    
    def test_keys_cleans_out_items_removed_from_the_backlog(self):
        self.story[Key.MILESTONE] = 'milestone1'
        self.story.save_changes(None, None)
        self.assert_length(0, self.backlog) # both story and requirement should be removed from the global backlog
        self.assert_length(0, self.backlog.keys())
    


class TestReleaseBacklog(AgiloTestCase):
    """Tests the Release Backlog"""
    
    def setUp(self):
        self.super()
        self.bmm = BacklogModelManager(self.env)
    
    def test_backlog_shows_right_tickets(self):
        """Tests the Release Backlog shows the Requirements belonging to a 
        specific Milestone"""
        sprint = self.teh.create_sprint("Release Sprint")
        release_backlog = BacklogConfiguration(self.env, name="Release Backlog", type=BacklogType.MILESTONE)
        release_backlog.ticket_types = [Type.REQUIREMENT, Type.USER_STORY]
        release_backlog.save()
        req = self.teh.create_ticket(Type.REQUIREMENT, props={Key.MILESTONE: sprint.milestone})
        # load the real backlog
        release_backlog = self.bmm.get(name="Release Backlog", scope=sprint.milestone)
        self.assert_contains(req, release_backlog)
        self.assert_length(1, release_backlog)
        # Now add 2 stories to the requirement, one planned for the sprint one
        # not, only the one assigned to the sprint should appear in the backlog
        us1 = self.teh.create_ticket(Type.USER_STORY, props={Key.SPRINT: sprint.name})
        us2 = self.teh.create_ticket(Type.USER_STORY)
        self.assert_true(us1 in release_backlog)
        self.assert_not_contains(us2, release_backlog)
        self.assert_length(1 + 1, release_backlog)


class TestSprintBacklog(AgiloTestCase):
    """Specific tests for the Sprint Backlog"""

    def setUp(self):
        self.super()
        self.bmm = BacklogModelManager(self.env)
    
    def test_tickets_from_other_sprint_not_appearing(self):
        """
        Tests that tasks created for other sprints are not appearing in the
        sprint backlog, see bug #345
        (https://dev.agile42.com/ticket/345)
        """
        s = self.teh.create_sprint("Test")
        sb = self.teh.create_backlog("Sprint Backlog", 
                                     num_of_items=100,
                                     ticket_types=[Type.USER_STORY, Type.TASK],
                                     b_type=BacklogType.SPRINT, 
                                     scope=s.name)
        self.assert_length(100, sb)
        # get a ticket from the backlog and check that it is planned for the sprint
        self.assert_equals(s.name, sb[10][Key.SPRINT])
        # Now add an extra ticket
        task = self.teh.create_ticket(Type.TASK, props={Key.SPRINT: s.name,
                                                        Key.REMAINING_TIME: '2'})
        self.assert_length(101, sb)
        self.assert_contains(task, sb)
        # Now remove the ticket explicitly and check if the sprint field is set
        # to None
        self.teh.move_changetime_to_the_past([task])
        sb.remove(task)
        self.assert_not_contains(task, sb)
        # reload task and backlog, the remove should have saved the task
        task = self.teh.load_ticket(task)
        self.assert_not_contains(task, sb)
        self.assert_equals('', task[Key.SPRINT])
        # Now move the ticket to another sprint
        s2 = self.teh.create_sprint("Another Sprint")
        task[Key.SPRINT] = s2.name
        task.save_changes('tester', 'Moved to sprint %s' % s2.name, 
                          when=now() + timedelta(seconds=1))
        self.assert_equals(s2.name, task[Key.SPRINT])
        # Now should not be in the backlog anymore
        self.assert_not_contains(task, sb)
        # Now change sprint again, twice
        task[Key.SPRINT] = s.name
        task.save_changes('tester', 'Moved to sprint %s' % s.name, 
                          when=now() + timedelta(seconds=2))
        self.assert_contains(task, sb)
        # again
        task[Key.SPRINT] = s2.name
        task.save_changes('tester', 'Moved to sprint %s' % s2.name, 
                          when=now() + timedelta(seconds=3))
        self.assert_equals(s2.name, task[Key.SPRINT])
        # Now should not be in the backlog anymore
        self.assert_not_contains(task, sb)
    
    def test_referenced_requirements_are_displayed_in_the_sprint_backlog(self):
        """Test that referenced requirements are shown in the sprint backlog 
        even if they are planned for a milestone."""
        milestone = self.teh.create_milestone('1.0')
        sprint = self.teh.create_sprint("First Sprint")
        backlog_name = 'My Backlog'
        my_backlog = BacklogConfiguration(self.env, name=backlog_name, type=BacklogType.SPRINT)
        my_backlog.ticket_types=[Type.USER_STORY, Type.TASK, Type.REQUIREMENT]
        my_backlog.save()
        req = self.teh.create_ticket(Type.REQUIREMENT, {Key.SUMMARY: 'Requirement', Key.MILESTONE: milestone.name})
        story = self.teh.create_ticket(Type.USER_STORY, {Key.SUMMARY: 'Story', Key.SPRINT: sprint.name})
        req.link_to(story)
        
        backlog = self.bmm.get(name=backlog_name, scope=sprint.name)
        self.assert_length(2, backlog)


class BacklogModelTest(AgiloTestCase):
    
    def _milestone_backlog(self, milestone_name=None):
        milestone_backlog_config = BacklogConfiguration(self.env, name='Milestone', type=BacklogType.MILESTONE)
        if not milestone_backlog_config.exists:
            milestone_backlog_config.ticket_types = [Type.REQUIREMENT, Type.USER_STORY]
            milestone_backlog_config.save()
        return Backlog(self.env, name='Milestone', scope=milestone_name)
    
    def _global_backlog(self):
        global_backlog_config = BacklogConfiguration(self.env, name='Global')
        if not global_backlog_config.exists:
            global_backlog_config.ticket_types = [Type.REQUIREMENT, Type.USER_STORY]
            global_backlog_config.save()
        return Backlog(self.env, name='Global') 
    
    def _sprint_backlog(self, sprint_name=None):
        sprint_backlog_config = BacklogConfiguration(self.env, name='Sprint', type=BacklogType.SPRINT)
        if not sprint_backlog_config.exists:
            sprint_backlog_config.save()
        return Backlog(self.env, name='Sprint', scope=sprint_name)
    
    # --- Test cases -----------------------------------------------------------
    
    def test_knows_if_it_is_a_global_backlog(self):
        backlog = self._global_backlog()
        self.assert_false(backlog.is_sprint_backlog())
        self.assert_false(backlog.is_milestone_backlog())
        self.assert_true(backlog.is_global_backlog())
    
    def test_knows_that_other_backlog_types_are_not_sprint_backlogs(self):
        self.assert_false(self._global_backlog().is_sprint_backlog())
        milestone = self.teh.create_milestone('AMilestone')
        self.assert_false(self._milestone_backlog(milestone.name).is_sprint_backlog())
    
    def test_scoped_backlog_initialization_without_scope_raises_exception(self):
        self.assert_raises(MissingOrInvalidScopeError, self._sprint_backlog)
    
    def test_can_identify_sprint_backlogs_with_sprint(self):
        sprint = self.teh.create_sprint('ASprint')
        backlog = self._sprint_backlog(sprint.name)
        self.assert_true(backlog.is_sprint_backlog())
    
    def test_loading_scoped_backlog_without_scope_raises_exception(self):
        self.assert_raises(MissingOrInvalidScopeError, self._sprint_backlog)
    
    def test_knows_if_it_is_a_milestone_backlog(self):
        milestone = self.teh.create_milestone('AMilestone')
        backlog = self._milestone_backlog(milestone.name)
        self.assert_false(backlog.is_sprint_backlog())
        self.assert_false(backlog.is_global_backlog())
        self.assert_true(backlog.is_milestone_backlog())
    
    def test_raise_exception_if_sprint_on_non_sprint_backlog(self):
        milestone = self.teh.create_milestone('AMilestone')
        self.assert_raises(ValueError, self._milestone_backlog(milestone.name).sprint)
        self.assert_raises(ValueError, self._global_backlog().sprint)
    
    def test_raises_exception_if_invalid_sprint_name_set(self):
        self.assert_raises(MissingOrInvalidScopeError, self._sprint_backlog, 'invalid_sprint')
    
    def test_can_return_sprint_for_sprint_backlog(self):
        sprint = self.teh.create_sprint('ASprint')
        self.assert_equals(sprint, self._sprint_backlog(sprint.name).sprint())
    
    def test_backlog_removes_leftover_backlog_items_on_load(self):
        pass
    
    # --- Loading planned items in a backlog -----------------------------------
    
    def test_can_include_planned_items_in_global_backlog(self):
        milestone = self.teh.create_milestone('AMilestone')
        story = self.teh.create_story(milestone=milestone.name)
        self.assert_equals(milestone.name, story[Key.MILESTONE])
        backlog = self._global_backlog()
        backlog.config.include_planned_items = True
        backlog.config.save()
        
        backlog = self._global_backlog()
        self.assert_length(1, backlog)

