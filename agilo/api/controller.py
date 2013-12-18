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
from agilo.utils.simple_super import SuperProxy
"""
Module containing all the API definitions to access Agilo API from external
interfaces. Controllers are in charge of getting the input, validate it and 
process it. Depending on the processing status, the controller will redirect
the flow to an appropriate View to display results back to the caller. The 
Controller are in charge of managing the flow, not necessarily via HTTP, one
day there may be asynchronous controllers.
"""
import datetime

from trac.core import Component
from trac.env import Environment
from trac.util.compat import set
from trac.util.text import to_unicode

from agilo.api import validator

__all__ = ['ICommand', 'Controller', 'ValueObject', 'ValuePerTime']

class ValueObject(dict):
    """Used to pass data to the view level without having to move the
    real domain object"""
    
    def __repr__(self):
        super_repr = super(ValueObject, self).__repr__()
        return '%s(%s)' % (self.__class__.__name__, super_repr)
    
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError, e:
            raise AttributeError(e)
    
    def __setattr__(self, name, value):
        self[name] = value
    
    def copy(self):
        dict_copy = super(ValueObject, self).copy()
        return ValueObject(dict_copy)
    
class ValuePerTime(object):
    super = SuperProxy()
    
    def __init__(self, value, when):
        self.value = value
        self.when = when
    
    def _value(self):
        return self.value
    
    def _set_value(self, value):
        self.value = value
    
    def __repr__(self):
        return '%s(%s, %s)' % (self.__class__.__name__, self.value, self.when)
    
    def __eq__(self, other):
        if not isinstance(other, ValuePerTime):
            return False
        return (self.when == other.when) \
            and (self.value == other.value)
    
    def __ne__(self, other):
        return not (self == other)



class CommandPropertyDescriptor(object):
    """
    A descriptor for a command property, will check if there are
    validators for every parameter in the command and will run the
    validator after having set the property value. The validator can
    call the not_valid command to rise a NotValidError with context
    data, that can be reused.
    """
    def __init__(self, validator):
        """Initialize a descriptor for the given property name"""
        self.property_name = '_' + validator.param
        self.validate = validator.validate
        self.validator = validator
        
    def __set__(self, inst, value):
        """Sets the given value and validate if present"""
        if isinstance(value, tuple) and isinstance(value[0], Environment):
            self.validator._set_env(value[0])
            value = value[1]
        if self.validate:
            value = self.validate(value)
        # sets the value for the property
        setattr(inst, self.property_name, value)
    
    def __get__(self, inst, cls):
        """Gets the value out of the instance, or None"""
        return getattr(inst, self.property_name, None)
    
    def __delete__(self, inst):
        """Avoid the deletion of the member"""
        pass


class CommandMeta(type):
    """Metaclass for an ICommand, setting CommandPropertyDescriptor"""
    def __new__(cls, cname, cbases, cdict):
        """Creates the new class type"""
        new_class = super(CommandMeta, cls).__new__(cls, cname, 
                                                    cbases, cdict)
        if cname == 'ICommand':
            return new_class
        
        assert new_class.parameters is not None and \
            isinstance(new_class.parameters, dict), \
            "%s is not a valid command, parameters not declared" % \
            new_class.__name__
            
        for param, validator in new_class.parameters.items():
            # set the descriptor and than the value with validate
            # set to false, or will raise at the first validation
            # without setting all the values first
            descr = CommandPropertyDescriptor(validator(param))
            setattr(new_class, param, descr)
            
        return new_class


