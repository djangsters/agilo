# -*- coding: utf-8 -*-
#   Copyright 2008 Agile42 GmbH - Andrea Tomasini
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
# Authors:
#     - Felix Schwarz <felix.schwarz__at__agile42.com>
#     - Andrea Tomasini <andrea.tomasini__at__agile42.com>

from datetime import datetime
import inspect
import string
import xmlrpclib

import trac.ticket.model as model

from trac.core import TracError, Component, implements
from trac.resource import Resource
import trac.ticket.model
from trac.util.datefmt import to_timestamp
from trac.util.translation import _

from agilo.core import PersistentObjectModelManager, \
    UnableToLoadObjectError, safe_execute, add_multiple_params_values, \
    Condition, format_condition
from agilo.ticket.api import AgiloTicketSystem
from agilo.ticket.links import LINKS_TABLE
from agilo.ticket.links.model import LinksConfiguration
from agilo.utils import Key, Realm
from agilo.utils.compat import exception_to_unicode
from agilo.utils.db import get_db_for_read, get_db_for_write
from agilo.utils.config import AgiloConfig, get_label
from agilo.ticket.links import LinkOption
from agilo.utils.log import debug, error, warning
from agilo.utils.sorting import By, Column, SortOrder
from agilo.ticket.renderers import Renderer

__all__ = ['AgiloTicket']


TICKET_COLUMNS = ['id', 'type', 'time', 'changetime',
                  'component', 'severity', 'priority', 
                  'owner', 'reporter', 'cc', 'version',
                  'milestone', 'status', 'resolution',
                  'summary', 'description', 'keywords']


class TicketValueWrapper(dict):
# Trac accesses ticket.values directly sometimes (especially in 
# _init_defaults). However we need to intercept type changes to use 
# the right list of ticket fields so we use this wrapper.
    def __init__(self, ticket):
        dict.__init__(self)
        self._ticket = ticket
    
    def __setitem__(self, name, value):
        # FIXME: (AT) This doesn't make sense as the change of type will happen 
        # through the normal setter, Trac will cycle through the values and set
        # the changed ones, in case of type, will generate another reset of the
        # fields.
        if name == Key.TYPE:
            self._ticket._reset_type_fields(value)
        dict.__setitem__(self, name, value)
    
    def setdefault(self, name, value):
        if (name == Key.TYPE) and (Key.TYPE not in self):
            # FIXME: (AT) This is called from init_defaults when the ticket
            # initializes and for the third time we call _reset_type_fields
            self._ticket._reset_type_fields(value)
        dict.setdefault(self, name, value)

has_tracrpc = False
try:
    import tracrpc
    from tracrpc.api import Binary
    from tracrpc.api import IXMLRPCHandler
    has_tracrpc = True
except:
    pass

if has_tracrpc:
    xmlrpclib.Marshaller.dispatch[TicketValueWrapper] = xmlrpclib.Marshaller.dump_struct
    
    def getTicketFields(self, req):
        ats = AgiloTicketSystem(self.env)
        fields = ats.get_ticket_fields(t_type="task")
        return fields
    
    tracrpc.ticket.TicketRPC.getTicketFields = getTicketFields
    
    def query(self, req, qstr='status!=closed'):
        import trac.ticket.query as ticket_query
        q = ticket_query.Query.from_string(self.env, qstr)
        ticket_realm = Resource('ticket')
        out = []
        for t in q.execute(req):
            tid = t['id']
            if 'TICKET_VIEW' in req.perm(ticket_realm(id=tid)) and str(t['type']) == 'task':
                out.append(tid)
        return out

    tracrpc.ticket.TicketRPC.query = query
    
    def getAll(self, req):
        for i in model.Type.select(self.env):
            if i.name == 'task':
                yield i.name
    getAll.__doc__ = """ Get a list of all ticket type names. """
    
    from tracrpc import XMLRPCSystem
    for i in range(len(XMLRPCSystem._registry[IXMLRPCHandler])):
        handler = XMLRPCSystem._registry[IXMLRPCHandler][i]
        if handler.__name__ == 'TypeRPC' and handler.__module__ == 'tracrpc.ticket':
            XMLRPCSystem._registry[IXMLRPCHandler][i].getAll = getAll
            break
    for i in range(len(XMLRPCSystem._components)):
        component = XMLRPCSystem._components[i]
        if component.__name__ == 'TypeRPC' and component.__module__ == 'tracrpc.ticket':
            XMLRPCSystem._components[i].getAll = getAll
            break


class AgiloTicket(trac.ticket.model.Ticket):
    """Represent a typed ticket, with Link capabilities as well as 
    aliases and properties check. It wraps the standard Trac Ticket."""
    
    def __init__(self, env, tkt_id=None, db=None, version=None, t_type=None, load=False):
        """Initializes an AgiloTicket, making sure that there are only 
        the fields allowed for this type"""
        if not AgiloConfig(env).is_agilo_enabled:
            super(AgiloTicket, self).__init__(env, tkt_id=tkt_id, db=db, version=version)
            return
        
        self.env = env
        if tkt_id is not None:
            tkt_id = int(tkt_id)

        self.tm = AgiloTicketModelManager(self.env)
        self.ats = AgiloTicketSystem(self.env)
        
        self.resource = Resource(Realm.TICKET, tkt_id, version)
        self.values = TicketValueWrapper(self)
        self._old = {}
        # Links lists
        self._incoming = dict()
        self._outgoing = dict()
        # ticket fields
#        from trac.ticket.api import TicketSystem
#        fields = TicketSystem(self.env).get_ticket_fields()
        self.std_fields = self.custom_fields = []
