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

import re
import threading
import cPickle
from UserDict import DictMixin

from trac.core import Component, implements, TracError
from trac.env import Environment
from trac.db import Table, Column, Index
from trac.util.compat import set
from trac.util.datefmt import to_datetime, to_timestamp, utc
from trac.util.text import to_unicode
from trac.util.translation import _

# The PyFormatCursor is only defined by Trac if pysqlite2 could be imported.
# If someone does not have psqlite2 installed, the import will fail.
try:
    from trac.db.sqlite_backend import PyFormatCursor
    has_modern_sqlite = True
except ImportError:
    has_modern_sqlite = False


from agilo import AGILO_TABLE_PREFIX
from agilo.api import IModelManager, SimpleModelCache
from agilo.utils.compat import exception_to_unicode
from agilo.utils.log import warning, debug
from agilo.utils.db import get_db_for_write, create_table
from agilo.utils.simple_super import SuperProxy

# Utility functions to safe pickle and unpickle unicode strings
def _pickle(value):
    return cPickle.dumps(value)
    
def _unpickle(db_value):
    if isinstance(db_value, unicode):
        return cPickle.loads(str(db_value))
    return cPickle.loads(db_value)

def add_multiple_params_values(current_values, column, operator, values, condition):
        """Add multiple values parameters to the query, for example in case
        of a criteria like: id in (1, 2, 3, 5, 8, 12) it will create a list
        of parameters: id1, id2, id3... with relative value associated. It
        modifies the condition and the current values dictionary"""
        if values:
            if not isinstance(values, (list, tuple)):
                values = [values]
            params = []
            for i, value in enumerate(values):
                pname = column + str(i)
                params.append('%(' + pname + ')s')
                current_values[pname] = value
            operator += ' (%s)' % ', '.join(params)
            condition.append('%s %s' % (column, operator))

def format_condition(table, column, operator):
    """Format the condition to be appended properly, according to the
    column type and value of the condition"""
    condition = ''
    if operator is None:
        condition = "(%(table)s.%(column)s IS NULL OR %(table)s.%(column)s='')" % \
                    {'table': table, 'column': column}
    else:
        condition = '%(table)s.%(column)s%(operator)s%%(%(column)s)s' % \
                    {'table': table, 'column': column, 'operator': operator}
    return condition
           
def safe_execute(cursor, sql, args=None):
    """Convert dictionary argument to list style because the trac sqlite
    backend can not handle named arguments in sql - even though SQLite
    itself can."""
    if not isinstance(args, dict):
        return cursor.execute(sql, args)
    
    if has_modern_sqlite:
        new_args = []
        new_sql = sql
        for match in re.finditer(r'%\((?P<name>.*?)\)s', sql):
            # loop over named arguments and replace with %s. Put arguments in list
            new_args.append(args[match.group('name')])
            new_sql = new_sql.replace('%%(%s)s' % match.group('name'), '%s', 1)
        if '_multi_' in args:
            # append the multiple values
            new_args += args['_multi_']
        sql, args = new_sql, new_args
    elif ('_multi_' in args):
        # We must not use named arguments together with parameter lists.
        # The solution here is to convert the parameter list into named 
        # parameters.
        multi_args = args.pop('_multi_')
        new_sql = sql
        
        # We need to replace the last variables first otherwise the start/end
        # indexes for later replacements become meaningless.
        matches_with_value = reversed(zip(re.finditer(r'(%[sd])', sql), multi_args))
        for i, (match, value) in enumerate(matches_with_value):
            dummy_name = 'auto_name%d' % i
            replacement = '%%(%s)s' % dummy_name
            new_sql = new_sql[:match.start()] + replacement + new_sql[match.end():]
            args[dummy_name] = value
        sql = new_sql
    return cursor.execute(sql, args)


class Field(Column):
    """Represent a persistent class field"""
    def __init__(self, name='field', type='text', primary_key=False, 
                 size=None, unique=False, auto_increment=False, db_name=None):
        # Flags to check the conversion types
        self.is_date = False # Converts to date
        self.is_datetime = False # Converts to datetime
        self.is_ticket = False # Converts to AgiloTicket
        self.is_serialized = False # Pickles and Unpickles the object into str
        if primary_key:
            unique = True
        if type == 'date':
            type = 'integer'
            self.is_date = True
        elif type == 'datetime':
            type = 'integer'
            self.is_datetime = True
        elif type == 'ticket':
            type = 'integer'
            self.is_ticket = True
        elif type == 'serialized':
            type = 'text'
            self.is_serialized = True
        
        # in Trac 0.11 Column.__init__ had a parameter named "unique" but it was
        # not used in any way in that method. That unused parameter was removed
        # in trac 0.12.
        super(Field, self).__init__(name=db_name or name, type=type, size=size, 
                                    auto_increment=auto_increment)
        self.display_name = name
        self.primary_key = primary_key
        # Trac doesn't use this parameter
        self.unique = unique
        
    def __str__(self):
        """Returns the field name"""
        return '<%s (name=%s, type=%s, pk=%s)>' % (self.__class__.__name__, 
                                                   repr(self.name), 
                                                   repr(self.type), 
                                                   repr(self.primary_key))
    
    def __repr__(self):
        """Returns a representation of the Field"""
        return self.__str__()
    
    def as_index(self):
        """Return an Index for the Database in case unique is True for this field"""
        if self.unique:
            return Index(columns=[self.name], unique=self.unique)
    
    def as_param(self, old=False):
        """Return the field as a replaceable string param, in the form %(fieldname)s"""
        # REFACT: this works _only_ because all default values in the db are also falsy ('', 0, 0.0, None)
        # And it fails if the old value is the empty string
        return '%%(%s%s)s' % (self.name, old and '_old' or '')
    
    def as_key_value(self, old=False, op='='):
        """Return the field as key and value pairs replaceable"""
        return self.name + op + self.as_param(old)
    
    def copy(self):
        """Returns a copy of this field"""
        return Field(name=self.display_name, type=self.type, 
                     primary_key=self.primary_key, size=self.size, 
                     unique=self.unique, auto_increment=self.auto_increment,
                     db_name=self.name)
    

