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
#   Authors: 
#       - Andrea Tomasini <andrea.tomasini_at_agile42.com>


from trac.resource import Resource

from agilo.core import PersistentObject, Field, Relation,\
    PersistentObjectModelManager
from agilo.utils import Key, Realm
from agilo.scrum.sprint import Sprint


class Contingent(PersistentObject):
    """
    Represent an amount of time that is collectively used by resources during
    a Sprint. It may be allocated at the beginning of a sprint as time or as
    percentage of the capacity of that Sprint. TeamMembers should be allowed
    to book time on the contingent and increase the actual time until reaching
    the amount defined, at which point an alarm should be risen.
    """
    class Meta(object):
        name = Field(primary_key=True)
        sprint = Relation(Sprint, primary_key=True, db_name='sprint')
        amount = Field(type='real')
        actual = Field(type='real')
    
    class ExceededException(Exception):
        """Raised when the contingent is exceeded, contains the amount exceeding"""
        def __init__(self, amount=None, *args, **kwargs):
            Exception.__init__(self, *args, **kwargs)
            self.amount = amount
    
    class UnderflowException(Exception):
        "Raised when the actual ('used') time would be decreased below zero."
        pass
    
    def __init__(self, env, percent=None, **kwargs):
        """
        Add the possibility to create the amount as percentage of the
        Sprint capacity
        """
        super(Contingent, self).__init__(env, **kwargs)
        if percent is not None and Key.SPRINT in kwargs:
            try:
                percent = float(percent)
            except ValueError:
                pass # Not a number?
            if isinstance(percent, float) and percent > 0 and \
                    self.sprint is not None and self.sprint.team is not None:
                self.amount = self.sprint.get_capacity_hours() / 100 * percent
        if self.actual is None:
            self.actual = 0
        # Sets the resource
        self.resource = Resource(Realm.CONTINGENT, self.name)
        
    def add_time(self, delta):
        """
        Add the given delta to the actual used amount and raises a 
        Contingent.ExceededException when this value would use excess the stored
        amount.
        Returns the remaining to reach the amount (or None if the actual time 
        was not changed).
        """
        try:
            delta = float(delta)
        except:
            return
        if self.sprint is None or self.sprint.team is None:
            return
        if self.actual + delta < 0:
            raise Contingent.UnderflowException()
        exceeded = (self.actual + delta) - self.amount
        if exceeded > 0:
            raise Contingent.ExceededException(amount=exceeded)
        self.actual += delta
        return -exceeded
    
    def is_warning(self):
        try:
            return self.actual / self.amount > 0.7
        except ZeroDivisionError:
            return False
    
    def is_critical(self):
        try:
            return self.actual / self.amount > 0.9
        except ZeroDivisionError:
            return False


class ContingentModelManager(PersistentObjectModelManager):
    """Model Manager for the Contingent objects"""
    model = Contingent
