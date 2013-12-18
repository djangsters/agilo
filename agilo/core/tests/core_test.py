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

from datetime import datetime
from random import randint

from trac.util.datefmt import FixedOffset, utc

from agilo.core import Field, PersistentObject, PersistentObjectManager, \
    Relation, UnableToSaveObjectError, PersistentObjectModelManager
from agilo.utils.compat import exception_to_unicode
from agilo.test import AgiloTestCase


# Test PO Object
class MyPO(PersistentObject):
    class Meta(object):
        name = Field(primary_key=True)
        users = Field(type='number')
        amount = Field(type='real')
        description = Field()


class MyPOwithoutPK(PersistentObject):
    class Meta(object):
        name = Field(unique=True)
        description = Field()


class MyPOModelManager(PersistentObjectModelManager):
    model = MyPO


class CoreTest(AgiloTestCase):
    
    def setUp(self):
        """Setup defines a dummy object and creates an environment"""
        self.super()
        self.pom = PersistentObjectManager(self.env)
        #FIXME: I don't know why, but putting the test to check if the table
        # is created, after a while gives error. I didn't have the chance to 
        # check it through, but I guess it is related to the :memory: db that
        # SQLite reallocate in the same position, so the new Env (which has 
        # a different Python id) is till pointing to the old InMemoryDatabase
        self.pom.create_table(MyPO)
        self.assert_true(self.pom.create_table(MyPOwithoutPK))
    
    def tearDown(self):
        self.teh.cleanup()
        self.super()
    
    def testDefineAndCreatePersistentObject(self):
        """Tests definition and creation of a PersistentObject"""
        class DummyPersistentObject(PersistentObject):
            class Meta(object):
                name = Field(primary_key=True)
                number = Field(type='real')
        
        self.assert_true(self.pom.create_table(DummyPersistentObject))
        
        # Now instantiate the object
        dpo = DummyPersistentObject(self.env, name='Test', number=2.5)
        self.assert_true(hasattr(dpo, 'number'))
        self.assert_equals(dpo.number, 2.5)
        self.assert_true(hasattr(dpo, 'name'))
        self.assert_equals(dpo.name, 'Test')
        # Save the object
        self.assert_true(dpo.save())
        dpo_copy = DummyPersistentObject(self.env, name='Test')
        self.assert_true(hasattr(dpo_copy, 'name'))
        self.assert_equals(dpo_copy.name, 'Test')
        self.assert_true(hasattr(dpo_copy, 'number'))
        self.assert_equals(dpo_copy.number, 2.5)
        
    def testPersistentObjectExistence(self):
        """Tests the persistent object exists method"""
        myPO = MyPO(self.env)
        myPO.name = 'This is my first Po'
        myPO.users = 3
        self.assert_true(myPO.save())
        self.assert_true(myPO.exists)
        
        myPO2 = MyPO(self.env)
        self.assert_false(myPO2.exists)
        
    def testPersistenceWithoutPK(self):
        """Tests the persistent object without the PK"""
        myPO = MyPOwithoutPK(self.env, name='Test')
        self.assert_true(hasattr(myPO, '_id'))
        self.assert_true(myPO.save())
        myPOreloaded = MyPOwithoutPK(self.env, name='Test')
        self.assert_true(myPOreloaded.exists)
        
    def testDeletePersistentObjectWithPK(self):
        """Tests the deletion of a persistent object with PK from the DB"""
        myObj = MyPO(self.env, name='Test', users=2)
        self.assert_true(myObj.save())
        # Now delete it
        self.assert_true(myObj.delete())
        myReborn = MyPO(self.env, name='Test')
        self.assert_false(myReborn.exists)
        
    def testDeletePersistentObjectWithoutPK(self):
        """Tests the deletion of a persistent object without PK from the DB"""
        myObj = MyPOwithoutPK(self.env, name='Test')
        self.assert_true(myObj.save())
        # Now delete it
        self.assert_true(myObj.delete())
    
    def testSelectPersistentObject(self):
        """Tests the select of the persistent object"""
        myObj1 = MyPO(self.env, name="Obj1", users=2)
        self.assert_true(myObj1.save())
        myObj2 = MyPO(self.env, name="Obj2", users=4)
        self.assert_true(myObj2.save())
        myObj3 = MyPO(self.env, name="Obj3", users=6)
        self.assert_true(myObj3.save())
        
        objs = MyPO.select(self.env, criteria={'name': 'Obj1'})
        self.assert_equals(len(objs), 1)
        self.assert_equals(objs[0].name, 'Obj1')
        
        objs = MyPO.select(self.env, criteria={"users": "> 3"})
        self.assert_equals(len(objs), 2)
        for obj in objs:
            self.assert_true(obj.users > 3)
        
        objs = MyPO.select(self.env)
        self.assert_equals(len(objs), 3)

    def testSelectPersistentObjectWithRelation(self):
        """Tests that the select is working on relations as well"""
        class MyRelatedPO(PersistentObject):
            class Meta(object):
                name = Field(primary_key=True)
                mypo = Relation(MyPO)

        self.assert_true(self.pom.create_table(MyRelatedPO))
        # create 2 related po so we can link one and test the
        # select
        myObj1 = MyPO(self.env, name="Obj1", users=2)
        self.assert_true(myObj1.save())
        myRObj1 = MyRelatedPO(self.env, name="RObj1", mypo=myObj1)
        self.assert_true(myRObj1.save())
        myRObj2 = MyRelatedPO(self.env, name="RObj2")
        self.assert_true(myRObj2.save())
        objs = MyRelatedPO.select(self.env, criteria={'mypo': myObj1})
        self.assert_equals(len(objs), 1)
        self.assert_equals(objs[0].name, 'RObj1')

    def testPersistentObjectUpdate(self):
        """Tests the Persistent Object Update"""
        myObj = MyPO(self.env, name="Test", users=4)
        self.assert_true(myObj.save())
        # Now update
        myObj.users = 5
        self.assert_true(myObj.save())
        # Now change the Primary Key
        myObj.name = "New Test"
        self.assert_true(myObj.save())
        # Now myObj Test should not exists anymore
        myOldObj = MyPO(self.env, name="Test")
        self.assert_false(myOldObj.exists, "Created new object instead of updating...")
        
    def checkInstanceVariableAndClassVariable(self):
        """Tests the setting and getting of instance and class variables"""
        myObj1 = MyPO(self.env, name="Test1", users=3)
        self.assert_true(myObj1.save())
        myObj2 = MyPO(self.env, name="Test2", users=6)
        self.assert_true(myObj2.save())
        self.assert_not_equals(myObj1.name, myObj2.name)
        self.assert_not_equals(myObj1.users, myObj2.users)
        
    def testSettingOfKeyFieldsToNone(self):
        """Test that the Persistent Object doesn't allow to set key or unique fields to None"""
        myObj = MyPO(self.env, name="Test", users=2)
        self.assert_true(myObj.save())
        myObj.name = None
        self.assert_not_equals(myObj.name, None)
        
    def testRelationBetweenTwoDifferentPo(self):
        """Tests the relation between 2 different POs"""
        class MyRelatedPO(PersistentObject):
            class Meta(object):
                name = Field(primary_key=True)
                mypo = Relation(MyPO)
        
        self.assert_true(self.pom.create_table(MyRelatedPO))
        
        myObj = MyPO(self.env, name="Test", users=4)
        self.assert_true(myObj.save())
        myRelObj = MyRelatedPO(self.env, name="Related Test", mypo=myObj)
        self.assert_true(myRelObj.save())
        # Test the member is still the object
        self.assert_equals(myRelObj.mypo, myObj)
        # Now reload the object from the database and check if it is an object and is the same
        myRelCopy = MyRelatedPO(self.env, name=myRelObj.name)
        self.assert_true(isinstance(myRelCopy.mypo, MyPO), "Object not converted! %s" % myRelCopy.mypo)
        self.assert_equals(myRelCopy.mypo.name, myObj.name)
        self.assert_equals(myRelCopy.mypo.users, myObj.users)
        
    def testSettingWrongTypeOnRelation(self):
        """Tests if the Relation is type safe"""
        class MyDummyPO(PersistentObject):
            class Meta(object):
                name = Field(unique=True)
        
        class MyRelatedPO(PersistentObject):
            class Meta(object):
                name = Field(primary_key=True)
                mypo = Relation(MyPO)
        
        self.assert_true(self.pom.create_table(MyDummyPO))
        self.assert_true(self.pom.create_table(MyRelatedPO))
        
        myObj = MyPO(self.env, name="Test", users=3)
        self.assert_true(myObj.save())
        self.assert_equals(myObj.name, "Test")
        self.assert_equals(myObj.users, 3)
        myRelObj = MyRelatedPO(self.env, name="Related Test", mypo=myObj)
        self.assert_true(myRelObj.save())
        # Test the member is still the object
        self.assert_equals(myRelObj.mypo, myObj)
        # Now create a dummy object and try to set the mypo
        myDummy = MyDummyPO(self.env, name="Dummy")
        self.assert_true(myDummy.save())
        self.assert_equals(myDummy.name, "Dummy")
        self.assert_not_equals(myDummy, myObj)
        myRelObj.mypo = myDummy
        self.assert_not_equals(myRelObj.mypo, myDummy)
        
    def testSettingNoneOnRelation(self):
        """Tests if the Relation is accepting None"""
        class MyRelatedPO(PersistentObject):
            class Meta(object):
                name = Field(primary_key=True)
                mypo = Relation(MyPO)
        
        self.assert_true(self.pom.create_table(MyRelatedPO))
        
        myObj = MyPO(self.env, name="Test", users=3)
        self.assert_true(myObj.save())
        myRelObj = MyRelatedPO(self.env, name="Related Test", mypo=myObj)
        self.assert_true(myRelObj.save())
        # Test the member is still the object
        self.assert_equals(myRelObj.mypo, myObj)
        # Now set None
        myRelObj.mypo = None
        self.assert_true(myRelObj.save())
        # Reload
        myRelObj = MyRelatedPO(self.env, name="Related Test")
        self.assert_equals(myRelObj.mypo, None)
    
    def testSettingNoneOnRelationWhenPKIsNumber(self):
        """Tests setting the PK as None on a relation"""
        class MyPOWithNumberId(PersistentObject):
            class Meta(object):
                id = Field(type='number', primary_key=True)
                users = Field(type='number')
        
        class MyRelatedPO(PersistentObject):
            class Meta(object):
                name = Field(primary_key=True)
                mypo = Relation(MyPOWithNumberId)
        
        self.assert_true(self.pom.create_table(MyPOWithNumberId))
        self.assert_true(self.pom.create_table(MyRelatedPO))
        
        myObj = MyPOWithNumberId(self.env, id=1, users=3)
        self.assert_true(myObj.save())
        myRelObj = MyRelatedPO(self.env, name="Related Test", mypo=myObj)
        self.assert_true(myRelObj.save())
        # Test the member is still the object
        self.assert_equals(myRelObj.mypo, myObj)
        # Now set None
        myRelObj.mypo = None
        self.assert_true(myRelObj.save())
        # Reload
        myRelObj = MyRelatedPO(self.env, name="Related Test")
        self.assert_equals(myRelObj.mypo, None)
        
    def testSelectWithNoneParameter(self):
        """Tests the select with a parameter None, also on relations"""
        class MyRelatedPO(PersistentObject):
            class Meta(object):
                name = Field(primary_key=True)
                mypo = Relation(MyPO)
        
        self.assert_true(self.pom.create_table(MyRelatedPO))
        
        myObj = MyPO(self.env, name="Test", users=3)
        self.assert_true(myObj.save())
        myRelObj = MyRelatedPO(self.env, name="Related Test", mypo=myObj)
        self.assert_true(myRelObj.save())
        
        # Select MyPO where name is None
        res = MyPO.select(self.env, criteria={'name': None})
        self.assert_equals(len(res), 0)
        
        # Select with relation None
        myRelObj.mypo = None
        self.assert_true(myRelObj.save())
        MyRelatedPO.select(self.env, criteria={'mypo': None})
    
    def testInsertEscapes(self):
        """Tests if strings containing quotes can be saved and loaded correctly."""
        description="""
                     This is a quote: ' And another "
                     And lots: '', ''', ""
                     ; drop table grades;
        """
        myObj = MyPO(self.env, name='ObjWithDesc', description=description)
        self.assert_true(myObj.save())
        myObj = MyPO(self.env, name='ObjWithDesc')
        self.assert_equals(myObj.description, description)
        
    def testPersistentObjectComparison(self):
        """Tests the compare between persistent objects"""
        myObj1 = MyPO(self.env, name="TestPOComparison", description="Test me too")
        self.assert_true(myObj1.save())
        myObj2 = MyPO(self.env, name="TestPOComparison")
        self.assert_equals(myObj1, myObj2)
        
    def testPersistentObjectRealConversion(self):
        """Tests the conversion of real to float of a Persistent Object"""
        myObj1 = MyPO(self.env, name="TestPO", amount=5.6)
        self.assert_true(myObj1.save())
        myObj2 = MyPO(self.env, name="TestPO")
        self.assert_equals(myObj1, myObj2)
        
    def _assert_po_behaves_as_expected(self, po_class):
        myPO = po_class(self.env)
        myPO.name = 'John Smith'
        myPO.foobar = 'should be ignored'
        self.assert_true(myPO.save())
        self.assert_true(myPO.exists)
        
        po = po_class(self.env, name='John Smith')
        self.assert_equals('John Smith', po.name)
        self.assert_false(hasattr(po, 'foobar'))
        self.assert_true(myPO.save())
        
        myPO.delete()
        po = po_class(self.env, name='John Smith')
        self.assert_false(po.exists)
    
    def testDifferentColumnNameInDb(self):
        """Tests that a different db name can be chosen for a column."""
        self._assert_po_behaves_as_expected(MyPO)
    
    def testDifferentColumnNameForPrimaryKeyInDb(self):
        """Tests that a different db name can be chosen for a column which is
        the primary key."""
        class MyPOKey(PersistentObject):
            class Meta(object):
                name = Field(primary_key=True, db_name='mypo_key')
                what = Field()
        self.pom.create_table(MyPOKey)
        self._assert_po_behaves_as_expected(MyPOKey)
    
    def testDifferentColumnNameForUniqueKeyInDb(self):
        """Tests that a different db name can be chosen for a column which is
        marked as unique."""
        class MyPOUnique(PersistentObject):
            class Meta(object):
                name = Field(unique=True, db_name='mypo_key')
                another = Field()
        self.pom.create_table(MyPOUnique)
        self._assert_po_behaves_as_expected(MyPOUnique)
    
    def testSelectWithDifferentColumnNameInDb(self):
        """Tests that a select on a key works even if the db column name is
        different from the Python attribute name."""
        class MyPODiffColName(PersistentObject):
            class Meta(object):
                name = Field(primary_key=True, db_name='foobar')
                
        self.assert_equals('foobar', MyPODiffColName.name.db_name)
        self.assert_true(self.pom.create_table(MyPODiffColName))
        
        myPO = MyPODiffColName(self.env)
        myPO.name = 'John Smith'
        self.assert_true(myPO.save())
        self.assert_true(myPO.exists)
        
        names = [s.name for s in MyPODiffColName.select(self.env)]
        self.assert_equals(['John Smith'], names)
    
    def testRenamePrimaryKeyWithDifferentColumnNameInDb(self):
        """Tests that the primary key can still be renamed even if the column
        name is different from the attribute name."""
        myPO = MyPO(self.env)
        myPO.name = 'John Smith'
        self.assert_true(myPO.save())
        self.assert_true(myPO.exists)
        
        myPo2 = MyPO(self.env, name='John Smith')
        myPo2.name = 'John Doe'
        myPo2.save()
        
        names = [s.name for s in MyPO.select(self.env)]
        self.assert_equals(['John Doe'], names)
        
    def testOrderByInSelectQuery(self):
        """Tests the orderby in select query"""
        for i in range(10):
            myPo = MyPO(self.env, name='test%s' % i, users=randint(0, 30))
            myPo.save()
        
        myPos = MyPO.select(self.env, order_by=['users'])
        self.assert_equals(10, len(myPos), 
                         "Found %s items instead of 10!" % len(myPos))
        
        # should be sorted ascending
        last = 0
        for myPo in myPos:
            if last == 0:
                last = myPo.users
            self.assert_true(myPo.users >= last, 
                            "Items out of order: %s !>= %s" % \
                            (myPo.users, last))
            last = myPo.users
        
        myPos = MyPO.select(self.env, order_by=['-users'])
        self.assert_equals(10, len(myPos), 
                         "Found %s items instead of 10!" % len(myPos))
        # should be sorted descending
        last = 0
        for myPo in myPos:
            if last == 0:
                last = myPo.users
            self.assert_true(myPo.users <= last, 
                            "Items out of order: %s !<= %s" % \
                            (myPo.users, last))
            last = myPo.users

    def testOrderByInSelectQueryWithDbFieldsName(self):
        """Tests the order_by in select query with specific db fields"""
        for i in range(10):
            myPo = MyPO(self.env, name='test%s' % i, users=randint(0, 30))
            myPo.save()
        
        myPos = MyPO.select(self.env, order_by=['users'])
        self.assert_equals(10, len(myPos), 
                         "Found %s items instead of 10!" % len(myPos))
        
        # should be sorted ascending
        last = 0
        for myPo in myPos:
            if last == 0:
                last = myPo.users
            self.assert_true(myPo.users >= last, 
                            "Items out of order: %s !>= %s" % \
                            (myPo.users, last))
            last = myPo.users
        
        myPos = MyPO.select(self.env, order_by=['-users'])
        self.assert_equals(10, len(myPos), 
                         "Found %s items instead of 10!" % len(myPos))
        # should be sorted descending
        last = 0
        for myPo in myPos:
            if last == 0:
                last = myPo.users
            self.assert_true(myPo.users <= last, 
                            "Items out of order: %s !<= %s" % \
                            (myPo.users, last))
            last = myPo.users

    def testLimitInPOQuery(self):
        """Tests the limit in the PersistentObject query"""
        for i in range(10):
            myPo = MyPO(self.env, name='test%s' % i, users=randint(0, 30))
            myPo.save()
        
        myPos = MyPO.select(self.env, limit=3)
        self.assert_equals(3, len(myPos), 
                         "Found %s items instead of 3!" % len(myPos))

        myPos = MyPO.select(self.env)
        self.assert_equals(10, len(myPos), 
                         "Found %s items instead of 10!" % len(myPos))

    def testNotInAndInSelectInPoQuery(self):
        """Tests the criteria 'in' and 'not in' a list of values"""
        some_pos = list()
        for i in range(10):
            myPo = MyPO(self.env, name='test%s' % i, users=i)
            myPo.save()
            if i % 2:
                some_pos.append(myPo.users)
        
        all_pos = MyPO.select(self.env)
        self.assert_equals(10, len(all_pos))
        # Now make a query and get all the Pos which are not included in the list
        in_pos = MyPO.select(self.env, criteria={'users': 'in %s' % some_pos})
        self.assert_equals(len(some_pos), len(in_pos))
        # negative
        not_pos = MyPO.select(self.env, criteria={'users': 'not in %s' % some_pos})
        self.assert_equals(10 - len(some_pos), len(not_pos))
        
        # now try with stings
        class MyStrPO(PersistentObject):
            class Meta(object):
                name = Field(primary_key=True) # , db_name='foobar'
        
        self.assert_true(self.pom.create_table(MyStrPO))
        
        some_pos = list()
        for i in range(10):
            myPo = MyStrPO(self.env, name='test%s' % i)
            myPo.save()
            if i % 2:
                some_pos.append(myPo.name)
        
        all_pos = MyStrPO.select(self.env)
        self.assert_equals(10, len(all_pos))
        # Now make a query and get all the Pos which are not included in the list
        in_pos = MyStrPO.select(self.env, criteria={'name': 'in %s' % some_pos})
        self.assert_equals(len(some_pos), len(in_pos))
        # negative
        not_pos = MyStrPO.select(self.env, criteria={'name': 'not in %s' % some_pos})
        self.assert_equals(10 - len(some_pos), len(not_pos))
    
    def testPODoesNotLoadFromDatabaseIfNoKeyGiven(self):
        class MyPO(PersistentObject):
            class Meta(object):
                name = Field(primary_key=True)
        # Check that name=None is the same as no name parameter given
        po = MyPO(self.env, name=None)
        self.assert_false(po.exists)

    def testAsDictUtilityMethod(self):
        """
        Tests the as_dict to transform a PersistentObject into plain
        Python Object
        """
        class MyPO2(PersistentObject):
            class Meta(object):
                name = Field(unique=True)
                prop2 = Relation(MyPO)
        
        self.assert_true(self.pom.create_table(MyPO2))
        
        myPO = MyPO(self.env, name='TestPO', users=2)
        myPO.save()
        myPO2 = MyPO2(self.env, name='testDictPO', prop2=myPO)
        myPO2.save()
        
        po2_dict = myPO2.as_dict()
        self.assert_equals('testDictPO', po2_dict['name'])
        self.assert_equals(myPO.as_dict(), po2_dict['prop2'])
        po_dict = myPO.as_dict()
        self.assert_equals('TestPO', po_dict['name'])
        self.assert_equals(2, po_dict['users'])
    
    def test_as_dict_does_not_change_source_object_lists(self):
        source = MyPO(self.env)
        source.foo = [MyPO(self.env)]
        source.as_dict()
        self.assert_equals(MyPO, type(source.foo[0]))
    
    
    def testDBConvertingData(self):
        """Tests the DB layer converting data of its own."""
        class MyTestPo(PersistentObject):
            class Meta:
                value0 = Field(unique=True)
                value1 = Field(type="real")
                value2 = Field(type="integer")
                value3 = Field()
        
        self.pom.create_table(MyTestPo)
        
        myt = MyTestPo(self.env, value0='TestConversion')
        self.assert_true(myt.save())
        self.assert_none(myt.value1)
        self.assert_none(myt.value2)
        self.assert_none(myt.value3)
        self.assert_none(myt._get_value_of_field(MyTestPo.value1.field, myt))
        self.assert_none(myt._get_value_of_field(MyTestPo.value2.field, myt))
        self.assert_none(myt._get_value_of_field(MyTestPo.value3.field, myt))
        
        # check what is into the DB
        db = self.env.get_db_cnx()
        cursor = db.cursor()
        cursor.execute('SELECT value1,value2,value3 FROM %s WHERE _id=%s' % \
                       (MyTestPo._table.name, myt._id))
        row = cursor.fetchone()
        self.assert_none(row[0])
        self.assert_none(row[1])
        self.assert_none(row[2])
        
        # Now see what comes back from the DB
        myt1 = MyTestPo(self.env, value0='TestConversion')
        self.assert_none(myt1._get_value_of_field(MyTestPo.value1.field, myt1))
        self.assert_none(myt1._get_value_of_field(MyTestPo.value2.field, myt1))
        self.assert_none(myt1._get_value_of_field(MyTestPo.value3.field, myt1))
        self.assert_none(myt1.value1)
        self.assert_none(myt1.value2)
        self.assert_none(myt1.value3)
    
    def testPODateTimeIsSavedAsUTC(self):
        # Actually we don't have to implement any code - trac stores datetime
        # internally always UTC as already.
        class MyDatetimePO(PersistentObject):
            class Meta(object):
                id = Field(primary_key=True, type='integer')
                start = Field(type='datetime')
        self.pom.create_table(MyDatetimePO)
        
        pdt = FixedOffset(-7*60, 'PDT')
        start = datetime(2008, 10, 4, 12, 42, tzinfo=pdt)
        # utc_timestamp = 1223149320
        
        po = MyDatetimePO(self.env, id=1, start=start)
        po.save()
        
        another_po = MyDatetimePO(self.env, id=1)
        self.assert_equals(start.astimezone(utc), another_po.start)
    
    def testOldValuesAreSetPerInstance(self):
        """This is a bugfix test to check that the _old values for persistent
        objects are set per instance and not on a class level."""
        class MyPOWithOld(PersistentObject):
            class Meta(object):
                name = Field(primary_key=True)
        
        env = self.teh.get_env()
        PersistentObjectManager(env).create_table(MyPOWithOld)
        
        obj1 = MyPOWithOld(env, name='foo')
        obj1.save()
        
        obj2 = MyPOWithOld(env, name='bar')
        obj2.save()
        
        obj2.name = 'baz'
        self.assert_equals({'name': 'bar'}, obj2._old)
        self.assert_false(obj1._changed)
    
    def testCanSelectWithCriteriaNone(self):
        """This is a bugfix test to check that the _old values for persistent
        objects are set per instance and not on a class level."""
        class MyPOWithNone(PersistentObject):
            class Meta(object):
                name = Field(primary_key=True)
                value = Field()
        
        PersistentObjectManager(self.env).create_table(MyPOWithNone)
        
        obj1 = MyPOWithNone(self.env, name='foo')
        obj1.save()
        
        results = obj1.select(self.env, criteria={'value': None})
        self.assert_equals(1, len(results))
    
    def testRaiseExceptionIfUnknownFieldIsUsedInConstructor(self):
        self.assert_raises(TypeError, MyPO, self.env, invalid_field='foo')
    
    def testRaiseExceptionIfWrongTypeForPrimaryKeyIsUsed(self):
        class FakeSprint(PersistentObject):
            class Meta(object):
                sprint = Field(primary_key=True)
        
        class FakeContingent(PersistentObject):
            class Meta(object):
                name = Field(primary_key=True)
                sprint = Relation(FakeSprint, db_name='sprint', primary_key=True)
        
        PersistentObjectManager(self.env).create_table(FakeSprint)
        PersistentObjectManager(self.env).create_table(FakeContingent)
        FakeSprint(self.env, sprint='Alpha').save()
        self.assert_raises(Exception, FakeContingent, self.env, name='bugs', sprint='Alpha')
    
    def test_can_support_autoincrement(self):
        class AutoIncrementPrimaryKeyClass(PersistentObject):
            class Meta(object):
                id = Field(primary_key=True, auto_increment=True)
                name = Field()
        
        PersistentObjectManager(self.env).create_table(AutoIncrementPrimaryKeyClass)
        first = AutoIncrementPrimaryKeyClass(self.env)
        self.assert_none(first.id)
        first.save()
        self.assert_not_none(first.id)
        
        second = AutoIncrementPrimaryKeyClass(self.env)
        second.save()
        self.assert_equals(first.id + 1, second.id)
    
    def test_can_delete_items_with_id_field(self):
        class AutoIncrementPrimaryKeyClass(PersistentObject):
            class Meta(object):
                id = Field(primary_key=True, auto_increment=True)
                name = Field()
        
        PersistentObjectManager(self.env).create_table(AutoIncrementPrimaryKeyClass)
        first = AutoIncrementPrimaryKeyClass(self.env)
        first.save()
        
        first.delete()
    
    def test__old_is_initialized_correctly_on_load_if_init_sets_a_default_value(self):
        class InitializerSetsDefault(PersistentObject):
            class Meta(object):
                scope = Field(primary_key=True)
            
            def __init__(self, env, scope='global', **kwargs):
                # simple_super can not cope with keyword arguments as Python
                # provides no means to find out the difference between
                # (**[]) and () so we have an explicit call here.
                self.super(env, scope=scope, **kwargs)
            
        PersistentObjectManager(self.env).create_table(InitializerSetsDefault)
        first = InitializerSetsDefault(self.env, scope="Foo")
        first.save()
        
        found_objects = InitializerSetsDefault.select(self.env)
        self.assert_length(1, found_objects)
        self.assert_equals(dict(scope='Foo'), found_objects[0]._old)
    
    def test__old_is_initialized_on_select(self):
        first = MyPO(self.env, name='foo')
        first.save()
        
        results = MyPOModelManager(self.env).select(criteria=dict(name='foo'))
        self.assert_length(1, results)
        first = results[0]
        self.assert_contains('name', first._old)
    
    def test_will_throw_if_save_doesnt_affect_any_rows(self):
        first = MyPO(self.env, name="foo")
        first.save()
        first.name = 'bar'
        first._old['name'] = 'bar' # this should generate wrong WHERE clause on saving
        exception = self.assert_raises(UnableToSaveObjectError, first.save)
        self.assert_true(r'0 rows affected' in exception_to_unicode(exception))

    def test_will_save_if_setting_attribute_twice(self):
        mypo = MyPO(self.env, name='bar')
        mypo.save()
        mypo.users = 3
        mypo.users = 1
        mypo.save()
        self.assert_equals(1, mypo.users)

    def test_will_revert_value_if_fail_to_save(self):
        mypo = MyPO(self.env, name='foo', amount=1.0)
        mypo.save()
        mypo.amount = 1.2
        # set a value that will generate a failure
        mypo.name = dict()
        self.assert_raises(Exception, mypo.save)
        # reset to original value after failed save
        self.assert_equals(1.0, mypo.amount)
    
    def test_insert_omits_autoincrement_column(self):
        class AutoIncrementPrimaryKeyClass(PersistentObject):
            class Meta(object):
                id = Field(primary_key=True, auto_increment=True)
                name = Field()
        
        PersistentObjectManager(self.env).create_table(AutoIncrementPrimaryKeyClass)
        first = AutoIncrementPrimaryKeyClass(self.env)
        
        sql, parameters = first._sql_and_parameters_for_insert()
        expected_sql = 'INSERT INTO agilo_auto_increment_primary_key_class (name) VALUES (%(name)s)'
        self.assert_equals(expected_sql, sql)
        # parameters contains id as well but that does not cause any problems
        # safe_execute filters it out (very likely)
        self.assert_contains('name', parameters)