class Relation(Field):
    """Express a relation to a PO Object"""
    def __init__(self, po_class, primary_key=False, unique=False, db_name=None):
        assert po_class is not None and issubclass(po_class, PersistentObject), \
            "PersistentObject: %s" % po_class
        # TODO: support multiple keys for Relation, means multiple fields
        if hasattr(po_class, 'Meta') and po_class.Meta is not None:
            for attr in dir(po_class.Meta):
                if not attr.startswith('__'):
                    field = getattr(po_class.Meta, attr)
                    if isinstance(field, Field) and field.primary_key:
                        self.relation_pk = field
                        break
        name = db_name
        if not name:
            name = po_class.__name__.lower() + '_' + self.relation_pk.name
        super(Relation, self).__init__(name=name, type=self.relation_pk.type, 
                                       size=self.relation_pk.size,
                                       unique=unique, primary_key=primary_key)
        self.relation_class = po_class


class Manager(object):
    """
    Manager type of field, sets the ModelManager for the current persistent
    object, so that will be available as an instance variable
    """
    def __init__(self, class_name):
        self.class_name = class_name
        self.name = 'manager'
        self._manager_class = None
        
    @property
    def manager_class(self):
        """
        Returns the Manager Class. Using lazy initialization or will fail
        if called before the whole module get parsed
        """
        if not self._manager_class:
            full_path = self.class_name.split('.')
            c_name = full_path.pop()
            m = __import__('.'.join(full_path), globals(), locals(), [c_name,])
            if hasattr(m, c_name):
                self._manager_class = getattr(m, c_name)
        return self._manager_class
    
    def __repr__(self):
        return "<Manager(%s): %s>" % (self.class_name, self.manager_class)


class UnableToLoadObjectError(Exception):
    """Raise when a PersistentObject can't load itself from the DB"""
    pass


class UnableToSaveObjectError(Exception):
    """Raise when a PersistentObject can't save itself to the DB"""
    pass


class UnableToDeleteObjectError(Exception):
    """Raise when a PersistentObject can't delete itself from the DB"""
    pass