#        for f in fields: 
#            if f.get('custom'): 
#                self.custom_fields.append(f['name']) 
#            else: 
#                self.std_fields.append(f['name']) 
        self.fields = None
        # self._calculated contains a dictionary (key is the calculated property 
        # name, value the operator callable to compute the value).
        self._calculated = None
        self._alloweds = self._sort = self._show_on_link = None
        if tkt_id is not None:
            self._fetch_ticket(tkt_id, db=db, t_type=t_type)
            return
        
        self.id = None
        if t_type is not None:
            self[Key.TYPE] = t_type
        else:
            # Unknown type, load all the fields
            self.fields = self.ats.get_ticket_fields()
        self.time_fields = self._time_fields()
        # FIXME: (AT) This reset the ticket type to task if it is empty
        # and it is already done in the line above by the ticket system
        # so it is twice reinitialized if t_type is None
        if AgiloTicketSystem.is_trac_1_0():
            self._init_defaults()
        else:
            self._init_defaults(db)
    
    def _time_fields(self):
        return [field['name'] for field in self.fields if field['type'] == 'time']
    
    # OVERRIDE Trac 0.12
    time_created = property(lambda self: self.values.get('time'), 
                            lambda self, value: self.values.__setitem__('time', value))
    
    def _set_time_changed(self, value):
        """Set the local time_changed attribute, removing the microsecond
        precision"""
        if AgiloConfig(self.env).is_agilo_enabled:
            # Need to remove microsecond precision because trac 
            # doesn't do if a ticket is kept in memory the validation 
            # will fail because of the microseconds.
            if isinstance(value, datetime):
                value = value.replace(microsecond=0)
        self.values.__setitem__('changetime', value)
    # OVERRIDE Trac 0.12
    time_changed = property(lambda self: self.values.get('changetime'), 
                            lambda self, value: self._set_time_changed(value))
    
    # OVERRIDE
    def _fetch_ticket(self, tkt_id, db=None, t_type=None):
        """Overrides the trac method to reset the ticket fields for the 
        type"""
        if not AgiloConfig(self.env).is_agilo_enabled:
            if AgiloTicketSystem.is_trac_1_0():
                return super(AgiloTicket, self)._fetch_ticket(tkt_id)
            else:
                return super(AgiloTicket, self)._fetch_ticket(tkt_id, db=db)
        if not t_type:
            t_type = self._get_type(tkt_id, db)
        self._reset_type_fields(t_type)
        
        if AgiloTicketSystem.is_trac_1_0():
            self.std_fields = self.values.keys()
            self.std_fields.append('id')
            self.std_fields.append('type')
            for f in self.fields:
                if f.get(Key.CUSTOM, False):
                    self.custom_fields.append(f['name'])

        super(AgiloTicket, self)._fetch_ticket(tkt_id)
        # Check if the team members should be set in the owner field
        self._set_team_members()
    
    @property
    def fields_for_type(self):
        """Returns the list of alloweds fields for this type of ticket"""
        return AgiloConfig(self.env).TYPES.get(self.get_type(), [])
    
    def _set_team_members(self, sprint_name=None):
        """
        Sets a list of team members that are member of the team to 
        which the Sprint of this ticket has been assigned. If the 
        ticket has no Sprint assigned it does nothing.
        """
        debug(self, "Called _set_team_members() => '%s'" % \
                    (sprint_name or self[Key.SPRINT]))
        ats = AgiloTicketSystem(self.env)
        if ats.restrict_owner and Key.SPRINT in self.fields_for_type:
            ats.eventually_restrict_owner(self.get_field(Key.OWNER), 
                                          ticket=self,
                                          sprint_name=sprint_name)
    
    def _update_values_from_fields_on_type_change(self, t_type):
        # We need to fill self.values as well - otherwise trac 
        # might store NULL values for standard fields upon 
        # ticket.insert() and there is an implicit assumption in 
        # trac's property change rendering that no field is None.
        for field in self.fields:
            name = field[Key.NAME]
            is_custom_field = field.get(Key.CUSTOM, False)
            field_already_present = (name in self.values)
            if field_already_present or is_custom_field or name == Key.TYPE:
                # don't overwrite existing values and we don't need to check 
                # for custom fields to satisfy trac's assumption that all 
                # standard fields are not None but without this check we will 
                # create at least two additional rows with empty values in the 
                # db every time.
                continue
            elif name == Key.RESOLUTION:
                # trac has a special case not to set resolution for new tickets
                # so we should not fill in a default resolution upon type change
                # resolution is a default trac field so it must not be None
                self.values[Key.RESOLUTION] = ''
                continue
            self.values[name] = field.get(Key.VALUE, '')
        #AT: we also need to remove from the _old keys anything which is not
        # matching the current ticket type, or trac will try to save the not
        # found custom properties as ticket table members
        # we need to reload it separately because here the new type is not yet
        # set
        fields_for_new_type = AgiloConfig(self.env).TYPES.get(t_type, [])
        for key in self._old.keys():
            if key not in fields_for_new_type:
                debug(self, u'Removing %s from ticket fields: %s' % \
                      (key, self._old))
                del self._old[key]
        
    def _reset_type_fields(self, t_type):
        """Cleanup the local fields dictionary removing the fields which
        are not allowed for this type"""
        if not self.ats:
            self.ats = AgiloTicketSystem(self.env)
        # Normalize the ticket type
        t_type = self.ats.normalize_type(t_type)
        old_type = self.get_type()
        
        if old_type is not None and t_type == old_type:
            # No type change, inform the caller that is not needed to take 
            # any action
            return False
        
        # AT: removed the printout of self.fields_for_type as it generates
        # for every new ticket some DB query to try to identify the type,
        # and load from the AgiloConfig the appropriate fields.
        # get a ticket system
        self.fields = self.ats.get_ticket_fields(t_type)
        self.time_fields = [f['name'] for f in self.fields if f['type'] == 'time']
        self._update_values_from_fields_on_type_change(t_type)
        self._calculated, self._alloweds, self._sort, self._show_on_link = \
            self.ats.get_agilo_properties(t_type)
        # Inform the caller that there as been a change of type
        return True
    
    def __str__(self):
        """
        Returns an ASCII string representation of the AgiloTicket
        """
        if not AgiloConfig(self.env).is_agilo_enabled:
            return super(AgiloTicket, self).__str__()
        return '<%s #%d (%s)>' % (self.__class__.__name__, 
                                  self.get_id(), 
                                  repr(self.get_type()))
    
    def __repr__(self):
        """Returns the representation for this AgiloTicket"""
        if not AgiloConfig(self.env).is_agilo_enabled:
            return super(AgiloTicket, self).__repr__()
        return '<%s@%s #%d (%s)>' % (self.__class__.__name__,
                                     id(self), 
                                     self.get_id(), 
                                     repr(self.get_type()))
    
    def get_id(self):
        """Returns the id of the ticket"""
        return self.id or 0
    
    def get_type(self, tkt_id=None, db=None):
        """Returns the ticket type"""
        t_type = self[Key.TYPE]
        if not t_type and (tkt_id or (hasattr(self, 'id') and self.id)):
            # if we have an id, try to get it from there
            t_id = tkt_id or self.id
            if t_id is not None:
                t_type = self._get_type(t_id, db)
                
        return t_type
    
    def get_field(self, field_name):
        """Returns the field dictionary corresponding to the given 
        field_name. If not found returns None."""
        if field_name in (None, ''):
            return None
        
        if field_name in self.get_calculated_fields_names():
            return self.get_calculated_field(field_name)
        
        for f in self.fields:
            if f[Key.NAME] == field_name:
                return f
        return None
    
    def is_readable_field(self, field_name):
        """
        Return True if the given field name is allowed for this ticket 
        type
        """
        return (field_name in self.get_calculated_fields_names()) or \
                self.get_field(field_name) is not None
    
    # REFACT: want other methods to check is_task_container etc, but not sure yet how to do it.
    def is_task_like(self):
        return self.is_writeable_field(Key.REMAINING_TIME)
    
    def is_writeable_field(self, field_name):
        """
        Return True if the given field name is allowed for this 
        ticket type
        """
        return self.get_field(field_name) is not None
    
    @property
    def has_owner(self):
        """Returns true if this ticket has an owner set"""
        if self.is_readable_field(Key.OWNER):
            return self[Key.OWNER] not in ('', None)
        return False
    
    def get_resource_list(self, include_owner=False):
        """
        Returns a list of resources for this ticket. If the ticket 
        has no resource field (or it is empty), this method will 
        return an empty list.
        If include_owner is True (default False), the owner (if 
        present) will be included in the resource list. If the owner 
        is already in the list of resources, he won't be included 
        twice.
        """
        resource_list = list()
        if include_owner and (self[Key.OWNER] not in [None, '']):
            resource_list.append(self[Key.OWNER].strip())
        
        resource_string = self[Key.RESOURCES] or ''
        for resource in resource_string.split(','):
            resource = resource.strip()
            if len(resource) > 0 and (resource not in resource_list):
                resource_list.append(resource)
        return resource_list
    
    def get_sprint(self):
        """
        Loads the Sprint from the database and returns it (as Python 
        instance, not the sprint name) if this ticket has a sprint configured
        (return None otherwise).
        """
        if self[Key.SPRINT] != None:
            if not hasattr(self, '_sprint'):
                setattr(self, '_sprint', None)
            if self._sprint is None or \
                    self[Key.SPRINT] != self._sprint.name:
                # sprint is changed
                from agilo.scrum.sprint import SprintModelManager
                self._sprint = SprintModelManager(self.env).get(name=self[Key.SPRINT])
            return self._sprint
        return None
    
    def get_alias(self, ticket_type=None):
        """Returns the type alias for this ticket"""
        if ticket_type is None:
            ticket_type = self.get_type()
        return AgiloConfig(self.env).ALIASES.get(ticket_type, None)
    
    def get_label(self, name=None):
        label = AgiloConfig(self.env).LABELS.get(name, None)
        if label is None:
            label = get_label(name)
        return label
    
    def get_alloweds(self):
        """Returns a list of all the allowed end points for linking"""
        return self._alloweds.values()
        
    def is_link_to_allowed(self, end_point):
        """
        Returns True if the link between this endpoint type and 
        the given end_point type is allowed.
        """
        debug(self, u"Self Type: %s, Dest Type: %s, Alloweds: %s" % \
                    (self.get_type(), end_point.get_type(), 
                     self.get_alloweds()))
        return end_point.get_type() in [t.get_dest_type() for t in \
                                        self.get_alloweds()]
        
    def is_link_from_allowed(self, end_point):
        """
        Returns True if the link between the given endpoint type 
        and this endpoint type is allowed.
        """
        return end_point.is_link_to_allowed(self)
    
    def get_calculated_fields(self):
        """
        Returns a list of the calculated fields for this ticket. 
        You should be aware that the value of a calculated field may 
        change but the value in the dict previously returned won't be 
        updated.
        
        Attention: Calling this method can be extremely expensive 
        because it needs to calculate the value of every calculated 
        property which may trigger loading of linked tickets. This may 
        turn out quite expensive as long there is no object identity 
        in our database abstraction layer!
        """
        calculated_fields = list()
        for name in self.get_calculated_fields_names():
            field_dict = self.get_calculated_field(name)
            calculated_fields.append(field_dict)
        return calculated_fields
    
    def get_calculated_field(self, name):
        """
        Returns the field dictionary for the given calculated property. 
        Raises a KeyError if no such field exists.
        """
        if name not in self.get_calculated_fields_names():
            raise KeyError(name)
        field_dict = {Key.NAME: name, Key.VALUE: self[name], 
                      Key.LABEL: self.get_label(name), 
                      Key.RENDERED: Renderer(self, name)}
        return field_dict
    
    def get_calculated_fields_names(self):
        """
        Returns the list of the calculated field names for this ticket.
        """
        if hasattr(self, '_calculated') and self._calculated:
            return self._calculated.keys()
        return []
    
    def is_linked_to(self, end_point):
        """
        Returns True if self is linked to the given end_point. To 
        check the existence of the link, given the time of propagation 
        needed by the Trac extension points, it checks first the to 
        endpoints incoming and outgoing link caches, and than checks 
        on the db directly.
        """
        debug(self, u"Called %s.is_linked_to(%s)" % (self, end_point))
        if not self._outgoing.has_key(end_point.get_id()) \
           and not end_point._incoming.has_key(self.get_id()):
            debug(self, u"Called %s._is_link(%d, %d)" % \
                  (self, self.get_id(), end_point.get_id()))
            return self._is_link(self.get_id(), end_point.get_id())
        return True
        
    def is_linked_from(self, end_point):
        """
        Returns True if the given end_point is linked to self. To 
        check the existence of the link, given the time of propagation 
        needed by the Trac extension points, it checks first the to 
        endpoints incoming and outgoing link caches, and than checks 
        on the db directly.
        """
        debug(self, u"Called %s.is_linked_from(%s)" % (self, 
                                                       end_point))
        if not self._incoming.has_key(end_point.get_id()) \
           and not end_point._outgoing.has_key(self.get_id()):
            debug(self, u"Called %s._is_link(%d, %d)" % \
                  (self, end_point.get_id(), self.get_id()))
            return self._is_link(end_point.get_id(), self.get_id())
        return True
    
    def link_to(self, end_point, db=None):
        """Creates an outgoing link to the given endpoint."""
        handle_ta = False
        # Check if the end_point is a new ticket not yet inserted
        if end_point.id is None and db is None:
            db, handle_ta = get_db_for_write(self.env, db=db)
        # Creates the database link
        if self.is_link_to_allowed(end_point):
            # If the end_point is new we have to save it first
            if end_point.id is None:
                end_point.insert()
            if not self.is_linked_to(end_point):
                try:
                    self._create_link(self.get_id(), 
                                      end_point.get_id(), db)
                    self._outgoing[end_point.get_id()] = end_point
                    end_point._incoming[self.get_id()] = self
                    debug(self, u"Link created: %s => %s" % \
                          (self, end_point))
                    debug(self, u"Check is linked: %s" % \
                          self.is_linked_to(end_point))
                    if handle_ta:
                        db.commit()
                    return True
                except Exception, e:
                    error(self, exception_to_unicode(e))
            else:
                error(self, "Link failed: %s => %s, the link is " \
                      "already existing!" % (self, end_point))
        else:    
            error(self, "Link failed: %s => %s, the link is not " \
                  "allowed!" % (self, end_point))
        # Roll back if db was created here
        if handle_ta:
            db.rollback()
        return False
        
    def link_from(self, end_point, db=None):
        """Creates an incoming link to the given endpoint."""
        handle_ta = False
        # Check if the end_point is a new ticket not yet inserted
        if end_point.id is None and db is None:
            db, handle_ta = get_db_for_write(self.env, db=db)
        # Creates the database link
        if self.is_link_from_allowed(end_point):
            # If the end_point is new we have to save it first
            if end_point.id is None:
                end_point.insert()
            if not self.is_linked_from(end_point):
                try:
                    self._create_link(end_point.get_id(), 
                                      self.get_id(), db)
                    self._incoming[end_point.get_id()] = end_point
                    end_point._outgoing[self.get_id()] = self
                    debug(self, u"Link created: %s <= %s" % \
                          (self, end_point))
                    debug(self, u"Check is linked: %s" % \
                          self.is_linked_from(end_point))
                    if handle_ta:
                        db.commit()
                    return True
                except Exception, e:
                    error(self, exception_to_unicode(e))
            else:
                error(self, "Link failed: %s <= %s, the link is " \
                      "already existing!" % (self, end_point))
        else:
            error(self, "Link failed: %s <= %s, the link is not " \
                  "allowed!" % (self, end_point))
        # Roll back if db was created here
        if handle_ta:
            db.rollback()
        return False
        
    def del_link_to(self, end_point, db=None):
        """Deletes the outgoing link to the specified endpoint."""
        # Make sure the links are loaded if needed
        self.get_outgoing()
        try:
            # Delete the link from the DB
            self._delete_link(src=self.get_id(), 
                              dest=end_point.get_id())
            self._outgoing.has_key(end_point.get_id())
            # Load incoming links if needed
            end_point.get_incoming()
            if end_point._incoming.has_key(self.get_id()):
                del end_point._incoming[self.get_id()]
            else:
                warning(self, "%s is linked to %s, but there is no " \
                        "incoming link..." % (self, end_point))
            del self._outgoing[end_point.get_id()]
            return True
        except:
            warning(self, "%s is not linked to %s, not deleting." % \
                    (self, end_point))
            return False
        
    def del_link_from(self, end_point, db=None):
        """Deletes the outgoing link to the specified endpoint."""
        # Make sure the links are loaded if needed
        self.get_incoming()
        try:
            self._delete_link(src=end_point.get_id(), 
                              dest=self.get_id())
            self._incoming.has_key(end_point.get_id())
            # Make sure the end_point links are loaded
            end_point.get_outgoing()
            if end_point._outgoing.has_key(self.get_id()):
                del end_point._outgoing[self.get_id()]
            else:
                warning(self, "%s is linked from %s, but there is " \
                        "no outgoing link..." % (self, end_point))
            del self._incoming[end_point.get_id()]
            return True
        except: 
            warning(self, "%s is not linked from %s, not deleting..." % (self, end_point))
            return False
    
    def _should_delete_linked_ticket(self, src_type, dest_type):
        links_configuration = LinksConfiguration(self.env)
        config = AgiloConfig(self.env)
        links = config.get_section(AgiloConfig.AGILO_LINKS)
        delete_pairs = dict([(l, list(links_configuration.extract_types(l))) for l in links.get_list(LinkOption.DELETE)])
        for key in delete_pairs.keys():
            if delete_pairs[key][0] == src_type and delete_pairs[key][1] == dest_type:
                return True
        return False
        
    
    def del_all_links(self, db=None):
        """Deletes all the links from this endpoint"""
        try:
            for dle in self.get_outgoing():
                if self._should_delete_linked_ticket(self.get_type(), dle.get_type()):
                    dle.delete(db=db)
            self._delete_all_links(self.get_id(), db=db)
            for dle in self.get_outgoing():
                dle.del_link_from(self, db=db)
            self._outgoing = dict()
            for sle in self.get_incoming():
                sle.del_link_to(self, db=db)    
            self._incoming = dict()
            return True
        except:
            return False
        
    def get_outgoing(self, db=None, force_reload=False):
        """Returns the list of outgoing links"""
        if hasattr(self, '_outgoing'):
            if hasattr(self, '_outgoing_loaded') and not force_reload:
                return self._outgoing.values()
            else:
                self._load_outgoing_links(db=db)
                self._outgoing_loaded = True
            return self._outgoing.values()
        self._outgoing_loaded = True
        return []

    def get_incoming(self, db=None, force_reload=False):
        """Returns the list of incoming links"""
        if hasattr(self, '_incoming'):
            if hasattr(self, '_incoming_loaded') and not force_reload:
                return self._incoming.values()
            else:
                self._load_incoming_links(db=db)
                self._incoming_loaded = True
            return self._incoming.values()
        self._incoming_loaded = True
        return []
    
    def _build_dict(self, agilo_ticket):
        """Returns the dictionary for the given end_point"""
        d_ep = {'id': agilo_ticket.get_id(),
                'type': agilo_ticket.get_alias(), # It will be used for display only
                'summary': agilo_ticket[Key.SUMMARY],
                'status': agilo_ticket[Key.STATUS]}
        
        # Now fills specific type field as Options
        if self._show_on_link is not None and \
                self._show_on_link.has_key(agilo_ticket.get_type()):
            debug(self, u"Link Fields: %s for type: %s" % \
                        (self._show_on_link[agilo_ticket.get_type()], 
                         agilo_ticket.get_type()))
            options = []
            for opt in self._show_on_link[agilo_ticket.get_type()]:
                val = agilo_ticket[opt]
                if val:
                    options.append((self.get_label(opt), val))
            if len(options) > 0:
                d_ep['options'] = options
        return d_ep
    
    def _add_links_to_serialized_dict(self, serialized_dict):
        for name, tickets in [('outgoing_links', self.get_outgoing()), 
                              ('incoming_links', self.get_incoming())]:
            serialized_dict[name] = []
            for ticket in tickets:
                serialized_dict[name].append(ticket.id)
    
    def as_dict(self):
        """Serialize this ticket in a dictionary. This dictionary does not 
        contain fields which are not allowed for this ticket type. Also the 
        returned dictionary contains the ID although it is not a real trac 
        'field'."""
        if self.id is None:
            raise ValueError('Ticket is not yet in the database.')
        dict_data = {Key.ID: int(self.id)}
        for field in self.fields:
            name = field[Key.NAME]
            if field.get(Key.SKIP) or name in ('time', 'changetime'):
                continue
            dict_data[name] = self[name]
            # We do not transmit the possible option values for select fields in
            # JSON as it makes the whole backlog load way bigger 
        for name in self.get_calculated_fields_names():
            dict_data[name] = self[name]
        self._add_links_to_serialized_dict(dict_data)
        dict_data['time_of_last_change'] = to_timestamp(self.time_changed)
        dict_data['ts'] = str(self.time_changed)
        if AgiloTicketSystem.is_trac_1_0():
            from trac.util.datefmt import to_utimestamp
            dict_data['view_time'] = str(to_utimestamp(self.time_changed))
        return dict_data
    
    @classmethod
    def as_agilo_ticket(cls, ticket):
        """Return the equivalent AgiloTicket instance for the specified ticket
        (even if it is a trac.Ticket."""
        if not isinstance(ticket, AgiloTicket):
            return AgiloTicket(ticket.env, ticket.id)
        return ticket
    
    def get_outgoing_dict(self):
        """
        Process the linked end point parameter applying the defined operator,
        an storing the result of the operation into the local end point variable
        result.
        """
        res = []
        outs = self.get_outgoing()
        # Sort the links by summary or by special property sort
        outs.sort(By(Column(Key.SUMMARY), SortOrder.DESCENDING))
        if len(outs) > 0 and self._sort and self._sort.has_key(outs[0].get_type()):
            props = self._sort.get(outs[0].get_type(), [])
            # We want the logical order of sort put in trac.ini to match the stable
            # sorting of python list sort
            opt = None
            for prop in props:
                if prop.find(':') != -1:
                    prop, opt = prop.split(':')
                debug(self, u"Sorting by: %s, desc: %s" % (prop, opt=='desc'))
                outs.sort(By(Column(prop), desc=(opt=='desc')))
        for ep in outs:
            res.append(self._build_dict(ep))
        debug(self, u"Sorted outgoing links: %s" % res)
        return res
        
    def get_incoming_dict(self):
        """Process the linked enpoint parameter applying the defined operator,
        an storing the result of the operation into the local endpoint variable
        result."""
        res = []
        for ep in self.get_incoming():
            res.append(self._build_dict(ep))
        return res
    
    # OVERRIDE
    # This method is only present since 0.11.2 but we have a special hack in
    # agilo_ticket_edit so that is also used in Trac 0.11.1
    def get_value_or_default(self, name):
        """This method is used from the template engine Genshi to get safely 
        value of the fields. It can be overridden to return special values for
        specific fields, such as type <-> alias"""
        if (name != Key.TYPE) or (not AgiloConfig(self.env).is_agilo_enabled):
            return super(AgiloTicket, self).get_value_or_default(name)
        else:
            return self.get_alias()
        
    # OVERRIDE
    def __setitem__(self, attr, value):
        """Sets the ticket attribute (attr) to the given value"""
        if not AgiloConfig(self.env).is_agilo_enabled:
            super(AgiloTicket, self).__setitem__(attr, value)
        elif attr in self.get_calculated_fields_names():
            debug(self, u"%s not setting calculated property named %s" % \
                        (self, attr))
        else:
            if attr == Key.TYPE:
                # If the type is changed the configuration will be updated
                if not self._reset_type_fields(value):
                    # not a valid type or the same type
                    return
            elif attr == Key.SPRINT and self.values.get(Key.SPRINT) != value:
                # Reset the team members if the restrict owner option is active
                self._set_team_members(sprint_name=value)
            if not hasattr(value, 'strip') and value is not None:
                value = unicode(value)
            super(AgiloTicket, self).__setitem__(attr, value)
    
    def _check_business_rules(self):
        """Checks if this ticket validates against business rules defined"""
        # Validate business rules
        from agilo.scrum.workflow.api import RuleEngine
        RuleEngine(self.env).validate_rules(self)
    
    # OVERRIDE
    def save_changes(self, author, comment, when=None, db=None, cnum='', replyto=''):
        """
        Store ticket changes in the database. The ticket must already exist in
        the database.  Returns False if there were no changes to save, True
        otherwise.
        """
        if not AgiloConfig(self.env).is_agilo_enabled:
            if AgiloTicketSystem.is_trac_1_0():
                return super(AgiloTicket, self).save_changes(author, comment, 
                                                         when=when, db=db, cnum=cnum, replyto=replyto)
            else:
                return super(AgiloTicket, self).save_changes(author, comment, 
                                                         when=when, db=db, cnum=cnum)
        self._check_business_rules()

        if AgiloTicketSystem.is_trac_1_0():
            for f in self.fields:
                if f.get(Key.CUSTOM, False):
                    self.custom_fields.append(f['name'])
            res = super(AgiloTicket, self).save_changes(author, comment, when, db, cnum, replyto=replyto)
        else:
            res = super(AgiloTicket, self).save_changes(author, comment, when, db, cnum)
        # Update Model Manager Cache in case is saved directly
        if res:
            self.tm.update_cache(self)
        return res
    
    # OVERRIDE
    def insert(self, when=None, db=None):
        """
        Intercept the insert() of the trac Ticket, and after that initialize
        the AgiloTicket properties.
        """
        if not AgiloConfig(self.env).is_agilo_enabled:
            return super(AgiloTicket, self).insert(when=when, db=db)
        self._check_business_rules()
        t_id = super(AgiloTicket, self).insert(when=when, db=db)
        # AT: if the type has been changed for this ticket, the reset of the
        # type might not be useful, as the setting a new type will call the
        # reset fields automatically
        #self._reset_type_fields(self.get_type())
        # Update the resource identifier, cause it is created in the Ticket __init__
        # when there is not yet and ID for new tickets.
        self.resource.id = t_id
        return t_id # Respect normal ticket behavior
    
    # OVERRIDE
    def delete(self, db=None):
        """
        Intercept the delete of the ticket to remove the links
        """
        if not AgiloConfig(self.env).is_agilo_enabled:
            return super(AgiloTicket, self).delete(db=db)
        debug(self, "Called delete() for ticket #%s..." % self.id)
        db, handle_ta = get_db_for_write(self.env, db=db)
        super(AgiloTicket, self).delete(db=db)
        # if deleted we remove all the links too
        self.del_all_links(db=db)
        if handle_ta:
            db.commit()
        # Return for convenience the previous ticket id, still
        # existing in the DB, used by the TicketModule to redirect
        # to a sensible ticket.
        cursor = db.cursor()
        cursor.execute("SELECT id FROM ticket WHERE id < %s ORDER BY id DESC" % self.id)
        row = cursor.fetchone()
        if row is not None:
            return row[0]
        
    def _get_calculated_attribute_value(self, attr):
        """Returns the value of a calculated attribute (assumes that the 
        attribute name really exists in this ticket)."""
        debug(self, "Requested calculated value %s for type %s" % (attr, self.get_type()))
        calc_value = None
        if hasattr(self, '_calculated') and attr in self._calculated:
            operator = self._calculated[attr]
            try:
                calc_value = operator(self)
            except Exception, e:
                error(self, u"Calculation Error: %s" % e)
        return calc_value
    
    def _alias_for_genshi(self):
        value = None
        try:
            if inspect.stack()[1][3] == 'lookup_item':
                value = self.get_alias()
        except IndexError:
            # For some reason unknown to me inspect.stack() may fail
            # with an index error sometimes (burndown chart embedded
            # in a wiki macro) so we need to guard against this.
            #  File "/usr/lib64/python2.5/inspect.py", line 885, in stack
            #    return getouterframes(sys._getframe(1), context)
            #  File "/usr/lib64/python2.5/inspect.py", line 866, in getouterframes
            #    framelist.append((frame,) + getframeinfo(frame, context))
            #  File "/usr/lib64/python2.5/inspect.py", line 841, in getframeinfo
            #    lines, lnum = findsource(frame)
            #  File "/usr/lib64/python2.5/inspect.py", line 510, in findsource
            #    if pat.match(lines[lnum]): break
            #IndexError: list index out of range
            pass
        return value
    
    def __getitem__(self, attr):
        """Gets the local ticket attribute (attr) value and returns it"""
        if not AgiloConfig(self.env).is_agilo_enabled:
            return super(AgiloTicket, self).__getitem__(attr)
        value = None
        if hasattr(self, '_calculated') and self._calculated is not None and \
                attr in self._calculated:
            value = self._get_calculated_attribute_value(attr)
        else:
            try:
                # Hack for backwards compatibility with trac 0.11.1
                if attr == Key.TYPE and self.ats.is_trac_011_before_0112():
                    value = self._alias_for_genshi()
                # The super method is doing nothing as of 0.11.2
                #value = super(AgiloTicket, self).__getitem__(attr)
                if not value:
                    value = self.values.get(attr)
                # with 0.11.2 we don't save anymore all the fields, therefore
                # we need to fake the milestone field in case some milestone
                # backlog want to see all the sprint ticket too
                if attr == Key.MILESTONE and not value and \
                        Key.SPRINT in self.fields_for_type:
                    sprint = self.get_sprint()
                    if sprint:
                        value = sprint.milestone
                
                if isinstance(value, basestring) and value == 'None':
                    value = None
                if value is None:
                    value = ''
            except KeyError:
                warning(self, u"%s(%d, %s) has no property named %s, can't get value..." % \
                               (self, self.id, self.get_type(), attr))
        return value
    
    #######################################################################
    ## Database connection API for AgiloTicket                           ##
    #######################################################################
    def _get_type(self, tkt_id, db=None):
        """Get the type of the ticket given the id from the DB"""
        db = get_db_for_read(self.env, db=db)
        sql_get_type = "SELECT type FROM ticket WHERE id=%s" % tkt_id
        cursor = db.cursor()
        cursor.execute(sql_get_type)
        t_type = cursor.fetchone()
        if t_type:
            return t_type[0]
        
    def _is_link(self, src, dest):
        """
        Checks if a link is already existing on the database directly.
        This method is called directly by one of the is_linked_to or
        is_linked_from method
        """
        db = self.env.get_db_cnx()
        sql_query = "SELECT 1 FROM %s WHERE src=%d AND dest=%d" % (LINKS_TABLE, src, dest)
        debug(self, "SQL Query: %s" % sql_query)
        cursor = db.cursor()
        cursor.execute(sql_query)
        if cursor.fetchone():
            return True
        return False
        
    def _create_link(self, src, dest, db=None):
        """
        creates a link between src and dest. The link is directional 
        and has to be allowed from config (trac.ini)
        """
        db, handle_ta = get_db_for_write(self.env, db=db)
        sql_query = "INSERT INTO %s (src, dest) VALUES (%d, %d)" % (LINKS_TABLE, src, dest)
        debug(self, "SQL Query: %s" % sql_query)
        try:            
            cursor = db.cursor()
            cursor.execute(sql_query)
            if handle_ta:
                db.commit()
                debug(self, "DB Committed, created link %d => %d" % (src, dest))
        except Exception, e:
            error(self, exception_to_unicode(e))
            if handle_ta:
                db.rollback()
            raise TracError("Link Already existing %d => %d! ERROR: %s" % (src, dest, exception_to_unicode(e)))
        
    def _delete_link(self, src, dest, db=None):
        """deletes the link between src and dest"""
        db, handle_ta = get_db_for_write(self.env, db=db)
        sql_query = "DELETE FROM %s WHERE src=%d AND dest=%d" % (LINKS_TABLE, src, dest)
        debug(self, "SQL Query: %s" % sql_query)
        try:
            cursor = db.cursor()
            cursor.execute(sql_query)
            if handle_ta:
                db.commit()
            debug(self, "DB Committed, deleted link %d => %d" % (src, dest))
        except Exception, e:
            error(self, exception_to_unicode(e))
            if handle_ta:
                db.rollback()
            raise TracError("ERROR: An error occurred while trying to delete link %d => %d, %s" % \
                            (src, dest, exception_to_unicode(e)))
        
    def _delete_all_links(self, t_id, db=None):
        """deletes all the links with src or dest equal t_id"""
        db, handle_ta = get_db_for_write(self.env, db=db)
        sql_query = "DELETE FROM %s WHERE src=%d OR dest=%d" % (LINKS_TABLE, t_id, t_id)
        try:
            cursor = db.cursor()
            cursor.execute(sql_query)
            if handle_ta:
                db.commit()
        except Exception, e:
            error(self, exception_to_unicode(e))
            if handle_ta:
                db.rollback()
            raise TracError(exception_to_unicode(e))
            
    # Get links from link table, both incoming and outgoing
    # needed for AgiloTypesModule to load links before showing
    # ticket details.
    def _load_incoming_links(self, db=None):
        """
        Returns a list of dictionaries representing the incoming links to 
        this ticket id.
        """
        sql_template = "SELECT t.id FROM ticket t INNER JOIN " + \
                       "%s l ON l.$from = t.id AND " % LINKS_TABLE + \
                       "l.$to = $id ORDER BY t.type"
        sql_query = string.Template(sql_template)
        
        db, handle_ta = get_db_for_write(self.env, db)
        try:
            cursor = db.cursor()
            cursor.execute(sql_query.substitute({'from': 'src', 'to': 'dest', 'id': self.get_id()}))
        except Exception, e:
            error(self, exception_to_unicode(e))
            if handle_ta:
                db.rollback()
            raise TracError("An error occurred while loading incoming links: %s" % exception_to_unicode(e))
            
        # Now fetch data and build the incoming endpoints list
        for t_id, in cursor:
            self._incoming[t_id] = self.tm.get(tkt_id=t_id)
    
    def _load_outgoing_links(self, db=None):
        """
        Returns a list of dictionaries representing the incoming links to 
        this ticket id.
        """
        sql_template = "SELECT t.id, t.type FROM ticket t INNER JOIN " + \
                       "%s l ON l.$from = t.id AND " % LINKS_TABLE + \
                       "l.$to = $id ORDER BY t.type"
        sql_query = string.Template(sql_template)
        
        db, handle_ta = get_db_for_write(self.env, db)
        try:
            cursor = db.cursor()
            cursor.execute(sql_query.substitute({'from': 'dest', 'to': 'src', 'id': self.get_id()}))
        except Exception, e:
            error(self, exception_to_unicode(e))
            if handle_ta:
                db.rollback()
            raise TracError("An error occurred while loading outgoing links: %s" % exception_to_unicode(e))
            
        # Now fetch data and build the outgoing endpoints tree
        for t_id, t_type in cursor:
            self._outgoing[t_id] = self.tm.get(tkt_id=t_id)


