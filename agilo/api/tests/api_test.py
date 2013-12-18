# -*- encoding: utf-8 -*-
#   Copyright 2008 Agile42 GmbH, Berlin (Germany)
#   Copyright 2007 Andrea Tomasini <andrea.tomasini__at__agile42.com>
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
#       - Andrea Tomasini <andrea.tomasini__at__agile42.com>

from agilo.api import controller, validator
from agilo.core import PersistentObject, PersistentObjectManager, \
    PersistentObjectModelManager, Field
from agilo.test import AgiloTestCase
from agilo.utils import Type, Key


# Create test classes
class MyModel(PersistentObject):
    """A sample Model Object to test API"""
    class Meta(object):
        name = Field(unique=True)
        value = Field(type="real")


class MyModelManager(PersistentObjectModelManager):
    """The MyModel manager"""
    model = MyModel

    def for_model(self):
        return self.model


class ApiModelTest(AgiloTestCase):
    """Tests Agilo API, usage of Model, ModelManager"""
    def setUp(self):
        self.super()
        # Register object with PersistentManager
        PersistentObjectManager(self.env).create_table(MyModel)
    
    def testModelManagerBoundToModel(self):
        """Tests that the ModelManager is bound to the Model"""
        manager = MyModelManager(self.env)
        self.assert_equals(MyModel, manager.for_model())
        
    def testModelManagerCreateNewModel(self):
        """Tests that the ModelManager can create a new Model instance"""
        manager = MyModelManager(self.env)
        my_model = manager.create(name='test1', value=2.3)
        self.assert_true(isinstance(my_model, MyModel), "Got something else: %s" % \
                                                        type(my_model))
        self.assert_equals('test1', my_model.name)
        self.assert_equals(2.3, my_model.value)
        
    def testModelManagerGetModel(self):
        """Tests that the ModelManager can retrive a Model instance"""
        manager = MyModelManager(self.env)
        manager.create(name='test1', value=2.3)
        my_model = manager.get(name='test1')
        self.assert_true(isinstance(my_model, MyModel), "Got something else: %s" % \
                                                        type(my_model))
        self.assert_equals('test1', my_model.name)
        self.assert_equals(2.3, my_model.value)
        
        non_existing = manager.get(name='nonexistent')
        self.assert_none(non_existing)
        
    def testSimpleModelCaching(self):
        """Tests the caching of the ModelManager"""
        manager = MyModelManager(self.env)
        my_first_model = manager.create(name='test1', value=2.3)
        my_model = manager.get(name='test1')
        my_model_too = manager.get(name='test1')
        self.assert_equals(id(my_first_model), id(my_model))
        self.assert_equals(id(my_model_too), id(my_model))
        
    def testModelManagerSaveModel(self):
        """Tests the ModelManager save method"""
        manager = MyModelManager(self.env)
        sample_m = manager.create(name='sample', value=5)
        sample_m.value = 4
        manager.save(sample_m)
        sample_m = manager.get(name='sample')
        self.assert_equals(4, sample_m.value)

    def testTicketWithModelManager(self):
        """Tests the ticket creation via ModelManager"""
        from agilo.ticket.model import AgiloTicketModelManager
        manager = AgiloTicketModelManager(self.env)
        t1 = manager.create(summary='This is a test ticket', 
                                  t_type=Type.TASK,
                                  remaining_time='12',
                                  description='take this')
        self.assert_true(t1.exists)
        self.assertNotEqual(0, t1.id)
        self.assert_equals('This is a test ticket', t1[Key.SUMMARY])
        self.assert_equals('12', t1[Key.REMAINING_TIME])
        self.assert_equals('take this', t1[Key.DESCRIPTION])
        t2 = manager.get(tkt_id=t1.id)
        self.assert_true(t2.exists)
        self.assert_equals(t1.id, t2.id)
        # test cache too
        self.assert_equals(id(t1), id(t2))
        # Now change the summary
        t2.summary = 'A new summary'
        manager.save(t2, author='tester', comment='Updated summary...')
        # is the same object so...
        self.assert_equals(t2.summary, t1.summary)
    
    def test_model_cache_can_handle_multiple_primary_keys(self):
        """Check that the model cache checks all primary keys for a match and
        not only one of them."""
        class MultiplePrimaryKeyModel(PersistentObject):
            class Meta(object):
                name = Field(primary_key=True)
                sprint = Field(primary_key=True)
                value = Field(type="real")
        
        class MultiplePrimaryKeyModelManager(PersistentObjectModelManager):
            model = MultiplePrimaryKeyModel
        
        PersistentObjectManager(self.env).create_table(MultiplePrimaryKeyModel)
        manager = MultiplePrimaryKeyModelManager(self.env)
        manager.create(name='a', sprint='b', value=12)
        self.assert_none(manager.get(name='a', sprint='c'))
        
    def test_model_manager_does_not_return_items_from_cache_if_no_primary_key_matched(self):
        manager = MyModelManager(self.env)
        manager.create(name='test', value=2.3)
        # Now there is an item in the cache
        self.assert_none(manager.get(name=None))
        self.assert_none(manager.get(name=''))

# Test Controller API and the Command Pattern
class TestMeController(controller.Controller):
    """Tests the Controller and the command pattern"""
    class TestCommand(controller.ICommand):
        """This is a test command"""
        parameters = {'name': validator.MandatoryStringValidator, 
                      'number': validator.IntValidator}
        
        def _execute(self, controller, date_converter=None, 
                     as_key=None):
            """Execute the command"""
            return True
        

class ApiControllerTest(AgiloTestCase):
    """Tests the Controller API using the TestMeController"""
    
    def testCommandCreation(self):
        """Test the creation of a Command"""
        cmd = TestMeController.TestCommand(self.env, name='test', 
                                           number=9)
        self.assert_not_none(cmd)
        self.assert_equals('test', cmd. name)
        self.assert_equals(9, cmd.number)
    
    def testCommandValidation(self):
        """Test the validation of a Command"""
        cmd_valid = TestMeController.TestCommand(self.env, 
                                                 name='valid',
                                                 number=10)
        self.assert_true(cmd_valid.is_valid)
        # now change the number to a string to make it invalid
        try:
            cmd_valid.number = 'not valid value'
            self.fail("Accepted a string for a number!")
        except validator.ValidationError:
            pass
        
    def testCommandExecution(self):
        """Test the command execution"""
        cmd_valid = TestMeController.TestCommand(self.env,
                                                 name='valid',
                                                 number=10)
        tmc = TestMeController(self.env)
        self.assert_true(tmc.process_command(cmd_valid))


if __name__ == '__main__':
    from agilo.test.testfinder import run_unit_tests
    run_unit_tests(__file__)