class PersistentObjectMeta(type):
    """
    Metaclass to control the PersistentObject behavior. It allows
    to define class members to be persisted, and take care of all the
    SQL needed to read, store and delete the object.
    """
    def __new__(cls, cname, cbases, cdict):
        """
        Check that the object has an inner class called Meta, and extract
        informations related to persistent fields
        """
        class FieldDictionary(DictMixin, dict):
            """
            Implements a field dictionary, which is a dictionary that
            returns items and values sorted by keys
            """
            __len__ = dict.__len__
            __contains__ = dict.__contains__
            has_key = __contains__
            
            def __iter__(self):
                """Return the key sorted"""
                for k in sorted(dict.__iter__(self)):
                    yield k
            iterkeys = __iter__
            
            def keys(self):
                """Return a sorted list of keys"""
                return sorted(self)
            
            def values(self):
                """Return a sorted list of values, sorted by key"""
                return map(self.get, self.keys())
            
            def items(self):
                """Return key, value pairs sorted by key"""
                return [(k, self[k]) for k in self.keys()]
            
            def iteritems(self):
                """Yields a tuple key, value sorted by key"""
                for k in self.keys():
                    yield k, self[k]
        
        
        class FieldDescriptor(object):
            """Adds custom getter and setter to persistent fields"""
            def __init__(self, field):
                """Initialize for a field"""
                self.field = field
                self.name = field.display_name
                self.db_name = field.name
                self.prop = '_%s' % self.name
                # Defines hooks for local function manipulators
                self.__before_set = '_before_set_%s' % self.name
                self.__after_get = '_after_get_%s' % self.name
                self.__after_set = '_after_set_%s' % self.name
                
            def __get_manipulator(self, inst, manipulator_name):
                """Return a callable manipulator object"""
                if hasattr(inst, manipulator_name):
                    method = getattr(inst, manipulator_name)
                    if callable(method):
                        return method
            
            def __get__(self, inst, cls):
                """Returns the value of the property"""
                if inst is not None:
                    value = getattr(inst, self.prop)
                    after = self.__get_manipulator(inst, self.__after_get)
                    if after is not None:
                        return after(value)
                    return value
                return self
            
            def __set__(self, inst, value):
                """Sets the value for the property, doesn't allow to set
                keys or unique values to None"""
                before = self.__get_manipulator(inst, self.__before_set)
                after = self.__get_manipulator(inst, self.__after_set)
                old_value = getattr(inst, self.prop)
                if before is not None:
                    value = before(value)

                if value is None:
                    if self.name in inst._keys or (hasattr(inst, '_uniques') and self.name in inst._uniques):
                        return
                elif isinstance(self.field, Relation) and not type(value) == self.field.relation_class:
                    # avoid setting wrong type on relations
                    return
                elif type(value) == type(old_value) and value == old_value:
                    return old_value

                # set the value only if needed
                setattr(inst, self.prop, value)
                inst._changed = True

                if after is not None:
                    return after(old_value, value)
                
            def __delete__(self, inst):
                """Avoid deletion of persistent fields"""
                pass
            
            
        class ManagerDescriptor(object):
            """
            Make sure the manager can not be changed or set at runtime, and
            return an instance when called
            """
            def __init__(self, manager):
                self.manager = manager
                self.prop = '_model_manager'
            
            def __get__(self, inst, cls):
                """
                Returns an instance of the manager configured for this
                persistent object
                """
                if inst is not None and hasattr(inst, 'env'):
                    value = getattr(inst, self.prop)
                    import types
                    if not value or isinstance(value, Manager):
                        value = self.manager.manager_class(inst.env)
                        setattr(inst, self.prop, value)
                    elif isinstance(value, types.TypeType):
                        # This is a fix for a unit test failure when running all
                        # unit tests - failed with 
                        # agilo/scrum/sprint.py", line 606, in _get_sprint
                        #     sprint = self.manager.get(name=sprint_or_name)
                        # TypeError: unbound method get() must be called with SprintModelManager instance as first argument (got nothing instead)
                        # Did not fail when I only run agilo/scrum/tests/sprint_test.py
                        value = value(inst.env)
                        setattr(inst, self.prop, value)
                    return value
            
            def __set__(self, inst, value):
                """No way to set the manager at runtime"""
                pass
            
            def __delete__(self, inst):
                """No way to delete the manager at runtime"""
                pass
            
                
        new_class = super(PersistentObjectMeta, cls).__new__(cls, cname, cbases, cdict)
        if cname == 'PersistentObject':
            # It is somehow an abstract class we don't need to process it
            return new_class
        
        # Prepares slots for fields, keys and table
        if '__slots__' in cdict:
            for prop in ['_fields', '_keys', '_uniques', '_table', '_old']:
                if prop not in cdict['__slots__']:
                    cdict['__slots__'] = tuple(cdict['__slots__']) + (prop,)
        
        meta = cdict.get('Meta')
        if meta is not None:
            # Identify all the fields to persist
            _fields = FieldDictionary()
            _keys = FieldDictionary()
            _uniques = FieldDictionary()
            table_name = AGILO_TABLE_PREFIX + re.sub(r'([A-Z]+)', r'_\1', cname).lower()[1:]
            
            for fieldname in dir(meta):
                if not fieldname.startswith('__'):
                    f = getattr(meta, fieldname)
                    if isinstance(f, Field):
                        if f.name == 'field':
                            f.name = fieldname
                        f.display_name = fieldname
                        _fields[fieldname] = f
                        if f.primary_key:
                            _keys[fieldname] = f
                        elif f.unique:
                            _uniques[fieldname] = f
                        # Create the member
                        setattr(new_class, '_%s' % fieldname, None)
                        setattr(new_class, fieldname, FieldDescriptor(f))
                    elif isinstance(f, Manager):
                        # is the current PersistentObject ModelManager
                        # store it in the variable as instance
                        f.name = fieldname
                        setattr(new_class, '_model_manager', f)
                        setattr(new_class, fieldname, ManagerDescriptor(f))
                    elif isinstance(f, basestring) and fieldname == 'table_name':
                        table_name = f
                        
            # if there is no Primary Key, supply a default incremental ID
            if len(_keys) == 0:
                if len(_uniques) == 0:
                    raise TypeError(_("A PersistentObject must have at least a PrimaryKey Field or a Unique Field"))
                else:
                    new_class._uniques = _uniques
                key = Field(name='_id', type='integer', primary_key=True, auto_increment=True)
                _keys[key.name] = key
                _fields[key.name] = key
                setattr(new_class, key.name, None)
            
            # Set fields and keys as class fields
            new_class._fields = _fields
            new_class._keys = _keys
            
            # Now build the table definition for this object
            new_class._table = Table(table_name, key=[k.name for k in _keys.values()])
            new_class._table.columns = _fields.values()
            if len(_uniques) > 0:
                new_class._table.indices = [i.as_index() for i in _uniques.values()]
            
            # Now set the SQL strings for the class
            new_class.SQL_I = "INSERT INTO " + table_name + " (%s) VALUES (%s)"
            new_class.SQL_U = "UPDATE " + table_name + " SET %s"
            new_class.SQL_D = "DELETE FROM " + table_name
            new_class.SQL_S = "SELECT %s FROM %s" % (', ' .join([f.name for f in _fields.values()]),
                                                     table_name)
        return new_class