class AgiloTicketModelManager(PersistentObjectModelManager):
    """A ModelManager to manage AgiloTicket Objects"""
    
    model = AgiloTicket
    
    def _get_model_key(self, model_instance=None):
        """
        Private method to return either a list of primary keys or a tuple with
        all the primary keys and unique constraints needed to identify a ticket.
        For ticket is enough the id.
        """
        if isinstance(model_instance, AgiloTicket):
            return ((model_instance.id,), None)
        else:
            return [['tkt_id',], None]
    
    def create(self, *args, **kwargs):
        """Specialized method to create a ticket, first create the 
        ticket, than sets all the parameters, if allowed, than saves 
        the ticket"""
        constructor_params = ['env', 'tkt_id', 'db', 'version', 't_type', 'load']
        # remove it to make sure is not causing any trouble
        save = kwargs.pop('save', True)
        
        ticket_params = {}
        for k in kwargs.keys():
            if k not in constructor_params:
                ticket_params[k] = kwargs.pop(k)
        
        ticket = self.model(self.env, *args, **kwargs)
    
        for k, v in ticket_params.items():
            if hasattr(ticket, k):
                setattr(ticket, k, v)
            else:
                #assert ticket.is_writeable_field(k), k
                ticket[k] = v
        
        if save:
            self.save(ticket)
        
        return ticket

    def update_cache(self, ticket):
        """Allows to update the cache with the given ticket"""
        old_ticket = self.get(tkt_id=ticket.id)
        if old_ticket and ticket.time_changed > old_ticket.time_changed:
            self.get_cache().set(self._get_model_key(ticket), ticket)
    
    def save(self, model_instance, **kwargs):
        """Method called to save a model instance, in case of AgiloTicket we
        have to pass also comments and author inside."""
        if model_instance:
            res = None
            if model_instance.exists:
                author = kwargs.pop('author', None)
                comment = kwargs.pop('comment', None)
                # now it is safe to pass extra parameters
                res = model_instance.save_changes(author, comment, **kwargs)
            else:
                res = model_instance.insert()
            # now store into the cache
            if AgiloConfig(self.env).is_agilo_enabled:
                self.get_cache().set(self._get_model_key(model_instance), 
                                     model_instance)
            return res

    def _split_ticket_type(self, criteria):
        """If the criteria contains the ticket type, it will return two
        separate Condition objects, to be appended to the filter for the ticket
        table only and the filter for the custom table."""
        if Key.TYPE in criteria:
            type_criteria = criteria.pop(Key.TYPE, None)
            if type_criteria is not None:
                cond = Condition(type_criteria)
                if cond.is_multiple:
                    return self._split_type_conditions(cond, criteria)
                elif cond.is_single:
                    # is only one, so we return the same type
                    return cond, cond

    def _create_type_condition_for_types(self, condition, ticket_type):
        """Return the Condition object that reflects the given condition with
        the defined list of types"""
        if not ticket_type:
            return None
        if len(ticket_type) > 1:
            ticket_cond = Condition("%s ('%s')" % (condition.operator, "','".join(ticket_type)))
        elif 'not' in condition.operator:
        # we have to create a single condition with !=
            ticket_cond = Condition("!='%s'" % ticket_type[0])
        else:
            ticket_cond = Condition(ticket_type[0])
        return ticket_cond

    def _split_type_conditions(self, condition, criteria):
        """Returns (ticket_type_condition, ticket_custom_type_condition) by
         splitting the given type condition into two, accrding to the passed
         criteria keys, so that the query will match the right table with the
         right type"""
        assert isinstance(condition, Condition) and condition.is_multiple, \
                "invalid Condition: %s" % type(condition)
        ticket_type = []
        custom_type = []
        ats = AgiloTicketSystem(self.env)
        for t_type in condition.value:
            if not criteria:
                ticket_type.append(t_type)
            for key in criteria:
                if key not in TICKET_COLUMNS and \
                        key in [f[Key.NAME] for f in ats.get_ticket_fields(t_type)] and \
                        t_type not in custom_type:
                    custom_type.append(t_type)
                    break
                elif t_type not in ticket_type:
                    ticket_type.append(t_type)
        # Now we divided the types based on the criteria, now we create to new
        # conditions containing the respective types for the two tables
        ticket_cond = self._create_type_condition_for_types(condition, ticket_type)
        custom_cond = self._create_type_condition_for_types(condition, custom_type + \
                [t_type for t_type in ticket_type if t_type not in custom_type])
        return ticket_cond, custom_cond

    def _add_condition(self, condition, column, existing_conditions, values):
        """Adds a condition to the list of conditions and add the value
        to the list of existing values"""
        if condition:
            if condition.is_multiple:
                add_multiple_params_values(values, column, condition.operator,
                                           condition.value, existing_conditions)
            else:
                if condition.is_single:
                    values[column] = condition.value
                # if it is not single is NULL and we add it anyway
                existing_conditions.append(self._format_condition(column, condition.operator))

    def _prepare_query(self, criteria):
        """Prepares the query to select tickets, depending on the criteria
        will return a tuple containing:
         - filter_ticket: a string with formatted SQL WHERE clause to apply
                          to the ticket table
         - filter_ticket_customer: a string with formatted SQL WHERE clause
                                   to be applied to the ticket_custom table
         - values: a dictionary containing key:value pairs for replacement
         - use_union: a boolean that informs the caller about the need or
                      or not to use a union query.
        """
        filter_ticket = filter_ticket_custom = None
        values = {}
        use_union = False
        if criteria is not None:
            conditions_ticket = []
            conditions_ticket_custom = []
            # check if there is type in the criteria and if split the
            # condition in the two table conditions
            split_types = self._split_ticket_type(criteria)
            # now proceed with the remaining criteria
            for column, condition in criteria.items():
                if column not in TICKET_COLUMNS:
                    conditions = conditions_ticket_custom
                    # check if the condition is None
                    if not use_union and condition is None:
                        use_union = True
                else:
                    conditions = conditions_ticket
                # Create a condition and evaluate it
                cond = Condition(condition)
                self._add_condition(cond, column, conditions, values)

            # Now add extra type conditions
            if split_types:
                ticket_cond, custom_cond = split_types
                if use_union:
                    self._add_condition(ticket_cond, Key.TYPE, conditions_ticket, values)
                self._add_condition(custom_cond, Key.TYPE, conditions_ticket_custom, values)

            # Build the filter
            # TODO (AT): discriminate on the AND and OR as well, this can go in
            # the PersistentObject as well, in form of utilities functions
            # We have to separate the conditions from the one to run on the ticket
            # and the one to run also on the ticket_custom scope
            if conditions_ticket:
                # we only add specific ticket conditions if there is at least a
                # pair that needs to be checked in AND on the ticket only that
                # would be affected by the JOIN with ticket_custom.
                filter_ticket = " WHERE " + " AND ".join(conditions_ticket)
            if conditions_ticket_custom:
                filter_ticket_custom = " WHERE " + " AND ".join(conditions_ticket + \
                                                                conditions_ticket_custom)
        return filter_ticket, filter_ticket_custom, values, use_union
    
    def _format_condition(self, column, operator):
        """Format the condition to be appended properly, according to the
        column type and value of the condition"""
        condition = ''
        if column in TICKET_COLUMNS:
            condition = format_condition('ticket', column, operator)
        else:
            if operator is None:
                condition = "ticket_custom.name='%s' AND (ticket_custom.value=''" \
                            " OR ticket_custom.value IS NULL)" % column
            else:
                condition = "(ticket_custom.name='%s' AND ticket_custom.value%s%%(%s)s)" % \
                            (column, operator, column)
        return condition
        
    def _build_order_by_clause(self, order_by):
        sql = ''
        order_pairs = list()
        for order_clause in order_by:
            desc = False
            if isinstance(order_clause, basestring) and \
                    order_clause.startswith('-'):
                order_clause = order_clause[1:]
                desc = True
            if order_clause in TICKET_COLUMNS:
                order_pairs.append('%s%s' % \
                                   (order_clause, 
                                    desc and ' DESC' or ''))
            else:
                order_pairs.append('ticket_custom.value%s' % \
                                   (desc and ' DESC' or ''))
                # we can only sort one property if it is
                # custom
                break
        if len(order_pairs) > 0:
            sql = ' ORDER BY ' + ', '.join(order_pairs)
        return sql

    def _build_sql_union_query(self, sql_main, filter_main, sql_join, filter_join):
        """Returns a SQL query that is the union of the two given one, using the
        given SQL filters"""
        sql = ""
        if filter_main:
            sql += sql_main + filter_main
        if filter_join:
            if sql:
                sql += " UNION "
            sql += sql_join + filter_join
        return sql

    def _build_sql_query(self, criteria=None, order_by=None, limit=None):
        """Builds the SQL query needed to retrive the tickets based on the
        property set chosen and the ticket types if any. This is necessary
        due to the fact that Ticket is spread over 2 tables, one of which
        is denormalized, and doesn't allow for simple JOIN statement"""
        sql_ticket_only = "SELECT DISTINCT id, type FROM ticket"
        sql_ticket_join = "SELECT DISTINCT id, type FROM ticket " \
                          "LEFT OUTER JOIN ticket_custom ON " \
                          "ticket.id=ticket_custom.ticket"

        filter_ticket_only, filter_ticket_join, values, build_union = self._prepare_query(criteria)
        # Building the final SQL query
        sql = ''
        if build_union:
            sql = self._build_sql_union_query(sql_ticket_only,
                                              filter_ticket_only,
                                              sql_ticket_join,
                                              filter_ticket_join)
        else:
            # No need for UNION, take the filter if any
            sql = sql_ticket_join + (filter_ticket_join or filter_ticket_only or '')
        # Now compute the order if there
        if order_by:
            sql += self._build_order_by_clause(order_by)
        if limit:
            sql += " LIMIT %d" % limit
        return sql, values

    def select(self, criteria=None, order_by=None, limit=None, db=None, ids_only=False):
        """Selects Tickets from the database, given the specified criteria.
        The criteria is expressed as a dictionary of conditions (object 
        fields) to be appended to the select query. The order_by adds 
        the order in which results should be sorted. the '-' sign in 
        front will make the order DESC. The limit parameter limits the 
        results of the SQL query.
        
        Example::
            
            criteria = {'name': 'test', 'users': '> 3', 'team': TheTeam}
            order_by = ['-name', 'users']
            limit = 10
        """
        assert criteria is None or isinstance(criteria, dict)
        assert order_by is None or isinstance(order_by, list)
        assert limit is None or isinstance(limit, int)

        sql, values = self._build_sql_query(criteria, order_by, limit)
        db, handle_ta = get_db_for_write(self.env, db)
        tickets = []

        try:
            cursor = db.cursor()
            debug(self, "SELECT => Executing Query: %s %s" % (sql, values))
            safe_execute(cursor, sql, values)
            for row in cursor:
                if not ids_only:
                    params = {
                        'tkt_id': int(row[0]),
                        't_type': row[1]
                    }
                    tickets.append(self.get(**params))
                else:
                    tickets.append(int(row[0]))
        
        except Exception, e:
            raise UnableToLoadObjectError(_("An error occurred while " \
                                            "getting ticket from the " \
                                            "database: %s" % exception_to_unicode(e)))
        return tickets
    
    def select_tickets_having_properties(self, properties, 
                                         criteria=None, order_by=None,
                                         limit=None, db=None):
        """Returns a list of tickets having the defined list of 
        properties, combined with the other normal select paramenters"""
        types = []
        for prop in properties:
            for t_type, fields in AgiloConfig(self.env).TYPES.items():
                if prop in fields:
                    types.append(t_type)
        # check if we have types to append to the criteria or not
        condition = None
        if len(types) > 1:
            condition = "in ('%s')" % "', '".join(types)
        elif len(types) == 1:
            condition = types[0]
            
        if criteria and condition:
            criteria.update({Key.TYPE: condition})
        elif condition:
            criteria = {Key.TYPE: condition}
        # return the select
        return self.select(criteria=criteria, order_by=order_by, limit=limit, db=db)


