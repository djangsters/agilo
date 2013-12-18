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

from agilo.utils import BacklogType
from agilo.test import AgiloTestCase
from agilo.scrum.backlog.model import BacklogModelManager, BacklogTypeError


class BacklogModelManagerTest(AgiloTestCase):
    """Tests the Model Manager for the Backlog"""
    
    def testGetModelFromManager(self):
        """Tests the get model from the manager"""
        backlog = self.teh.create_backlog('TestModelBacklog')
        self.assert_true(backlog.exists)
        # Now try to get it with the Model Manager
        model_manager = BacklogModelManager(self.env)
        same_backlog = model_manager.get(name='TestModelBacklog')
        self.assert_equals(backlog.name, same_backlog.name)
        self.assert_equals(len(backlog), len(same_backlog))
        # Now check the object identity
        self.assert_equals(id(backlog), id(same_backlog))
        
    def testCreateModelFromManager(self):
        """Tests the creation of a new model using the Manager"""
        params = {'name': 'TestCreateBacklog'}
        model_manager = BacklogModelManager(self.env)
        backlog = model_manager.create(**params)
        self.assert_not_none(backlog)
        self.assert_true(backlog.exists)
        self.assert_equals('global', backlog.scope)
        # Now let's add a scope
        sprint = self.teh.create_sprint('ScopeSprint')
        params['name'] = 'AnotherBacklog'
        params['type'] = BacklogType.SPRINT
        params['scope'] = sprint.name
        sprint_backlog = model_manager.create(**params)
        self.assert_not_none(sprint_backlog)
        self.assert_true(sprint_backlog.exists)
        self.assert_equals(sprint.name, sprint_backlog.scope)
        self.assert_equals(BacklogType.SPRINT, sprint_backlog.config.type)
        # now trying to create a backlog twice should return None
        self.assert_none(model_manager.create(**params))
        
    def testDeleteBacklogFromManager(self):
        """Test the deletion of a Backlog using the model manager"""
        model_manager = BacklogModelManager(self.env)
        backlog = model_manager.create(name='TestDeleteBacklog')
        self.assert_not_none(backlog)
        self.assert_true(backlog.exists)
        self.assert_equals('global', backlog.scope)
        # now delete it
        model_manager.delete(backlog)
        self.assert_raises(BacklogTypeError, model_manager.get, name='TestDeleteBacklog')
        
    def testSelectBacklogFromManager(self):
        """Tests the select from the manager, with the order_by parameter"""
        model_manager = BacklogModelManager(self.env)
        letters = ['A', 'B', 'C']
        for letter in letters:
            backlog = model_manager.create(name='Test%sBacklog' % letter)
            self.assert_not_none(backlog)
            self.assert_true(backlog.exists)
            self.assert_equals('global', backlog.scope)
        # now select and verify that the default order is by name
        backlogs = model_manager.select()
        r_letters = [l for l in reversed(letters)]
        for backlog in backlogs:
            if backlog.name.startswith('Test'):
                letter = r_letters.pop()
                self.assert_equals('Test%sBacklog' % letter, backlog.name)
        
        # now sort descending by name
        backlogs = model_manager.select(order_by=['-name'])
        for backlog in backlogs:
            if backlog.name.startswith('Test'):
                letter = letters.pop()
                self.assert_equals('Test%sBacklog' % letter, backlog.name)
        