class PersistentObject(object):
    """Represent a basic persistent object for agilo"""
    __metaclass__ = PersistentObjectMeta
    super = SuperProxy()
    
    class DoesNotExists(Exception):
        """
        Risen when the object you request doesn't exists, used when
        you need to be sure that the PersistentObject exists on the DB
        """
        pass
    
    def __init__(self, env, **kwargs):
        """Initialize the persistent object"""
        assert isinstance(env, Environment), 'env has to be a valid Environment object'
        assert self._keys is not None and len(self._keys) >= 1, 'a Persistent Object must have a Primary Key'
        super(PersistentObject, self).__init__()
        # Set an place to store instance old values
        self._old = dict()
        self._changed = False
        self._exists = False
        self.env = env
        self.log = env.log
        
        db = kwargs.pop('db', None)
        do_load = kwargs.pop('load', True)
        
        self._assert_has_no_invalid_parameters(kwargs)
        
        # The idea here is that we only want to load anything from the db if we 
        # have at least all the necessary primary keys or all the necessary
        # unique indexes so we can correctly identify which row in the database
        # to load.
        at_least_one = False
        for prop, value in kwargs.items():
            is_valid_primary_key = prop in self._keys
            is_valid_unique_id = hasattr(self, '_uniques') and prop in self._uniques
            if value and (is_valid_primary_key or is_valid_unique_id):
                at_least_one = True
        
        # Sets member primary key attribute from constructor
        # FIXME (AT): why do we copy the dictionary here? it is not getting 
        # changed in the loop and even if the items() already returns a tuple
        # list that is a copy of the keys, values
        for prop, value in kwargs.copy().items():
            is_valid_field = prop in self._fields
            if is_valid_field:
                setattr(self, prop, value)
        
        # FIXME: at_least_one is wrong - we need enough data (compound primary keys)
        # Check if there is a load False in the parameter
        if at_least_one and do_load:
            # loads value from the database for this object
            self._load(db=db)
    
    def _assert_has_no_invalid_parameters(self, parameters):
        invalid_parameters = set(parameters).difference(set(self._fields))
        if len(invalid_parameters) > 0:
            parameter_name = list(invalid_parameters)[0]
            error_msg = "__init__() got an unexpected keyword argument '%s'"
            raise TypeError(error_msg % parameter_name)
    
    def __cmp__(self, other):
        """
        Standard compare method for PersistentObjects, returns
        0 if all the fields are equal and the class is an instance
        of the same type
        """
        if isinstance(other, self.__class__):
            for f in self._fields:
                if not getattr(self, f) == getattr(other, f):
                    return 1
            return 0
        return -1
    
    @property
    def exists(self):
        """Returns True if the object exists in the database"""
        return self._exists
    
    def _get_db_keys_and_ids(self, is_insert=False):
        ids = list()
        db_keys = dict()
        keys = self._get_keys(is_insert=is_insert)
        for k in keys:
            field = self._fields.get(k)
            if field is None: # it's an _old field probably
                db_keys[k] = keys[k]
                continue
            db_keys[field.name] = keys[k]
            ids.append(field)
        return db_keys, ids
    
    def _get_filter(self):
        """Returns the tuple (keys, filter) where keys is the dictionary of
        'keys:value' to use in the WHERE clause and filter is the current 
        filter set as WHERE clause"""
        db_keys, ids = self._get_db_keys_and_ids()
        clause_elements = [k.as_key_value(old=self._old.get(k.display_name) is not None) for k in ids]
        filter = ' WHERE ' + ' AND '.join(clause_elements)
        return db_keys, filter
    
    def _get_keys(self, is_insert=False):
        """Returns the dictionary of the parameters needed for the SQL query to 
        identify this instance exactly."""
        params = dict()
        ids = None
        if self._keys.has_key('_id'):
            # Self generated id, use unique
            ids = self._uniques
        else:
            ids = self._keys
        for key, field in ids.items():
            value = self._get_value_of_field(field, inst=self)
            if is_insert and field.auto_increment:
                # For auto increment fields we can skip this field because the 
                # database will assign a value to this field
                continue
            if value is None:
                # We must not ignore None types - otherwise we are not able to
                # identify the db row exactly.
                raise ValueError('No valid value for primary key <%s> (did you pass a string instead of an object?)' % key)
            db_name = field.name
            params[key] = value
            if self._changed and self._old.get(key) is not None:
                params['%s_old' % db_name] = self._get_value_of_field(field, value=self._old[key])
            else:
                params['%s_old' % db_name] = params[key]
        return params
    
    def _get_params(self, is_insert=False):
        """Returns the dictionary of the parameters needed for the SQL query"""
        params = dict()
        for field_name, field in self._fields.items():
            if field_name == '_id' or (is_insert and field.auto_increment):
                continue
            value = self._get_value_of_field(field, inst=self)
            params[field_name] = value
        return params
    
    @classmethod
    def _get_related_manager(cls, env, related_class):
        """
        Returns the manager instance to manage the related class or
        a default PersistentObjectModelManager subclass
        """
        model_manager = getattr(related_class, '_model_manager', None)
        if isinstance(model_manager, Manager):
            # we can build the class now
            related_class._model_manager = model_manager.manager_class
        elif not model_manager:
            default_manager = type('%sModelManager' % related_class.__name__.split('.').pop(),
                                   (PersistentObjectModelManager,), {})
            default_manager.model = related_class
            related_class._model_manager = default_manager
            debug(env, "Class %s has no ModelManager set..." % related_class)
        return related_class._model_manager(env)
    
    @classmethod
    def _set_value_of_field(cls, inst, env, value, field, db=None):
        """
        Sets the value of the instance (inst) attribute, taking care of
        conversion expressed in the field type member. Used to set
        attribute from value loaded from the db.
        """
        if value not in (None, '', 0):
            if isinstance(field, Relation):
                # Load the object into the field member
                kwargs = {field.relation_pk.name: value}
                related_manager = cls._get_related_manager(env, field.relation_class)
                value = related_manager.get(db=db, **kwargs)
            elif field.is_date:
                value = to_datetime(value).date()
            elif field.is_datetime:
                # The timestamps are saved in UTC and should be loaded
                # as datetime aware object in UTC timezone
                value = to_datetime(value, tzinfo=utc)
            elif field.is_ticket:
                # local import to avoid loop
                from agilo.ticket.model import AgiloTicketModelManager
                value = AgiloTicketModelManager(env).get(tkt_id=value)
            elif field.is_serialized:
                # It is a pickled string that has to be converted into an
                # object
                value = _unpickle(value)
        elif value == '':
            value = None # we need None and not empty string
        
        attribute_name = field.display_name or field.name
        setattr(inst, attribute_name, value)
    
    @classmethod
    def _get_value_of_field(cls, field, inst=None, value=None):
        """Gets the value of the instance (inst) field, taking care of
        converting it to the right db type, according to the type
        specified in the field. Used to get instance attribute and
        write them to the db. If value is supplied will only perform
        type conversions."""
        assert inst is not None or value is not None
        if value is None and inst is not None:
            value = getattr(inst, field.display_name or field.name)
        if isinstance(field, Relation):
            if value is not None:
                value = getattr(value, field.relation_pk.name)
        elif field.is_date or field.is_datetime:
            if value is not None:
                value = to_timestamp(value)
        elif field.is_ticket:
            if value is not None:
                value = value.id
        elif field.is_serialized:
            if value is not None:
                value = _pickle(value)
        return value

    def _update_old_values(self):
        # Updates the old values to the current values
        for f in self._fields:
            self._old[f] = getattr(self, f)
        self._changed = False

    def _reset_current_values(self):
        # Reset the current values from the old values
        for f, v in self._old.items():
            setattr(self, f, v)
        self._changed = False

    def _load(self, db=None):
        """Loads the object from the database given some specific key values,
        it is 'private' because the object should be able to load itself, 
        given the keys in the constructor"""
        debug(self, "DB Connection: %s" % db)
        db, handle_ta = get_db_for_write(self.env, db)
        try:
            cursor = db.cursor()
            keys, filter = self._get_filter()
            #debug(self, "LOAD => Executing Query: %s%s (%s)" % (self.SQL_S, filter, keys))
            safe_execute(cursor, self.SQL_S + filter, keys)
            # This is a safe guard against bad SQL - we want to load a specific
            # object from the db - if we have more than one, this is guaranteed
            # to be an error!
            rows = cursor.fetchall()
            if len(rows) > 1:
                sql = self.SQL_S + filter
                msg = 'Got multiple rows for primary keys. Please report that wrong SQL was generated: ' + repr(sql)
                self.env.log.error(msg)
                raise TracError(msg)
            #debug(self, "Read from DB: %s" % to_unicode(rows))
            if len(rows) == 1 or len(rows) > 0:
                row = rows[0]
                for i, f in enumerate(self._fields):
                    value = row[i]
                    field = self._fields[f]
                    self._set_value_of_field(self, self.env, value, field, db=db)
                self._exists = True
                # debug(self, "Read object from the DB! %s" % to_unicode(self))
                self._update_old_values()
                return True
        except Exception, e:
            raise
            self.env.log.exception(e)
            raise UnableToLoadObjectError(_("An error occurred while loading %s from the database: %s") % \
                                            (self.__class__.__name__, to_unicode(e)))
        return False
    
    def _assert_exactly_one_line_was_changed(self, result, sql):
        # Actually PEP 249 specifies 'cursor.rowcount' to get the number of
        # 'affected rows'.
        # However for MySQL there is a difference between matched and changed,
        # and by default it returns the number of changed rows.
        # A more detailed explanation of MySQL's behavior is in this article:
        # http://answers.oreilly.com/topic/168-how-to-obtain-the-number-of-rows-affected-by-a-statement-in-mysql/
        # 
        # Actually .save() has a different dirty tracking (_changed) and we 
        # should only issue SQL that does something... However it looks like 
        # this dirty tracking is currently (May 2010) faulty. I don't want to
        # invest much time in our ORM that we like to replace anyway - therefore
        # for now I just do something for sqlite in the hope it finds our bugs.
        # Also using 'changed' rows instead of 'matched' might be a problem if
        # there are two concurrent, identical changes so the second user does 
        # not change anything.
        if not hasattr(result, 'rowcount'):
            return
        
        nr_of_changed_lines = result.rowcount
        if nr_of_changed_lines == -1:
            # -1 means that the DB was unable to determine the number of 
            # affected rows as per Python DB API specification (PEP 249)
            return
        if nr_of_changed_lines != 1:
            # somehow we didn't change one single row
            message = _("%s rows affected while saving ticket %s with sql <%s> (sql not quoted)") % (nr_of_changed_lines, self, sql)
            raise UnableToSaveObjectError(message)
    
    def _db_parameters_including_keys(self, keys):
        db_param_names = {}
        params = self._get_params()
        for user_field_name, field_value in params.items():
            db_name = self._fields[user_field_name].name
            db_param_names[db_name] = field_value
        db_param_names.update(keys)
        return db_param_names
    
    def _sql_and_parameters_for_update(self):
        params = self._get_params()
        keys, filter = self._get_filter()
        db_param_names = self._db_parameters_including_keys(keys)
        sql = self.SQL_U % \
            ', '.join([self._fields[f].as_key_value() for f in params]) + \
            filter
        db_param_names.update(keys) # adds the keys to the params
        debug(self, "SAVE => Executing Query: %s (%s)" % (sql, db_param_names))
        return sql, db_param_names
    
    def _sql_and_parameters_for_insert(self):
        # does not support only auto increment id field, 
        # add at least one other field to the table
        params = self._get_params(is_insert=True)
        keys = self._get_db_keys_and_ids(is_insert=True)[0]
        db_param_names = self._db_parameters_including_keys(keys)
        list_of_db_column_names = [self._fields[f].name for f in params]
        list_of_values_to_insert = [self._fields[f].as_param() for f in params]
        sql = self.SQL_I % (', '.join(list_of_db_column_names),
                            ', '.join(list_of_values_to_insert))
        debug(self, "SAVE => Executing Query: %s (%s)" % (sql, db_param_names))
        return sql, db_param_names
    
    def save(self, db=None):
        """Saves the object to the database, reuse the db connection in case is not none"""
        # REFACT: either returns or throws -> True/False return value is meaningless
        # AT: this is how trac works, and we decided at the time to implement the same
        # behavior
        db, handle_ta = get_db_for_write(self.env, db)
        try:
            cursor = db.cursor()
            if self.exists:
                if not self._changed: # There are changes
                    True
                sql, parameters = self._sql_and_parameters_for_update()
                result = safe_execute(cursor, sql, parameters)
                self._assert_exactly_one_line_was_changed(result, sql % parameters)
            else:
                sql, parameters = self._sql_and_parameters_for_insert()
                safe_execute(cursor, sql, parameters)
                if hasattr(self, '_id'):
                    self._id = db.get_last_id(cursor, self._table.name)
            if handle_ta:
                db.commit()
            debug(self, "Committed object %s to database!" % self.__class__.__name__)
            self._exists = True
            # updates the _old dictionary
            self._update_old_values()
            return True
        except Exception, e:
            # reset the values from _old dictionary
            self._reset_current_values()
            self.env.log.exception(e)
            raise UnableToSaveObjectError(_("An error occurred while saving %s to the database: %s") % \
                                            (self, exception_to_unicode(e)))
        return False
    
    def delete(self, db=None):
        """Deletes the current object from the DB"""
        db, handle_ta = get_db_for_write(self.env, db)
        try:
            cursor = db.cursor()
            ids, filter = self._get_filter()
            debug(self, "DELETE => Executing Query: %s (%s)" % (self.SQL_D + filter, ids))
            if ids is not None:
                safe_execute(cursor, self.SQL_D + filter, ids)
            else:
                safe_execute(cursor, self.SQL_D + filter)
            if handle_ta:
                db.commit()
            return True
        except Exception, e:
            self.env.log.exception(e)
            raise UnableToDeleteObjectError(_("An error occurred while deleting %s from the database: %s") % \
                                              (self.__class__.__name__, to_unicode(e)))
        return False
    
    @classmethod
    def _build_filter_for_select(cls, criteria):
        values = {}
        filter = ""
        if criteria is not None:
            conditions = []
            for attr, condition in criteria.items():
                field = cls._fields.get(attr)
                if field is None:
                    raise TypeError(_("Invalid Field name: %s") % attr)
                # Create a condition
                cond = Condition(condition)
                value = None
                
                if isinstance(field, Relation) and condition is not None and \
                    isinstance(condition, PersistentObject):
                    # we're looking for a relation
                    value = getattr(condition, field.relation_pk.name)
                    values[field.name] = value
                    conditions.append(format_condition(cls._table.name,
                                                       field.name,
                                                       cond.operator))
                if value is None:
                    if cond.is_multiple:
                        add_multiple_params_values(values, field.name, cond.operator,
                                                   cond.value, conditions)
                    else:
                        if cond.is_single:
                            values[field.name] = cond.value
                        conditions.append(format_condition(cls._table.name,
                                                           field.name,
                                                           cond.operator))
            # Finally add the filter
            filter = " WHERE " + " AND ".join(conditions)
        return filter, values
    
    @classmethod
    def select(cls, env, db=None, criteria=None, order_by=None, limit=None):
        """
        Selects Objects from the database, given the specified criteria. The
        criteria is expressed as a dictionary of condition (object fields) to be appended
        to the select query. The order_by adds the order in which results should
        be sorted. the '-' sign in front will make the order DESC. The limit parameter
        limits the results of the SQL query.
        
        Example::
            
            criteria = {'name': 'test', 'users': '> 3', 'team': TheTeam}
            order_by = ['-name', 'users']
            limit = 10
        """
        assert criteria is None or isinstance(criteria, dict)
        assert order_by is None or isinstance(order_by, list)
        assert env is not None and isinstance(env, Environment)
        assert limit is None or isinstance(limit, int)
        
        db, handle_ta = get_db_for_write(env, db)
        objects = []
        # This is used in the exception to communicate the last changed object
        obj = None
        try:
            filter, values = cls._build_filter_for_select(criteria)
            # Now compute the order if there
            if order_by:
                order_pairs = []
                for order_clause in order_by:
                    desc = False
                    if isinstance(order_clause, basestring) and \
                            order_clause.startswith('-'):
                        order_clause = order_clause[1:]
                        desc = True
                    field = cls._fields.get(order_clause)
                    if field is None:
                        raise TypeError(_("Invalid Field name: %s") % order_clause)
                    if isinstance(field, Relation):
                        # we're looking for a relation
                        raise NotImplementedError("Lookup to related objects attributes not yet implemented!")
                    order_pairs.append('%s%s' % (field.name, desc and ' DESC' or ''))
                if len(order_pairs) > 0:
                    filter = filter + " ORDER BY " + ", ".join(order_pairs)
                    
            if limit:
                filter = filter + " LIMIT %d" % limit
            
            cursor = db.cursor()
            debug(env, "SELECT => Executing Query: %s %s" % (cls.SQL_S + filter, values))
            safe_execute(cursor, cls.SQL_S + filter, values)
            for row in cursor:
                obj = cls(env, load=False)
                for i, f in enumerate(cls._fields):
                    value = row[i]
                    field = cls._fields[f]
                    cls._set_value_of_field(obj, env, value, field)
                obj._exists = True
                obj._update_old_values()
                objects.append(obj)
        except Exception, e:
            env.log.exception(e)
            raise UnableToLoadObjectError(_("An error occurred while getting %s from the database: %s") % \
                                            (obj, to_unicode(e)))
        return objects
    
    def as_dict(self):
        """Utility function to return the current object attributes values as a 
        dictionary of attr:value to be used as value object."""
        attrs = {}
        for attr in dir(self):
            attr_value = getattr(self, attr)
            if isinstance(attr_value, PersistentObjectModelManager):
                continue
            if not attr.startswith('_') and not callable(attr_value) and \
                    not attr.startswith('SQL') and not attr in ('env', 'log'):
                # AT: we do not make any data conversion here, cause the
                # format of numbers and dates may be different on the 
                # client, therefore the views should take care of the
                # display part of it.
                transformed_value = attr_value
                if hasattr(attr_value, 'as_dict') and \
                        callable(getattr(attr_value, 'as_dict')):
                    transformed_value = attr_value.as_dict()
                elif isinstance(attr_value, list):
                    def as_dict_if_possible(an_object):
                        if hasattr(an_object, 'as_dict'):
                            return an_object.as_dict()
                        else:
                            return an_object
                    transformed_value = map(as_dict_if_possible, attr_value)
                attrs[attr] = transformed_value
        return attrs


