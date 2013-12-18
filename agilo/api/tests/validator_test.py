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

from trac.util.datefmt import utc

from agilo.api import validator
from agilo.test import AgiloTestCase
from agilo.utils.days_time import now


class ValidatorTest(AgiloTestCase):
    """Tests the validator API"""
    
    def testNoValidator(self):
        """Tests the NoValidator"""
        val = validator.NoValidator(None)
        self.assert_equals(3, val.validate(3))
        self.assert_equals('test', val.validate('test'))

    def testStringValidator(self):
        """Tests the StringValidator"""
        val = validator.StringValidator(None)
        self.assert_equals('test', val.validate('test'))
        self.assert_raises(validator.ValidationError, val.validate, 3)
        # should allow None, it is not Mandatory
        self.assert_none(val.validate(None))
        
    def testDictValidator(self):
        """Tests the DictValidator"""
        val = validator.DictValidator(None)
        self.assert_equals({}, val.validate({}))
        self.assert_raises(validator.ValidationError, val.validate, '')
        # should allow None, it is not Mandatory
        self.assert_none(val.validate(None))
        
    def testIterableValidator(self):
        """Tests the IterableValidator"""
        val = validator.IterableValidator(None)
        self.assert_equals([], val.validate([]))
        self.assert_equals((), val.validate(()))
        self.assert_equals({}, val.validate({}))
        self.assert_raises(validator.ValidationError, val.validate, 3)
        # should allow None, it is not Mandatory
        self.assert_none(val.validate(None))
        
    def testIntValidator(self):
        """Tests the IntValidator"""
        val = validator.IntValidator(None)
        self.assert_equals(3, val.validate(3))
        # tests conversion too
        self.assert_equals(2, val.validate('2'))
        self.assert_raises(validator.ValidationError, val.validate, '')
        # should allow None, it is not Mandatory
        self.assert_none(val.validate(None))
        
    def testIntOrFloatValidator(self):
        """Tests the IntOrFloatValidator"""
        val = validator.IntOrFloatValidator(None)
        self.assert_equals(3, val.validate(3))
        self.assert_equals(3.5, val.validate(3.5))
        # tests conversion too
        self.assert_equals(2, val.validate('2'))
        self.assert_equals(2.1, val.validate('2.1'))
        self.assert_raises(validator.ValidationError, val.validate, '')
        # should allow None, it is not Mandatory
        self.assert_none(val.validate(None))
        
    def testBoolValidator(self):
        """Tests the BoolValidator"""
        val = validator.BoolValidator(None)
        self.assert_true(val.validate(True))
        self.assert_false(val.validate(False))
        self.assert_raises(validator.ValidationError, val.validate, '')
        self.assert_raises(validator.ValidationError, val.validate, 0)
        # should allow None, it is not Mandatory
        self.assert_none(val.validate(None))
        
    def testUTCDatetimeValidator(self):
        """Tests the UTCDatetimeValidator"""
        val = validator.UTCDatetimeValidator(None)
        utc_now = now(tz=utc)
        self.assert_equals(utc_now, val.validate(utc_now))
        # No UTC datetime
        self.assert_raises(validator.ValidationError, val.validate, now())
        # No datetime
        self.assert_raises(validator.ValidationError, val.validate, 0)
        # should allow None, it is not Mandatory
        self.assert_none(val.validate(None))
        
    def testMandatoryValidator(self):
        """Tests the MandatoryValidator"""
        val = validator.MandatoryValidator(None)
        self.assert_equals(1, val.validate(1))
        self.assert_equals('test', val.validate('test'))
        self.assert_raises(validator.ValidationError, val.validate, None)
        
    def testMandatoryStringValidator(self):
        """Tests the MandatoryStringValidator"""
        val = validator.MandatoryStringValidator(None)
        self.assert_raises(validator.ValidationError, val.validate, 
                          None)
        self.assert_equals('test', val.validate('test'))
        self.assert_raises(validator.ValidationError, val.validate, 1)
        
    def testMandatoryTicketValidator(self):
        """Tests the MandatoryTicketValidator"""
        val = validator.MandatoryTicketValidator(None)
        val._set_env(self.teh.get_env())
        ticket = self.teh.create_ticket('task')
        self.assert_equals(ticket, val.validate(ticket.id))
        self.assert_raises(validator.ValidationError, val.validate, 1652)
        self.assert_raises(validator.ValidationError, val.validate, None)


