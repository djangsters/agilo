#   Copyright 2007 Andrea Tomasini <andrea.tomasini__at__agile42.com>
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
#   Authors:
#        - Andrea Tomasini <andrea.tomasini__at__agile42.com>
"""
Module containing all the API definitions to manipulate Models in Agilo.
Models are Python Objects that can be persisted, Agilo has defined its own
PersistentObject and uses it as middleware for DB related operations
"""

from trac.core import Interface


__all__ = ["IModelCache", "IModelManager", "SimpleModelCache"]


class IModelCache(object):
    """
    Interface to represent a ModelCache, used by the ModelManagers to get
    objects which have already been loaded from the DB, or to implement
    specific Caching policies.
    """
    def get(self, key_instance):
        """
        Get the Model uniquely identified by the given parameters from the cache
        and returns it. Returns None if the Model is not cached.
        """
        raise NotImplementedError("get should be implemented in any subclass!")
        
    def set(self, key_instance, model_instance):
        """
        Set the Model instance into the cache for further usage. The caching
        policy is delegated to the implementation.
        """
        raise NotImplementedError("set should be implemented in any subclass!")
    
    def invalidate(self, key_instance=None, model_instance=None):
        """
        Invalidate the cache for this Model, if the key_instance or model_instance
        are passed only that model will be deleted, otherwise the whole content
        should be dropped.
        """
        raise NotImplementedError("invalidate should be implemented in any subclass!")


class SimpleModelCache(IModelCache):
    """
    Simple implementation of IModelCache, using a dictionary for internal 
    storage. Objects are cached in memory and the key_instance is used as
    dictionary key to locate them.
    """
    def __init__(self):
        self._cache = dict()
    
    def __repr__(self):
        return self.__class__.__name__ + ":" + repr(self._cache)
    
    def _get_cache_key(self, key_instance):
        """
        Returns a cache key given a key_instance, that can be a complete
        key, or only a part of it
        """
        assert isinstance(key_instance, tuple), "The key_instance is wrong: %s" % key_instance
        # at: a key_instance is a touple containing as a fisrt element
        # the primary key of a PersistentObject, and as additional
        # elements unique constraint for that model instance. It is
        # needed to index an object with all the parameters, cause it
        # can be retrieved using different keys. 
        if not isinstance(key_instance, tuple):
            # We assume someone tried to send the primary key directly
            key_instance = (key_instance, None)
        
        # try full shot
        if self._cache.has_key(key_instance):
            return key_instance
        # is a part of a key separate the
        # elements keys and unique constraints
        pk, constraints = key_instance
        for cache_key in self._cache:
            # check with the pk first
            if pk and pk == cache_key[0]:
                return cache_key
            # no pk found look in the constraint, are all unique
            # so it should be enough to have one, it works also with
            # unique together as a tuple
            elif constraints:
                for key_piece in constraints:
                    if key_piece:
                        if (key_piece not in cache_key[1]):
                            break
                        else:
                            return cache_key
    
    def _get_cache_key_from_model(self, model_instance):
        """
        Returns the cache key corresponding to the given model instance, if
        cached, otherwise return None
        """
        if model_instance:
            for cache_key, value in self._cache.items():
                # object identity should suffice, the goal of the cache is to
                # keep it unique
                if value == model_instance:
                    return cache_key
        return None
    
    def get(self, key_instance):
        return self._cache.get(self._get_cache_key(key_instance))
    
    def set(self, key_instance, model_instance):
        self._cache[key_instance] = model_instance
    
    def invalidate(self, key_instance=None, model_instance=None):
        assert not key_instance or isinstance(key_instance, tuple), \
            "The key_instance must be a valid cache key, got a: %s" \
            % key_instance
        from agilo.core import PersistentObject
        from agilo.ticket.model import AgiloTicket
        from agilo.scrum.backlog import Backlog
        assert not model_instance or \
            isinstance(model_instance, (PersistentObject, AgiloTicket, Backlog)), \
            "The model_instance must be a PersistentObject, or AgiloTicket not: %s" \
            % model_instance
        
        if key_instance:
            return self._cache.pop(self._get_cache_key(key_instance), None)
        elif model_instance:
            return self._cache.pop(self._get_cache_key_from_model(model_instance), None)
        else:
            self._cache = dict()
            return None


class IModelManager(Interface):
    """
    Interface to represent a Model Manager, a Component implementing this 
    interface will take care of managing a specific Model Type. A Model can
    be a PersistentObject or another type of object, the manager has to take
    care that the Model is loaded, persisted and cached.
    """
    def for_model(self):
        """
        Must return the class object of the Model that this Manager is 
        managing
        """
    
    def get(self, **kwargs):
        """
        Must return a specific Model instance, given the needed parameters to
        initialize it or to uniquely identify it and load it. the key parameter
        must be a unique
        """
    
    def create(self, **kwargs):
        """
        Must create a new instance of the model and return it. Depending on the
        Model type it might be required to pass an arbitrary number of 
        parameters to create the object. It returns the new object instance
        """
    
    def delete(self, model_instance, **kwargs):
        """
        Must delete the given instance from the database. The Manager should take
        care about the cache too, and use specific extra parameters if needed
        """
    
    def save(self, model_instance, **kwargs):
        """
        Must save and persist the model, in case of error rise an exception.
        """
        
    def select(self, criteria=None, order_by=None, limit=None):
        """
        Must return a list of models matching the query criteria. Criteria 
        should be a dictionary with with key: value pairs.
        """
    
    def get_cache(self):
        """
        Returns an instance of the IModelCache set to manage caching for this
        Model type
        """