class PersistentObjectManager(Component):
    """Component to take care of the initialization of PersistentObjects"""
    
    def __init__(self, *args, **kwargs):
        """Initialize the component"""
        super(PersistentObjectManager, self).__init__(*args, **kwargs)
        self._tables = dict()
    
    def exists_table(self, po_class):
        """Checks if the given persistent object has already a table"""
        assert po_class is not None and issubclass(po_class, PersistentObject)
        if self._tables.has_key(po_class._table.name):
            return True
        else:
            db = self.env.get_db_cnx()
            cursor = db.cursor()
            try:
                safe_execute(cursor, po_class.SQL_S)
                self._tables[po_class._table.name] = po_class._table
                return True
            except Exception:
                db.rollback()
        return False

    def create_table(self, po_class):
        """Creates a table in the database for the given PersistentObject"""
        assert po_class is not None and issubclass(po_class, PersistentObject)
        if not self.exists_table(po_class):
            try:
                debug(self, "Creating table: %s with columns: %s" % \
                      (po_class._table.name, po_class._table.columns))
                create_table(self.env, po_class._table)
                return True
            except Exception, e:
                warning(self, "Table Already Existing: %s" % to_unicode(e))
        return False


def add_as_dict(original_class):
    """Class decorator that will add the as_dict method to the given 
    class. The class decorator are available only in python 2.6."""
    def __init__(self, *args, **kwargs):
        original_class.__init__(self, *args, **kwargs)
        original_class.as_dict = PersistentObject.as_dict
        # replace original class init
        original_class.__init__ = __init__

    return original_class