class ValidatorTestCase(AgiloTestCase):
    
    def init_validator(self, validator):
        self.validator = validator
        self.validator._set_env(self.env)
    
    def validate(self, *args, **kwargs):
        return self.validator.validate(*args, **kwargs)
    
    def assert_error(self, *args, **kwargs):
        self.assert_raises(validator.ValidationError, self.validate, *args, **kwargs)


class MandatorySprintValidatorTest(ValidatorTestCase):
    def setUp(self):
        self.super()
        self.init_validator(validator.MandatorySprintValidator(None))
        self.sprint = self.teh.create_sprint('test')
    
    def test_accept_valid_sprint_names(self):
        self.assert_equals(self.sprint, self.validate('test'))
    
    def test_reject_invalid_names(self):
        self.assert_error('none')
        self.assert_error(None)
        self.assert_error("")
    
    def test_accept_serialized_sprint_in_value_object(self):
        self.assert_equals(self.sprint, self.validate(self.sprint.as_dict()))


class MandatorySprintOrStringValidatorTest(ValidatorTestCase):
    def setUp(self):
        self.super()
        self.init_validator(validator.MandatorySprintOrStringValidator(None))
        self.sprint = self.teh.create_sprint('test')
    
    def testCanValidateSprints(self):
        self.assert_equals(self.sprint, self.validate('test'))
    
    def testReturnStringIfNoSuchSprintFound(self):
        self.assert_equals('fnord', self.validate('fnord'))


class SprintNameValidatorTest(ValidatorTestCase):
    def setUp(self):
        self.super()
        self.init_validator(validator.SprintNameValidator(None))
    
    def test_accepts_simple_sprint_names(self):
        self.assert_equals('fnord', self.validate('fnord'))
        self.assert_equals('a&b', self.validate('a&b'))
    
    def test_reject_slash_in_sprint_name(self):
        self.assert_raises(validator.ValidationError, self.validate, 'foo/bar')

class NonExistantSprintNameValidatorTest(ValidatorTestCase):
    def setUp(self):
        self.super()
        self.init_validator(validator.NonExistantSprintNameValidator(None))

    def test_accepts_non_existing_sprint(self):
        self.assert_equals('fnord', self.validate('fnord'))
    
    def test_reject_existing_sprint(self):
        self.sprint = self.teh.create_sprint('existing_sprint')
        self.assert_raises(validator.ValidationError, self.validate, 'existing_sprint')

    def test_reject_bad_sprint_name(self):
        self.assert_raises(validator.ValidationError, self.validate, 'bad/name')

    def test_reject_empty_sprint_name(self):
        self.assert_error("")
        self.assert_error(None)

class TeamValidatorTest(ValidatorTestCase):
    def setUp(self):
        super(TeamValidatorTest, self).setUp()
        self.init_validator(validator.TeamValidator(None))
        self.team = self.teh.create_team('Foo')
    
    def testTeamValidatorAcceptsSerializedTeamInValueObject(self):
        self.assert_equals(self.team, self.validate(self.team.as_dict()))


class IterableIntValidatorTest(ValidatorTestCase):
    def setUp(self):
        self.super()
        self.init_validator(validator.MandatoryIterableIntValidator(''))
    
    def test_can_validate_int_list(self):
        self.assert_equals((1, 2, 3), self.validate(['1', 2, '3']))
    
    def test_rejects_non_integer_values_in_list(self):
        self.assert_error("fnord")
        self.assert_error(["fnord"])
        self.assert_error("12345")
        self.assert_error([None])
        self.assert_error(None)


if __name__ == '__main__':
    from agilo.test.testfinder import run_unit_tests
    run_unit_tests(__file__)