class PersistentObjectModelManagerTest(AgiloTestCase):

    def setUp(self):
        self.super()
        self.pom = PersistentObjectManager(self.env)
        #FIXME: I don't know why, but putting the test to check if the table
        # is created, after a while gives error. I didn't have the chance to
        # check it through, but I guess it is related to the :memory: db that
        # SQLite reallocate in the same position, so the new Env (which has
        # a different Python id) is till pointing to the old InMemoryDatabase
        self.pom.create_table(MyPO)
        self.assert_true(self.pom.create_table(MyPOwithoutPK))
        self.pomm = MyPOModelManager(self.env)

    def test_model_manager_can_create_objects(self):
        mypo = self.pomm.create(name='testPO', description='test', amount=2.0, users=1)
        self.assert_not_none(mypo)
        self.assert_true(mypo.exists)
        self.assert_equals('testPO', mypo.name)
        self.assert_equals('test', mypo.description)
        self.assert_equals(2.0, mypo.amount)
        self.assert_equals(1, mypo.users)

    def test_model_manager_can_select_objects(self):
        mypos = self.pomm.select()
        self.assert_length(0, mypos)
        # now create 2
        mypo1 = self.pomm.create(name='testPO1', description='test', amount=2.0, users=1)
        mypo2 = self.pomm.create(name='testPO2', description='test', amount=1.0, users=2)
        mypos = self.pomm.select()
        self.assert_length(2, mypos)
        self.assert_contains(mypo1, mypos)
        self.assert_contains(mypo2, mypos)

    def test_model_manager_select_uses_cache(self):
        mypo1 = self.pomm.create(name='testPO1', description='test', amount=2.0, users=1)
        mypos = self.pomm.select()
        self.assert_contains(mypo1, mypos)
        # the select loads another object instance from the db
        self.assert_not_equals(id(mypo1), id(mypos[0]))
        # now the get should get the same object from the cache
        another_mypo1 = self.pomm.get(name=mypo1.name)
        self.assert_equals(id(mypos[0]), id(another_mypo1))

    def test_can_force_load_from_db(self):
        mypo = self.pomm.create(name='loaded')
        reloaded = self.pomm.get(name='loaded', load=True)
        self.assert_equals(mypo, reloaded)
        self.assert_not_equals(id(mypo), id(reloaded))

    def test_can_save_twice_the_same_object(self):
        mypo = self.pomm.create(name='mypo', description='po', amount=2.0, users=0)
        mypo.amount = 1.0
        self.pomm.save(mypo)
        mypo = self.pomm.get(name=mypo.name, load=True)
        self.assert_equals(1.0, mypo.amount)
        mypo.amount = 3.0
        self.pomm.save(mypo)
        mypo = self.pomm.get(name=mypo.name, load=True)
        self.assert_equals(3.0, mypo.amount)


if __name__ == '__main__':
    from agilo.test.testfinder import run_unit_tests
    run_unit_tests(__file__)
