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

import re
# We need to import Key here because some evaluated commands may include things
# like Key.Type 
from agilo.utils import Key
from agilo.utils.compat import exception_to_unicode
from agilo.utils.log import debug, warning, error

class CommandParser(object):
    """
    A command parser to interpret commands to substitute aliases
    into the data dictionary of an HTTP Request.
    """
    # Accessors Expression to match predicates and elements
    # ELEM is the first data dictionary entry
    ELEM = re.compile(r'[\w\.\']+')
    # ITER is an iterator, preceded by the @ sign
    ITER = re.compile(r'(?<=[\@])([\w\.\']+)(\(.+\))?')
    # KEY is a by_key element, preceded by : sign
    KEY = re.compile(r'(?<=[\:])([\w\.\'\*]+)(\|([\w\.\']+))?')
    # POS is a by_pos element, preceded by , sign
    POS = re.compile(r'(?<=\,)([0-9]+)(\|([0-9]+))?')

    def __init__(self, env, type_to_alias, alias_to_type):
        """Initialize the command parser"""
        self.env = env
        self.log = env.log
        self._alias_mapping = alias_to_type or {}
        self._type_to_alias = type_to_alias or {}
        self._DEBUG = "[CommandParser]"
        
    def _parse_command(self, command):
        """
        Parses a command and returns a tuple containing 
        (accessor, key, command), where:
         - accessor: is a callable accessor
         - key: is the key to pass to the accessor
         - command: is the remaining part of the command
        """
        def _parse_by_key(key_m, command):
            """Returns the appropriate tuple to represent a by key accessor"""
            key1 = key_m.group(1)
            # may be also an alternative key
            key2 = key_m.group(3)
            command = command[key_m.end():]
            # Before sending the keys, check whether they
            # are string to be avaluated
            if key2 is not None:
                #debug(self, "[Parse Command]: Returning By Key, %s, %s" % \
                #            ((eval(key1), eval(key2)), command))
                return (self._by_key, (eval(key1), eval(key2)), command)
            else:
                #debug(self, "[Parse Command]: Returning By Key, %s, %s" % \
                #            (eval(key1), command))
                return (self._by_key, eval(key1), command)
                
        def _parse_iterate(iter_m, command):
            """Returns the appropriate tuple to represent an iterate accessor"""
            key = iter_m.group(1)
            cond = iter_m.group(2)
            command = command[iter_m.end():]
            if cond is not None:
                #debug(self, "[Parse Command]: Returning Iterate, %s, %s" % \
                #                ((eval(key), cond), command))
                return (self._iterate, (eval(key), cond), command)
            else:
                #debug(self, "[Parse Command]: Returning Iterate, %s, %s" % \
                #                (eval(key), command))
                return (self._iterate, eval(key), command)
                
        def _parse_by_pos(pos_m, command):
            """Returns the appropriate tuple to represent a by pos accessor"""
            key1 = pos_m.group(1)
            key2 = pos_m.group(2)
            command = command[pos_m.end():]
            if key2 is not None:
                #debug(self, "[Parse Command]: Returning By Pos, %s, %s" % \
                #                ((eval(key1), eval(key2)), command))
                return (self._by_pos, (eval(key1), eval(key2)), command)
            else:
                #debug(self, "[Parse Command]: Returning By Pos, %s, %s" % \
                #                (eval(key1), command))
                return (self._by_pos, eval(key1), command)
            
        #debug(self, "[Parse Command]: Called with %s" % command)
        # With match we get the first key for data dictionary
        if isinstance(command, basestring) and self.ELEM.match(command):
            elem_m = self.ELEM.match(command)
            key = elem_m.group(0)
            command = command[elem_m.end():]
            #debug(self, "[Parse Command]: Returning By Key, %s, %s" % 
            #                (eval(key), command))
            return (self._by_key, eval(key), command)
        # Look if there is a valid iterator expression, including
        # condition
        else:
            # Given the search behaviour we have to check that there is no
            # previous match of KEY as well:
            key_m = self.KEY.search(command)
            iter_m = self.ITER.search(command)
            pos_m = self.POS.search(command)
            # find the minimum position and execute that command
            pos = dict()
            for match, parse in [(key_m, _parse_by_key), (iter_m, _parse_iterate), (pos_m, _parse_by_pos)]:
                if match is not None:
                    pos[match.start()] = (parse, match)
            # Now get the minimum if any
            if len(pos) > 0: # at least one
                parse, match = pos[min(pos.keys())]
                return parse(match, command)
            else:
                error(self, "[Parse Command]: Please provide a string or buffer => %s(%s)" % \
                      (command, type(command)))
                return (None, None, None)

    def _aliasize(self, p_type):
        """
        Returns the alias for the given property type or the property type
        for the given alias
        """
        def _process(prop_type):
            """
            Process the final property
            """
            try:
                if prop_type in self._type_to_alias:
                    #debug(self, "[Aliasize]: Returning %s for %s" % \
                    #      (self._type_to_alias[prop_type], prop_type))
                    return self._type_to_alias[prop_type]
                elif prop_type in self._alias_mapping:
                    #debug(self, "[Aliasize]: Returning %s for %s" % \
                    #      (self._alias_mapping[prop_type], prop_type))
                    return self._alias_mapping[prop_type]