class PersistentObjectModelManager(Component):
    """
    Default PersistentObject Model Manager, uses specific PersistentObject
    Properties to create unique identifier and uses the SimpleModelCache as
    cache manager.
    """
    implements(IModelManager)
    abstract = True
    # override in subclassing
    model = None
    
    def __init__(self, *args, **kwargs):
        """Sets thread local cache using a SimpleModelCache"""
        self._tls = threading.local()
    
    def for_model(self):
        return self.model
    
    def _get_model_key(self, model_instance=None):
        """Returns a unique identifier (tuple) for the given model instance, or 
        return the list of the properties needed to set a key for the model
        Managed by this Manager."""
        # at: cluster the key as a single tuple (key1,key2..) and the
        # unique constraints can be "together" in a tuple or just as
        # single entries, than a key looks like: 
        # ((key1,key2), unique, (unique, together))
        keys_unique = list()
        if isinstance(model_instance, PersistentObject):
            # collect keys and unique identifier for the model_instance
            keys_unique.append(tuple([PersistentObject._get_value_of_field(key, model_instance) \
                                      for key in model_instance._keys.values()]))
            if hasattr(model_instance, '_uniques'):
                for unique in model_instance._uniques.values():
                    keys_unique.append(PersistentObject._get_value_of_field(unique,
                                                                            model_instance))
            else:
                keys_unique.append(None)
            # in case of instance must be an hash-able object
            return tuple(keys_unique)
        else:
            # collect only properties
            keys_unique.append(self.model._keys.keys())
            if hasattr(self.model, '_uniques'):
                keys_unique += self.model._uniques.keys()
            else:
                keys_unique.append(None)
            return keys_unique
    
    def get(self, load=False, **kwargs):
        """
        Returns the PersistentObject instance corresponding to the given
        parameters if existing, or None. In case the object is already stored
        in the cache, returns it from there.
        """
        def _find_in_kwargs(item, all=False):
            """
            Find at least one or all of the item in the param in 
            the kwargs, and returns the list of the matching ones, or
            None
            """
            result = []
            if isinstance(item, (list, tuple)):
                for piece in item:
                    partial_result = _find_in_kwargs(piece, all=True)
                    if partial_result:
                        result += partial_result
            elif item in kwargs:
                result.append(kwargs[item])
            elif all:
                result = None
            return result

        if not load:
            # get the cache key format
            l = []
            cache_key = self._get_model_key()
            assert len(cache_key) == 2, "The cache key is missing a part %s" % cache_key
            pk, constraints = cache_key
            # it should come out at least with _id
            l_pk = _find_in_kwargs(pk, all=True)
            # empty list is a valid tuple!!!
            if l_pk is not None:
                l_pk = tuple(l_pk)
            l.append(l_pk)
            # constraints can be None, but we still need to have an empty
            # position in the key
            l_constraints = _find_in_kwargs(constraints or [])
            if l_constraints is not None:
                l_constraints = tuple(l_constraints)
            l.append(l_constraints)
            # try to get it from the cache
            m = self.get_cache().get(tuple(l))
            if m:
                return m
        # Not in cache
        m = self.model(self.env, **kwargs)
        if m.exists:
            self.get_cache().set(self._get_model_key(m), m)
            return m
    
    def create(self, save=True, **kwargs):
        """Creates a new model, given the properties passed and return 
        it. The Model is also cached in the local cache"""
        m = self.model(self.env, **kwargs)
        
        if m.exists:
            # Already existing, we return None, it can be recreated
            return None
        # Now should set all the attribute passed into the parameters which are
        # not None, in the creation of a model may overwrite automatically set
        # values.
        for attr, value in kwargs.items():
            if value and hasattr(m, attr) and not callable(getattr(m, attr)):
                setattr(m, attr, value)
        # check if we have to save it or return it as is
        if save:
            # It is a new model we save it
            self.save(m)
        return m
    
    def create_or_get(self, save=True, **kwargs):
        """Tries to create the new instance and if it is already existing
        returns it"""
        m = self.create(save=save, **kwargs)
        if not m:
            # is probably already existing
            m = self.get(**kwargs)
        return m
        
    def delete(self, model_instance, db=None):
        """Deletes the model_instance from the DB and from the cache"""
        if model_instance:
            removed = self.get_cache().invalidate(model_instance=model_instance)
            # fs: The condition could actually made a bit less strict because
            # we can delete a model instance even when it is not in the cache:
            # if (not removed) or (removed == model_instance):
            # However the current form may catch more errors in the cache 
            # handling because these objects won't be deleted so I'll leave it 
            # like it is currently.
            if removed and (removed == model_instance):
                return removed.delete(db=db)
        return False
    
    def save(self, model_instance, **kwargs):
        """Saves the model instance"""
        res = model_instance.save(**kwargs)
        # if the saving succeeded, and the model is now saved we want to cache it
        if model_instance.exists:
            # now store into the cache
            self.get_cache().set(self._get_model_key(model_instance), model_instance)
        return res
    
    def select(self, criteria=None, order_by=None, limit=None, db=None):
        """Returns the list of objects matching the criteria"""
        objects = self.model.select(self.env, criteria=criteria, order_by=order_by,
                                    limit=limit, db=db)
        # AT: this solves the object_identity issue, and allows to use the
        # cache also from the select. It could be optimized by moving the
        # static method select from the PersistentObject to the ModelManager
        # and take care of caching directly while loading from the db.
        for obj in objects:
            key = self._get_model_key(obj)
            self.get_cache().set(key, obj)
        return objects
    
    def get_cache(self):
        """
        Returns the instance of SimpleModelCache bound to the current
        Thread object
        """
        if not hasattr(self._tls, 'cache'):
            self._tls.cache = SimpleModelCache()
        return self._tls.cache