# REFACT: consider to move this to it's own file?
class AgiloMilestone(trac.ticket.model.Milestone):
    """Wraps the Trac Milestone to add the update behaviour for the Sprints, on
    top of the tickets"""
    
    def serialize_timestamp(self, a_datetime):
        "Trac 0.12 compatibility helper, timestamps in trac 0.12 are saved as utimestamps"
        from agilo.ticket import AgiloTicketSystem
        if AgiloTicketSystem(self.env).is_trac_012():
            from trac.util.datefmt import to_utimestamp
            return to_utimestamp(a_datetime)
        else:
            return to_timestamp(a_datetime)
    
    # OVERRIDE
    def update(self, db=None):
        if not AgiloConfig(self.env).is_agilo_enabled:
            return super(AgiloMilestone, self).update(db=db)
        assert self.name, 'Cannot update milestone with no name'
        if not db:
            db = self.env.get_db_cnx()
            handle_ta = True
        else:
            handle_ta = False
            
        # AT: importing inline, to avoid overlapping at import time, or the
        # monkey patching won't work out
        from trac.ticket.model import simplify_whitespace
        
        self.name = simplify_whitespace(self.name)
        cursor = db.cursor()
        self.env.log.info('Updating milestone "%s"' % self.name)
        # in Trac 0.12, milestones have an _old instead of the specialized _old_name
        if hasattr(self, '_old_name'):
            old_milestone_name = self._old_name
        else:
            old_milestone_name = self._old['name']
        cursor.execute("UPDATE milestone SET name=%s,due=%s,"
                       "completed=%s,description=%s WHERE name=%s",
                       (self.name, self.serialize_timestamp(self.due), self.serialize_timestamp(self.completed),
                        self.description, old_milestone_name))
        self.env.log.info('Updating milestone field of all tickets '
                          'associated with milestone "%s"' % self.name)
        cursor.execute("UPDATE ticket SET milestone=%s WHERE milestone=%s",
                       (self.name, old_milestone_name))
        # AT: adding rename of the sprints to avoid sprint not in sync with milestones
        self.env.log.info('Updating milestone field of all sprints '
                          'associated with milestone "%s"' % self.name)
        cursor.execute("UPDATE agilo_sprint SET milestone=%s WHERE milestone=%s",
                       (self.name, old_milestone_name))
        
        self._old_name = self.name
        
        if handle_ta:
            db.commit()
        AgiloTicketSystem(self.env).reset_ticket_fields()


# AT: Monkey patching the Trac Milestone.
trac.ticket.model.Milestone = trac.ticket.Milestone = AgiloMilestone
trac.ticket.model.Ticket = AgiloTicket
trac.ticket.Ticket = AgiloTicket

# This will take care of field caching in Trac 0.12 (new milestones don't appear
# in the ticket drop-down even though the milestone was created)
trac.ticket.model.TicketSystem = AgiloTicketSystem


# This will remove reference fields from the custom query page
# (filter fields, column fields and, where available, batch modify
# since these are advanced fields and do not work anyway
from trac.ticket.query import Query

original_template_data = Query.template_data


def custom_template_data(self, context, tickets, orig_list=None, orig_time=None, req=None):
    result = original_template_data(self, context, tickets, orig_list=orig_list, orig_time=orig_time, req=req)
    if 'i_links' in result['fields']:
        result['fields'].pop('i_links')
    if 'o_links' in result['fields']:
        result['fields'].pop('o_links')
    return result


Query.template_data = custom_template_data