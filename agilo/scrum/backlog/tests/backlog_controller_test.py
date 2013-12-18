# -*- encoding: utf-8 -*-
#   Copyright 2008 Agile42 GmbH, Berlin (Germany)
#   Copyright 2011 Agilo Software GmbH All rights reserved
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

from agilo.test import AgiloTestCase
from agilo.scrum.backlog.model import BacklogTypeError
from agilo.scrum.backlog.controller import BacklogController
from agilo.utils import Type, BacklogType, Key


class BacklogControllerTest(AgiloTestCase):
    """Tests the Backlog Controller"""
    
    def setUp(self):
        """Loads a Backlog Controller"""
        self.super()
        self.controller = BacklogController(self.env)

    def get(self, name, scope):
        """Send a get Command to get a Backlog with the given name and scope"""
        get_backlog = BacklogController.GetBacklogCommand(self.env,
                                                          name=name,
                                                          scope=scope)
        return self.controller.process_command(get_backlog)

    def testGetBacklogCommand(self):
        """Tests the GetBacklogCommand"""
        # test with a non existing backlog
        get_backlog = BacklogController.GetBacklogCommand(self.env,
                                                          name='NotExisting')
        self.assert_raises(BacklogTypeError, self.controller.process_command, get_backlog)

        # now create a backlog and test it
        backlog = self.teh.create_backlog('RealOne', num_of_items=10)
        self.assert_true(backlog.exists)
        self.assert_length(10, backlog)
        
        get_backlog = BacklogController.GetBacklogCommand(self.env,
                                                          name='RealOne')
        real_one = self.controller.process_command(get_backlog)
        self.assert_not_none(real_one)
        self.assert_true(real_one.exists)
        self.assert_length(10, real_one)
        # now try with a Sprint Backlog
        sprint = self.teh.create_sprint('MySprint')
        backlog = self.teh.create_backlog('MySprintBacklog', 
                                          num_of_items=10, 
                                          b_type=1, 
                                          scope=sprint.name)
        self.assert_true(backlog.exists)
        items_count = len(backlog)
        get_backlog = BacklogController.GetBacklogCommand(self.env,
                                                          name='MySprintBacklog',
                                                          scope='MySprint')
        sprint_backlog = self.controller.process_command(get_backlog)
        self.assert_not_none(sprint_backlog)
        self.assert_true(sprint_backlog.exists)
        self.assert_length(items_count, sprint_backlog)
        
    def testCreateBacklogCommand(self):
        """Test the creation of a Backlog with various parameters"""
        create_cmd = BacklogController.CreateBacklogCommand(self.env,
                                                            name='TestBacklog')
        backlog = self.controller.process_command(create_cmd)
        self.assert_not_none(backlog)
        self.assert_true(backlog.exists)
        
        # Try to create a backlog that already exist
        backlog = self.controller.process_command(create_cmd)
        self.assert_none(backlog)
        
    def testMoveBacklogItemCommand(self):
        """Test the moving of a backlog item in the backlog"""
        backlog = self.teh.create_backlog('MovingBacklog', num_of_items=20)
        first_item = backlog[0]
        # create a moving command and move the first item to the 5th
        # poistion in the backlog
        fifth_item = backlog[4]
        move_cmd = BacklogController.MoveBacklogItemCommand(self.env,
                                                            name='MovingBacklog',
                                                            ticket=first_item,
                                                            to_pos=4)
        self.controller.process_command(move_cmd)
        # we need to reload the backlog from the DB
        get_reload_cmd = BacklogController.GetBacklogCommand(self.env,
                                                             name='MovingBacklog')
        backlog = self.controller.process_command(get_reload_cmd)
        self.assert_equals(backlog[4].ticket, first_item.ticket)
        self.assert_equals(backlog[3].ticket, fifth_item.ticket)
        self.assert_equals(4, backlog[4].pos)
        self.assert_equals(3, backlog[3].pos)
    
    def testCanMoveItemsInGlobalBacklogByHandingInTickets(self):
        backlog = self.get(name='Product Backlog', scope=None)
        requirement = self.teh.create_ticket(Type.REQUIREMENT)
        backlog.add(requirement)
        backlog.add(self.teh.create_ticket(Type.REQUIREMENT))
        backlog.add(self.teh.create_ticket(Type.REQUIREMENT))
        backlog.save()
                
        first_item = backlog[0]
        # cleaning out the cache, because if this where a new request, the cache would be empty and this would throw
        move = BacklogController.MoveBacklogItemCommand(self.env,
                                                        name='Product Backlog',
                                                        ticket=first_item,
                                                        to_pos=2)
        self.controller.process_command(move)
        index = backlog.index(first_item)
        self.assert_equals(2, index)
        self.assert_equals(2, backlog[index].pos)
        self.assert_equals(first_item, backlog[index].ticket)

    # FIXME (AT): the save command is not really needed, it should be more focused on the
    # BacklogConfiguration, from the moment it does only safe those parameters, as the
    # scope is not persisted. This is in contradiction with the BacklogModelManager itself
    def testSaveBacklogCommand(self):
        """Tests the saving backlog command"""
        sprint = self.teh.create_sprint('MyChaningSprint')
        backlog = self.teh.create_backlog('ChangingBacklog',
                                          ticket_types=[Type.USER_STORY, Type.TASK],
                                          b_type=BacklogType.SPRINT,
                                          scope=sprint.name,
                                          num_of_items=20)
        self.assert_length(20, backlog)
        # now remove some of the items and save
        backlog.remove(backlog[0])
        backlog.remove(backlog[1])
        self.assert_length(18, backlog)
        # now save it and reload it
        cmd_save_backlog = BacklogController.SaveBacklogCommand(self.env,
                                                                name='ChangingBacklog',
                                                                scope=sprint.name)
        self.controller.process_command(cmd_save_backlog)
        # now reload the backlog and check the two items have been removed
        cmd_get_backlog = BacklogController.GetBacklogCommand(self.env,
                                                              name='ChangingBacklog',
                                                              scope=sprint.name)
        backlog = self.controller.process_command(cmd_get_backlog)
        self.assert_length(18, backlog)

    def testGetBacklogListCommand(self):
        """Tests that the BacklogModule returns the list of Backlogs configured"""
        cmd_list = BacklogController.ListBacklogsCommand(self.env)
        blist = self.controller.process_command(cmd_list)
        self.assert_length(2, blist) # Only Product Backlog and Sprint Backlog
        # the list is returned ordered by type and than by name
        self.assert_equals(Key.PRODUCT_BACKLOG, blist[0][Key.NAME])
        self.assert_equals(Key.SPRINT_BACKLOG, blist[1][Key.NAME])