class ICommand(object):
    """Represent a command containing the needed information to be 
    executed. As a coding style a Command should be defined as inner 
    class of a specific controller representing the possible actions 
    that the Controller Performs.
    
    Every ICommand subclass should declare a class member 'parameters'
    as a dict containing all the parameters name:validator class.
    
    In case of validation error the validate method must call the
    'not_valid' method, passing an error message, the parameter and
    the wrong value."""
    __metaclass__ = CommandMeta
    # every command has to declare a dict of parameters as:
    #     name:validator_class
    # pairs so that will be possible to validate the number and
    # name of parameters
    parameters = None
    # Native will be checked in the _execute of each command to
    # determine if the data should be serialized back to a dictionary
    # or as native.
    native = False
    
    super = SuperProxy()
    
    
    class NotValidError(Exception):
        """Exception to be risen when the command is not valid"""
        def __init__(self, *args, **kwargs):
            """Set the attribute passed to create the command in the 
            exception"""
            cmd_attr = 'command_attributes'
            cmd = 'command'
            if kwargs.has_key(cmd_attr):
                setattr(self, cmd_attr, kwargs[cmd_attr])
                del kwargs[cmd_attr]
            if kwargs.has_key(cmd):
                setattr(self, cmd, kwargs[cmd])
                del kwargs[cmd]
            # Prepend the class name to the message argument
            if args:
                args = ("[" + self.command.__name__ + "] " + args[0],)
            # Python 2.4 compatibility, Exception is an old style class
            Exception.__init__(self, *args, **kwargs)
    
    
    class CommandError(Exception):
        """Risen when the command fails to execute"""
    
    
    def __init__(self, env, **params):
        """Initialize a command, making sure that the parameters are
        declared and that the command is valid"""
        # a list of tuple (message, param, value) that represent the
        # current command validation errors
        self._errors = None
        self.validate(params, env)
    
    @property
    def is_valid(self):
        """Returns True if the current command generated no validation
        errors, false otherwise. Differs from the validate cause it
        doesn't throw the not valid exception"""
        return not self._errors or len(self._errors) == 0
    
    def validate(self, params, env=None):
        """Validate the command parameters, if not valid raise a 
        NotValidError error, otherwise stores the params as needed for
        the command to perform properly."""
        for param in self.__class__.parameters:
            # is setting also None, cause in case a parameter is
            # mandatory for a command, the validator can set an error
            try:
                value = params.get(param)
                if env is not None:
                    value = (env, value)
                setattr(self, param, value)
            except validator.ValidationError, e:
                self.not_valid(to_unicode(e), e.param, e.value)
                continue
        # Check if the number of parameters is more than needed
        extra_params = set(params).difference(set(self.__class__.parameters))
        if len(extra_params) > 0:
            self.not_valid("Parameters not recognized:", '', 
                           ', '.join(extra_params))
        
        # check if there is a consistency validation
        consistency_validation = getattr(self, 
                                         'consistency_validation', 
                                         None)
        if callable(consistency_validation):
            consistency_validation(env)
        
        if not self.is_valid:
            self._raise_errors()
            
    def _raise_errors(self):
        """Utility to raise errors, and reset validation"""
        message = ''
        params = {}
        for error in self._errors:
            message += "%s: %s (value=%s)" % \
                        (error[1], error[0], error[2])
            params[error[1]] = error[2]
        # reset errors
        self._errors = None
        raise self.NotValidError(message, 
                                 command=self.__class__, 
                                 command_attributes=params) 
    
    def not_valid(self, message, param, value=None):
        """
        Sets a validation error to the command, before the command
        will be executed, the validation will be performed and an
        error risen. In this way will be possible to validate multiple
        parameters at the same time, without raising the exception for
        each of them.
        """
        if not self._errors:
            self._errors = []
        self._errors.append((message, param, value))
        
    def as_dict(self):
        """
        Utility method to return the currently set command parameters as a dict
        of attr:value to be used in a response context.
        """
        attrs = dict()
        for attr in self.__class__.parameters:
            attr_value = getattr(self, attr)
            if isinstance(attr_value, CommandPropertyDescriptor):
                # Should always be the case... but...
                attrs[attr] = attr_value
        return attrs
    
    def return_as_value_object(self, persistent_object, date_converter=None, 
                       as_key=None):
        """Utility to build a dictionary out of a persistent object, 
        so that it can be send to Genshi directly. The datetime 
        parameters are set as python datetime in UTC, the view will
        have to convert them into the right format or pass a
        date_converter function and let the controller filter the
        datetimes. The as_key parameter allow to specify with which
        dictionary key the object has to be returned, to avoid key 
        clashing, by default the key will be the classname lowered."""
        if (persistent_object is not None) and (self.native == False):
            if hasattr(persistent_object, 'as_dict'):
                data = persistent_object.as_dict()
                for key, value in data.items():
                    if isinstance(value, (datetime.datetime, datetime.date)) and \
                            date_converter is not None:
                        data[key] = date_converter(value)
                    elif hasattr(value, 'as_dict'):
                        data[key] = ValueObject(value.as_dict())
                    elif isinstance(value, dict) and not isinstance(value, ValueObject):
                        data[key] = ValueObject(value)
                return ValueObject(data)
            elif isinstance(persistent_object, (list, set, tuple)):
                data = list()
                for item in persistent_object:
                    data.append(self.return_as_value_object(item, date_converter, as_key))
                return data
        return persistent_object

    def execute(self, controller, date_converter=None, as_key=None):
        """
        Wrapper to specific command execution that will take care to
        verify that there are no validation errors, and that the 
        command can be executed, normally called by the controller
        """
        if self._errors and len(self._errors) > 0:
            self._raise_errors()
        else:
            return self._execute(controller, date_converter, as_key)
    
    def _execute(self, controller, date_converter=None, as_key=None):
        """
        Execute the command, needs to have a controller reference to 
        access the environment and other members specific to the 
        controller. It must return the result of the Command 
        processing or raise a CommandError in case the elaboration 
        could not complete
        """
        raise NotImplementedError("Each command need to implement" + \
                                  " its own _execute method")


class Controller(Component):
    """
    Represent a Controller, taking a command to process, and returning
    its output to the caller. In case of errors it will raise the 
    appropriate exceptions.
    """
    abstract = True
    
    class CommandNotFoundError(Exception):
        """Raised when a requested command is not found by the 
        controller"""
    
    
    def _check_command_is_for_this_controller(self, command):
        """Returns True if the command belongs to this controller"""
        for member_name in dir(self):
            member = getattr(self, member_name)
            if isinstance(member, type) and \
                    issubclass(member, ICommand) and \
                    command.__class__ == member:
                return True
    
    def process_command(self, command, date_converter=None, 
                        as_key=None):
        """
        Process the given command and return the result to the caller,
        it wraps any exception into an ICommand.CommandError.
        """
        if not self._check_command_is_for_this_controller(command):
            msg = "The command (%s) was not found on this controller" % command
            raise self.CommandNotFoundError(msg)
        try:
            return command.execute(self, date_converter, as_key)
        except Exception, e:
            if not isinstance(e, ICommand.CommandError):
                e = ICommand.CommandError(to_unicode(e))
                #raise e
            raise

