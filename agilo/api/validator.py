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
Module containing all the API needed to build a validator. Validator
are simple objects which allow to validate a given parameter against
some specific rules. Validator can be instantiated and reused inside
ICommand or IView.
"""
from datetime import datetime, timedelta

from trac.env import Environment

from agilo.utils.compat import exception_to_unicode
from agilo.utils.simple_super import SuperProxy


class ValidationError(Exception):
    """Represent a Validation error"""
    def __init__(self, *args, **kwargs):
        """Set the attribute passed to create the command in the 
        exception"""
        validation_params = ('param', 'value')
        for arg in validation_params:
            if kwargs.has_key(arg):
                setattr(self, arg, kwargs[arg])
                del kwargs[arg]
        # Python 2.4 compatibility, Exception is an old style class
        Exception.__init__(self, *args, **kwargs)


class IValidator(object):
    """Represent a Validator Interface. The environment is needed to
    be able o check the validity of primary key based types."""
    
    super = SuperProxy()
    
    def __init__(self, param):
        self.param = param
        self.env = None
        self.message = "Invalid Parameter (%s): " % param
    
    def _set_env(self, env):
        """Sets the environment, used before validation, must be 
        called before validating a Model Type"""
        assert isinstance(env, Environment), \
            "You must provide a trac environment! (%s)" % env
        self.env = env
        
    def validate(self, value):
        """Must raise a ValidationError with message, param, value in
        case the validation fails"""
        return value
    
    def error(self, value):
        """Raise a Validation error when called setting message, and
        other parameters"""
        raise ValidationError(self.message, param=self.param, 
                              value=value)
        
######################################################################
# VALIDATORS TO BE USED IN COMMANDS OR VIEWS
######################################################################
class NoValidator(IValidator):
    """Just calls the superclass and leave the value as is"""
    pass


class StringValidator(IValidator):
    """Checks that the param is a valid string value"""
    def validate(self, value, empty=True):
        if value:
            if not isinstance(value, basestring):
                self.message = "must be a valid string"
                self.error(value)
        elif not empty:
            self.error(value)
        return value


class DictValidator(IValidator):
    """Checks that the value is a dictionary type"""
    def validate(self, value):
        if value is not None and not isinstance(value, dict):
            self.message = "must be a valid dictionary"
            self.error(value)
        else:
            return value


class IterableValidator(IValidator):
    """Checks that the value is a list type"""
    def validate(self, value):
        if value is not None and not hasattr(value, '__iter__'):
            self.message = "must be an iterable type"
            self.error(value)
        else:
            return value


class IntValidator(IValidator):
    """Checks that the value is an int type or convertible to int"""
    def validate(self, value):
        if value is not None and not isinstance(value, int):
            try:
                # we try to convert
                value = int(value)
            except ValueError:
                self.message = "must be a valid integer"
                self.error(value)
        return value


class MandatoryIterableIntValidator(IterableValidator):
    """As the superclass, but only ints"""
    def validate(self, value):
        values = super(MandatoryIterableIntValidator, self).validate(value)
        try:
            return tuple(map(int, values))
        except Exception:
            self.message = "must all be valid integers"
            self.error(value)


class IntOrFloatValidator(IValidator):
    """Checks that the value is a int, float or convertible"""
    def validate(self, value):
        if value is not None and not isinstance(value, (int, float)):
            try:
                value = int(value)
            except ValueError:
                try:
                    value = float(value)
                except ValueError:
                    self.message = "must be a integer or a float"
                    self.error(value)
        return value


class BoolValidator(IValidator):
    """Checks that the value is a bool type"""
    def validate(self, value):
        if value is not None and not isinstance(value, bool):
            self.message = "must be a valid boolean"
            self.error(value)
        return value


class UTCDatetimeValidator(IValidator):
    """Checks that the value is a valid datetime in UTC timezone"""
    def validate(self, value):
        if value is not None and (not isinstance(value, datetime) or \
                value.utcoffset() != timedelta(0)):
            self.message = "must be a UTC datetime"
            self.error(value)
        else:
            return value

# Mandatory Validators

class MandatoryValidator(IValidator):
    """Checks if the param exists, so it is not None the value"""
    def validate(self, value):
        if value is None:
            self.message = "is mandatory, can't be None"
            self.error(value)
        else:
            return value


class MandatoryStringValidator(MandatoryValidator, StringValidator):
    """Checks that the param exists and is a valid string"""
    def validate(self, value):
        # We don't need to catch the value of the Mandatory validator
        MandatoryValidator.validate(self, value)
        # Being mandatory we won't accept empty strings
        return StringValidator.validate(self, value, empty=False)


class MandatoryIntValidator(MandatoryValidator,
                            IntValidator):
    """Checks that the value is an integer"""
    def validate(self, value):
        # We don't need to catch the value of the Mandatory validator
        MandatoryValidator.validate(self, value)
        return IntValidator.validate(self, value)


class MandatoryUTCDatetimeValidator(MandatoryValidator, 
                                    UTCDatetimeValidator):
    """Checks that a field is not None and a valid UTC datetime"""
    def validate(self, value):
        # We don't need to catch the value of the Mandatory validator
        MandatoryValidator.validate(self, value)
        return UTCDatetimeValidator.validate(self, value)

# Domain specific Validators

class MandatoryTicketValidator(MandatoryIntValidator):
    """Checks that the value is a valid AgiloTicket id and return
    the ticket in case it is."""
    def validate(self, value):
        from agilo.ticket.model import AgiloTicket, \
            AgiloTicketModelManager
        from agilo.scrum.backlog import Backlog
        if isinstance(value, (AgiloTicket, Backlog.BacklogItem)):
            return value
        value = self.super()
        try:
            value = AgiloTicketModelManager(self.env).get(tkt_id=value)
        except Exception:
            self.message = "must be a valid AgiloTicket id"
            self.error(value)
        return value


class SprintValidator(StringValidator):
    """Given a sprint name (or a Sprint instance or a serialized Sprint 
    instance) return the Sprint instance from the database. If no sprint name
    was given, just return None. Bail out if the given sprint name is invalid."""
    
    def _sprint_name(self, sprint_name):
        if isinstance(sprint_name, dict) and 'name' in sprint_name:
            return sprint_name['name']
        return sprint_name
    
    def _get_sprint(self, sprint_name):
        from agilo.scrum.sprint.model import Sprint, SprintModelManager
        if isinstance(sprint_name, Sprint):
            return sprint_name
        sprint_name = self.super.validate(self._sprint_name(sprint_name))
        sprint = SprintModelManager(self.env).get(name=sprint_name)
        return sprint
    
    def validate(self, sprint_name):
        if not sprint_name:
            return None
        try:
            return self._get_sprint(sprint_name)
        except Exception, e:
            self.message = exception_to_unicode(e)
            self.error(sprint_name)


class MandatorySprintOrStringValidator(SprintValidator, MandatoryStringValidator):
    """Return a Sprint or (if there is no sprint with that name) the initial 
    string. Bail out if sprint_name is empty.
    
    This is necessary for the SaveSprintCommand.
    """
    
    def validate(self, sprint_name):
        MandatoryStringValidator.validate(self, sprint_name)
        sprint = self._get_sprint(sprint_name)
        if sprint is None:
            return self._sprint_name(sprint_name)
        return sprint


class MandatorySprintValidator(SprintValidator):
    """Checks that the value is a valid Sprint name, and if returns
    the sprint, otherwise raise an exception"""
    def validate(self, value):
        sprint = self.super()
        if sprint is None:
            self.message = "must be a valid Sprint name"
            self.error(value)
        return sprint


class SprintNameValidator(MandatorySprintOrStringValidator):
    """Checks that the value would be an acceptable sprint name. Does not check
    if there is actually a sprint with that name."""
    def validate(self, value):
        value = self.super()
        if isinstance(value, basestring) and '/' in value:
            self.error(value)
        return value


class NonExistantSprintNameValidator(SprintNameValidator):
    """Checks that the value is a valid Sprint name, but raises an exception
    if the sprint already exists"""
    def validate(self, sprint_name):
        # raises exception if the name is invalid
        self.super()

        sprint = self._get_sprint(sprint_name)
        if sprint is not None:
            self.message = "already exists"
            self.error(sprint_name)
        return sprint_name


class TeamValidator(StringValidator):
    """Checks that the value is a valid Team name, and if returns the
    Team object, otherwise raise an exception"""
    def validate(self, team_name):
        from agilo.scrum.team.model import TeamModelManager, Team
        if isinstance(team_name, Team):
            return team_name
        elif isinstance(team_name, dict) and 'name' in team_name:
            team_name = team_name['name']
        # name must be a valid string
        team_name = super(TeamValidator, self).validate(team_name)
        if team_name:
            try:
                team = TeamModelManager(self.env).get(name=team_name)
                return team
            except Exception, e:
                self.message = unicode(e)
                self.error(team_name)
        return None


class MandatoryTeamValidator(TeamValidator):
    """Checks that the value is a valid Team object or a valid team
    name, for an existing Team object. If value is None an exception
    will be risen"""
    def validate(self, team_name):
        team = super(MandatoryTeamValidator, self).validate(team_name)
        if team is None:
            self.message = "must be a valid Team name"
            self.error(team_name)
        return team


class MandatorySprintWithTeamValidator(MandatorySprintValidator):
    """Checks that the value is a valid sprint and that the team 
    assigned to the sprint, is not None"""
    def validate(self, value):
        sprint = super(MandatorySprintWithTeamValidator, self).validate(value)
        if sprint.team is None:
            self.message = "This sprint has no team set"
            self.error(sprint)
        return sprint
