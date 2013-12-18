# -*- encoding: utf-8 -*-
#   Copyright 2008 Agile42 GmbH, Berlin (Germany)
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
#       - Sebastian Schulze <sebastian.schulze__at__agile42.com>
#       - Jonas von Poser jonas.vonposer__at__agile42.com>

from agilo.core import PersistentObject, Field, Relation,\
    PersistentObjectModelManager
# We need the 'Team' for the TeamMetricsEntry meta class so it's okay to import 
# that directly. I did not export this symbol via agilo.scrum.team consciously
# so that others don't use it directly.
from agilo.scrum.team.model import Team
from agilo.scrum.sprint.model import Sprint

__all__ = ['TeamMetrics']


class TeamMetrics(object):
    """This class is a wrapper for all Team related metrics."""
    class TeamMetricsEntry(PersistentObject):
        class Meta(object):
            team = Relation(Team, primary_key=True, db_name='team')
            sprint = Relation(Sprint, primary_key=True, db_name='sprint')
            # in MySQL 'key' is a reserved word
            key = Field(primary_key=True, db_name='metrics_key')
            value = Field(type='real')
    
    def __init__(self, env, sprint, team=None, properties=None, db=None):
        """Initializes a new TeamMetrics objects related to the given
        Team and Sprint."""
        assert sprint != None, "Parameter 'sprint' must not be None"
        assert team or sprint.team, "Parameter 'team' must not be None"
        self.env = env
        self.tme_manager = TeamMetricsEntryModelManager(self.env)
        self.sprint = sprint
        self.team = team or sprint.team
        self._properties = {}
        if properties is not None:
            self._properties = properties
        self._load()

    def __getitem__(self, attr):
        """
        Gets the local metric attribute (attr) value and returns it
        """
        if attr in self._properties:
            return self._properties[attr]
        return None

    def __setitem__(self, attr, value):
        """Sets the local metric attribute (attr) value to value"""
        self._properties[attr] = value

    def __delitem__(self, attr):
        """Deletes the local metric value (attr)"""
        if attr in self._properties:
            del self._properties[attr]
            entry = self.tme_manager.select(
                criteria={'sprint': self.sprint, 'team':self.team, 'key':attr})
            if entry:
                entry[0].delete()

    # Iterator methods, to retrieve all keys in the Metrics object
    def __iter__(self):
        """Returns the iterator"""
        for p in self._properties.keys():
            yield p

    def keys(self):
        return self._properties.keys()

    def _load(self, db=None):
        """
        loads the TeamMetrics from the database into the local properties dict
        """
        models = self.tme_manager.select(criteria={'sprint': self.sprint, 
                                                          'team': self.team})
        for tm in models:
            self._properties[tm.key] = tm.value
        
    def save(self, db=None):
        """saves the object to the database"""
        for k, v in self._properties.items():
            metric = self.tme_manager.get(sprint=self.sprint,
                                          team=self.team, key=k, db=db)
            if not metric:
                metric = self.tme_manager.create(sprint=self.sprint,
                                                 team=self.team, key=k, db=db)
            metric.value = v
            metric.save()
        return True
    
    def as_dict(self):
        return self._properties.copy()


class TeamMetricsEntryModelManager(PersistentObjectModelManager):
    """Model Manager to manage the TeamMetricsEntry object"""
    model = TeamMetrics.TeamMetricsEntry
    