class Condition(object):
    """Represent a select criteria condition"""
    def __init__(self, condition):
        self._condition = condition
        self._operator = '='
        self._value = ''
        if isinstance(self._condition, basestring):
            self._value = self._condition
        self._is_multiple = False
        self._evaluate()

    def __str__(self):
        return "%s:%s" % (self.operator, self.value)

    def __repr__(self):
        return "%s:%s" % (repr(self.operator), repr(self.value))

    @property
    def operator(self):
        return self._operator

    @property
    def value(self):
        return self._value

    @property
    def is_multiple(self):
        return self._is_multiple

    @property
    def is_single(self):
        return not self._is_multiple

    def _evaluate_multiple_condition(self):
        """Evaluates if the condition is a multiple set condition, returns
        the operator,value pair, where the operator is the operator part of
        the condition and the value the value part. In case the condition is
        not a multiple one, the value returned contains the condition and the
        operator is None."""
        value = self._value
        operator = None
        match = re.match(r'((not)?\s?in)\s*[\[|\(](.+(\s,)?)+[\]|\)]', value)
        if match:
            operator = match.group(1)
            # FIXME (AT): dangerous eval without try/except
            value = eval(match.group(3))
        return operator, value

    def _evaluate_single_condition(self):
        """Evaluates if the condition is single and can be transformed into
        an operator, value pair. In case it is not the operator is returned
        as None, and the value is containing the condition."""
        value = self._value
        operator = self._operator
        match = re.match(r'(!=|<>|>=|<=)\s*', value)
        if not match:
            match = re.match(r'(=|>|<)\s*', value)
        # get operators from condition and remove
        if match:
            operator = match.group(1)
            value = value.replace(match.group(0), '', 1)
        return operator, value

    def _evaluate(self):
        """Returns operator, value, multiple tuple for the given condition
        to be evaluated, so thase can be used to build a SQL query. If it is
        a multiple condition the value multiple is True otherwise False."""
        if self._condition is None:
            self._operator = None
            self._value = None
        else:
            operator, value = self._evaluate_multiple_condition()
            if operator:
                self._is_multiple = True
                self._operator = operator
                # Protect against single value in the inclusion, the caller
                # will expect a list
                if not isinstance(value, (tuple, list)):
                    value = [value]
                self._value = value
            else:
                self._operator, self._value = self._evaluate_single_condition()