#                else:
#                    warning(self, "No alias found for %s..." % prop_type)
            except TypeError, e:
                warning(self, "[Aliasize]: Error, %s" % exception_to_unicode(e))
                
            # Return always the property if not aliasized
            return prop_type

        # Check if prop_type is a list, the case is common and we
        # don't want to make inutil double calls to iterate
        #debug(self, "Called _aliasize(%s)..." % p_type)
        
        if isinstance(p_type, list):
            for i, e in enumerate(p_type):
                p_type[i] = self._aliasize(e)
        else:
            p_type = _process(p_type)
        return p_type

    def _by_pos(self, data, key=None, command=None):
        """
        Replaces aliases/types in the given data at the given key position.
        If the position is not valid, than None is returned
        """
        # Check if there is a double key
        key1 = key2 = None
        if isinstance(key, tuple):
            key1, key2 = key
        else:
            key1 = key
        
        #debug(self, "[By Pos]: Processing %s, with %s" % (repr(data), key))    
        if key1 is not None and isinstance(key1, int):
            # Replace if there is no command left
            if not command:
                if isinstance(data, list):
                    data[key1] = self._aliasize(data[key1])
                    if key2 is not None and isinstance(key2, int):
                        data[key2] = self._aliasize(data[key2])
                        
                elif isinstance(data, tuple):
                    # is unmutable we need to rebuild the tuple
                    new_data = list()
                    for i, value in enumerate(data):
                        if i in [key1, key2]:
                            new_data.append(self._aliasize(value))
                        else:
                            new_data.append(value)
                    data = tuple(new_data)
            else:
                acc, key, command = self._parse_command(command)
                if acc is not None:
                    try:
                        #debug(self, "[By Pos]: calling\nacc: %s\ndata: %s" \
                        #            "\nkey: %s\n\n" % \
                        #            (acc, data[key1], key1))
                        acc(data[key1], key, command)
                        if key2 is not None:
                            #debug(self, "[By Pos]: calling\nacc: %s\n" \
                            #            "data: %s\nkey: %s\n\n" % \
                            #            (acc, data[key2], key2))
                            acc(data[key2], key, command)
                    except IndexError, e:
                        error(self, "[By Pos]: Invalid index: %s, %s for data: %s" % \
                                    (key1, key2, repr(data)))

    def _by_key(self, data, key=None, command=None):
        """
        Replaces aliases/types in the given data, accessing the given key.
        None is returned in case the given data is not supporting key access
        or the given key is not existing. If the alias is not existing, than the
        value of the dictionary key is returned.
        """
        # Checks for double key, only valid in case of leaf
        if key is not None:
            if isinstance(key, tuple):
                key1, key2 = key
            else:
                key1, key2 = key, None
            
            # Processing the data
            #debug(self, "[By Key]: Processing %s, with %s" % (repr(data), key))
            if data is not None and hasattr(data, '__setitem__'):
                try:
                    # check if key is '*' that will mean we have to parse
                    # all the values of the dictionary
                    if key1 == '*' and isinstance(data, dict):
                        for data_key, data_value in data.items():
                            if not command:
                                data[data_key] = self._aliasize(data_value)
                            else:
                                # Not consuming the real command, we are in a loop
                                acc, key, newcommand = self._parse_command(command)
                                if acc is not None:
                                    acc(data[data_key], key, newcommand)
                    # If there is no command left, than we are at the leaf
                    # substitute the value in the dictionary
                    elif not command:
                        data[key1] = self._aliasize(data[key1])
                        try:
                            data[key2] = self._aliasize(data[key2])
                        except KeyError:
                            # key2 is None or not existing
                            #warning(self, "[By Key]: No second key found...")
                            pass
                    else:
                        acc, key, command = self._parse_command(command)
                        #debug(self, "[By Key]: calling\nacc: %s\ndata[%s], " \
                        #            "data: %s\nkey: %s\n\n" % \
                        #            (acc, key1, repr(data), key))
                        if acc is not None:
                            acc(data[key1], key, command)
                except KeyError, e:
                    #warning(self, "[By Key]: Warning %s" % exception_to_unicode(e))
                    pass
                
    def _iterate(self, data, key=None, command=None):
        """
        Operator to iterate over a sequence and return the items matching the
        given condition. If no condition is supplied an Alias replacing will 
        be attempted on the whole list. The operator returns a list
        """
        # Check if the key contains also a condition
        condition = realkey = None
        if key is not None and isinstance(key, tuple):
            realkey, condition = key
        else:
            realkey = key
        
        #debug(self, "[Iterate]: Processing %s with %s, command: #%s#" % \
        #      (repr(data), key, command))
        # Now process the data, take the analyzed data that should be pointers to the
        # real ones, so that the real_data gets modified too
        if data is not None and hasattr(data, '__iter__'):
            for i, item in enumerate(data):
                #debug(self, "[Iterate]: Command left: %s\ni: %d\ndata[%d] = %s" % \
                #            (command, i, i, data[i]))
                if (condition is not None and eval(condition)) or condition is None:
                    if realkey is not None:
                        try:
                            if not command:
                                #debug(self, "[Iterate]: No command left, " \
                                #            "calculating aliases...")
                                data[i][realkey] = self._aliasize(item[realkey])
                            else:
                                #debug(self, "[Iterate]: Processing next " \
                                #            "command... %s" % command)
                                # The command in this case is not consumed, 
                                # because we are in a cycle and the same command 
                                # has to be used to evaluate all items.
                                acc, newkey, newcommand = self._parse_command(command)
                                if acc is not None:
                                    #debug(self, "[Iterate]: calling\nacc: %s\n" \
                                    #            "data[%s], data: %s\nkey: %s\n\n" % \
                                    #            (acc, realkey, data[i], newkey))
                                    acc(data[i][realkey], newkey, newcommand)
                        except KeyError, e:
                            warning(self, "[Iterate]: Warning %s" % exception_to_unicode(e))
                    else:
                        data[i] = self._aliasize(item)

    def replace(self, data, command):
        """Build a replacer command and return it"""
        if command is not None:
            #debug(self, "[Replace]: replacing %s in %s" % \
            #                (command, repr(data)))
            acc, key, command = self._parse_command(command)
            if acc is not None:
                acc(data, key, command)
