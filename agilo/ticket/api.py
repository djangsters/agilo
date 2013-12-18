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
#     - Andrea Tomasini <andrea.tomasini__at__agile42.com>

from trac.config import Option
from trac.core import implements, TracError
import trac.ticket.api
from trac.ticket.api import TicketSystem
from trac.util.text import to_unicode

from agilo.utils import Key
from agilo.utils.config import AgiloConfig, IAgiloConfigChangeListener


__all__ = ['AgiloTicketSystem']

# TODO: override all list methods that may affect the content of the data.
class FieldsWrapper(list):
    """This class allows to wrap the ticket fields list and depending on the
    initialization type, will return only the fields allowed for that
    ticket. This is type dependent and not instance or request dependent,
    this class aims to avoid duplication of data, just yield the allowed
    ones back."""
    def __init__(self, env, fields, t_type=None):
        """Initialize the FieldsWrapper for a specific ticket type"""
        self.env = env
        self._all_fields = fields
        self._type = t_type
        self._field_names = None
        self._fields = self._initialize(t_type, fields)
    
    def _initialize(self, t_type, fields):
        """Initialize the wrapper for the given type, it assumes that the 
        fields are already set in _all_fields"""
        self._field_names = AgiloConfig(self.env).TYPES.get(t_type)
        fields_for_type = list()
        if self._field_names is None:
            return fields
        
        # copy a reference to the fields which are valid for this type
        for f in self._all_fields:
            if f[Key.NAME] in self._field_names:
                fields_for_type.append(f)
            elif f[Key.NAME] == Key.MILESTONE and \
                    Key.SPRINT in self._field_names:
                # AT: if sprint is a valid field we have to include
                # also milestone, the reason is that the query to
                # the DB will not return this ticket as belonging
                # to the milestone. The field is anyway skipped
                # from the UI, which justify its scope against the
                # sprint.
                f[Key.SKIP] = True
                fields_for_type.append(f)
        return fields_for_type
        
    def _get_type(self):
        """Returns the actual set ticket type for this FieldWrapper"""
        return self._type
    
    def _set_type(self, t_type):
        """
        Sets the type of the ticket for this wrapper and 
        reload the properties, in case it changes
        """
        if t_type != self._type:
            self._type = t_type
            self._initialize(t_type)
    
    t_type = property(_get_type, _set_type)
    
    def __repr__(self):
        return repr(self._fields)
    
    def __len__(self):
        return self._fields.__len__()
    
    def __contains__(self, elem):
        return self._fields.__contains__(elem)
    
    def __iter__(self):
        """Returns the iterator"""
        self.__next = 0
        return self
        
    def next(self):
        """
        Returns the next item from the list of tickets, according
        to the actual sorting
        """
        if self.__next < len(self._fields):
            self.__next += 1
            return self._fields[self.__next - 1]
        raise StopIteration
    
    iterkeys = __iter__
    
    def __getitem__(self, key):
        """
        Emulates the get by index of a list, returns only the items in the
        list of allowed fields
        """
        return self._fields.__getitem__(key)
    
    def __setitem__(self, key, value):
        """Sets the item in the list position"""
        return self._fields.__setitem__(key, value)

    def __delitem__(self, key):
        """Delete the item form the list"""
        return self._fields.__delitem__(key)


class AgiloTicketSystem(TicketSystem):
    """Extends the Trac TicketSystem to add support for specific Agilo fields"""
    
    implements(IAgiloConfigChangeListener)
    
    # In Trac this is part of the TicketModule (but not used - the TicketSystem
    # accesses the configuration directly). I think the TicketSystem is the 
    # right place to have it.
    # AT: I changed this to task instead of defect, because it makes more sense
    # and is an Agilo supported type.
    default_type = Option('ticket', 'default_type', 'task',
        """Default type for newly created tickets (''since 0.9'').""")
    
    
    # Override in Trac 0.11 + 0.12
    def eventually_restrict_owner(self, field, ticket=None, sprint_name=None):
        """
        Restrict the owner of a ticket to the allowed ones. On top of Trac
        method which restrict the owners to only the users with a TICKET_MODIFY
        right, this version remove from the list all the users which are not
        team members of the current sprint
        """
        if not AgiloConfig(self.env).is_agilo_enabled:
            super(AgiloTicketSystem, self).eventually_restrict_owner(field, ticket=ticket)
        elif (ticket and Key.SPRINT in ticket.fields_for_type) or sprint_name:
            members = self._get_team_members(sprint_name or ticket[Key.SPRINT])
            if members is not None:
                # the ticket has been assigned and the sprint has a team
                field[Key.OPTIONS] = members
                field[Key.TYPE] = Key.SELECT
                field[Key.OPTIONAL] = True
        elif self.is_trac_with_field_caching():
            super(AgiloTicketSystem, self).eventually_restrict_owner(field, ticket=ticket)
    
    def _get_team_members(self, sprint_name):
        """
        Returns the list of team member names for the given sprint, if existing
        """
        if not sprint_name:
            return None
        # Avoid recursive imports (things from .api should not import other
        # stuff globally)
        from agilo.scrum.sprint import SprintModelManager
        sprint = SprintModelManager(self.env).get(name=sprint_name)
        if not sprint or not sprint.exists or not sprint.team:
            return None
        members =  [m.name for m in sprint.team.members]
        members.sort()
        return members

    def normalize_type(self, type_or_alias, new_aliases=None):
        """Returns the trac type for the given type or alias"""
        if type_or_alias is None:
            return None
        ticket_config = AgiloConfig(self.env).ticket_configuration
        return ticket_config.trac_type_for_alias_or_type(type_or_alias, alias_mapping=new_aliases)
    
    @classmethod
    def is_trac_011_before_0112(cls):
        return cls.is_trac_011() and not cls.is_trac_011_after_0112()
    
    @classmethod
    def is_trac_011_after_0112(cls):
        return AgiloTicketSystem.is_trac_011() and hasattr(TicketSystem, '_get_custom_fields')
    uses_field_caching = is_trac_011_after_0112
    
    @classmethod
    def is_trac_011(cls):
        return (not cls.is_trac_012())
    
    @classmethod
    def is_trac_012(cls):
        # return true if it's at least 0.12
        import trac
        revisions = trac.__version__.split('.')
        return int(revisions[0]) >= 1 or (int(revisions[0]) == 0 and int(revisions[1] >= 12))
        #return hasattr(TicketSystem, 'fields')

    @classmethod
    def is_trac_1_0(cls):
        import trac
        revisions = trac.__version__.split('.')
        return int(revisions[0]) >= 1
    
    @classmethod
    def is_trac_with_field_caching(cls):
        return cls.is_trac_011_after_0112() or cls.is_trac_012()
    
    def _initialize_agilo_properties(self, prop_list):
        """Initialize the properties container for the ticket system"""
        for prop in prop_list:
            if not hasattr(self, prop) or getattr(self, prop) is None:
                setattr(self, prop, dict())
        
    def get_agilo_properties(self, t_type):
        """Initialize specific AgiloTicket properties, they all depend on the
        ticket type that need to be set. In case is a new created ticket, not
        yet save, the type is not defined, therefore we check the type before
        trying any configuration. Returns a tuple: calculated_properties, 
        allowed_links, sort_properties, show_on_link_properties"""
        self._initialize_agilo_properties(['_alloweds', 
                                           '_calculated', 
                                           '_sort',
                                           '_show_on_link'])
        
        if t_type is not None and not self._calculated.has_key(t_type):
            # The algorithm is ugly but at the moment I found no other way
            try:
                # Import only if needed
                from agilo.ticket.links import LinkOption
                from agilo.ticket.links.model import LinksConfiguration

                lc = LinksConfiguration(self.env)
                if not lc.is_initialized():
                    raise TracError("The Links Configurations didn't initialize correctly!")
                self._calculated[t_type] = lc._calculated_properties_by_type.get(t_type, dict())
                
                # Set the calculated fields list for the UI
                for allowed in lc.get_alloweds(t_type):
                    if not self._alloweds.has_key(t_type):
                        self._alloweds[t_type] = dict()
                    self._alloweds[t_type][allowed.dest_type] = allowed
                    # Now fill the sort options
                    sort = allowed.get_option(LinkOption.SORT)
                    if sort is not None: 
                        if not self._sort.has_key(t_type):
                            self._sort[t_type] = dict()
                        self._sort[t_type][allowed.dest_type] = sort
                    # Now fill the fields to show in the links
                    show = allowed.get_option(LinkOption.SHOW)
                    if show is not None:
                        if not self._show_on_link.has_key(t_type):
                            self._show_on_link[t_type] = dict()
                        self._show_on_link[t_type][allowed.dest_type] = show
            except Exception, e:
                raise TracError("The Links Configurations didn't initialize correctly! => %s" % to_unicode(e))
        # Returns the agilo fields
        return self._calculated.get(t_type, {}), self._alloweds.get(t_type, {}), \
                    self._sort.get(t_type, {}), self._show_on_link.get(t_type, {})
    
    # Override only in Trac 0.11
    def get_custom_fields(self):
        """Add specific custom fields to the TicketSystem"""
        fields = super(AgiloTicketSystem, self).get_custom_fields()
        if not AgiloConfig(self.env).is_agilo_enabled:
            return fields
        
        if self.is_trac_012() or self.is_trac_011_before_0112():
            # In Trac < 0.11.2 there is no field cache so our _get_custom_fields
            # method is not called.
            self._add_sprint_options(fields)
        return fields
    
    
    def _add_sprint_options(self, fields):
        # Avoid recursive imports (things from .api should not import other 
        # stuff globally)
        from agilo.scrum.sprint import SprintModelManager
        sp_manager = SprintModelManager(self.env)
        for field in fields:
            if field[Key.NAME] == Key.SPRINT:
                field['custom'] = True
                field['optional'] = True
                field['options'] = [s.name for s in sp_manager.select()]
                break
    
    # Override (since Trac 0.11.2, not in Trac 0.12)
    def _get_custom_fields(self):
        # This method is only called in Trac 0.11.2 (Field cache)
        fields = super(AgiloTicketSystem, self)._get_custom_fields()
        if AgiloConfig(self.env).is_agilo_enabled:
            self._add_sprint_options(fields)
        return fields
    
    # Override: (since trac 0.11.2) trac's own reset_ticket_fields does not reset 
    # the custom fields.
    def reset_ticket_fields(self, notify_other_trac_processes=True):
        if not AgiloConfig(self.env).is_agilo_enabled:
            return super(AgiloTicketSystem, self).reset_ticket_fields()
        if self.is_trac_012():
            del self.fields
            del self.custom_fields
        elif self.is_trac_011_after_0112():
            self._fields_lock.acquire()
            try:
                self.clear_cached_information()
                if notify_other_trac_processes:
                    self.config.touch() # brute force approach for now
            finally:
                self._fields_lock.release()
    
    def clear_cached_information(self):
        """Remove all cached information from the ticket system. But does not 
        care about locking or reloading the information from the configuration.
        
        This method is important because we need a reliable way of resetting all
        cached fields for this TicketSystemInstance without touching the 
        configuration which might trigger a full environment reload for other 
        Agilo processes as well.
        """
        if self.is_trac_011_after_0112():
            self._fields_lock.acquire()
            try:
                self._fields = None
                self._custom_fields = None
            finally:
                self._fields_lock.release()
        self._calculated = None
        self._alloweds = None
        self._sort = None
        self._show_on_link = None
    
    def fieldnames(self, fields):
        return [i['name'] for i in fields]
    
    # OVERRIDE: 0.11.2+ (and REPLACE)
    # now the hack should work copying the lists too
    def get_ticket_fields(self, t_type=None, new_aliases=None):
        """Returns the list of fields available for tickets. If t_type is 
        specified only the fields for that given type are returned.
        Be aware that the returned list does not include calculated fields."""
        if not AgiloConfig(self.env).is_agilo_enabled:
            return super(AgiloTicketSystem, self).get_ticket_fields()
        
        # Normalize the type, so we convert eventual alias
        t_type = self.normalize_type(t_type, new_aliases)
        if self.is_trac_012():
            return self._get_ticket_fields_without_extra_copy(t_type)
        # This is now cached - as it makes quite a number of things faster,
        # since trac 0.11.2 there is an attribute _fields.
        elif self.is_trac_011_after_0112():
            return self._get_ticket_fields_with_deep_copy(t_type)
        # In 0.11.1 there is no cache. But actually the FieldsWrapper is
        # very useful nevertheless because it filters out all fields which
        # are not shown for the type.
        return self._get_ticket_fields_without_extra_copy(t_type)
    
    def _get_ticket_fields_without_extra_copy(self, ticket_type):
        all_fields = super(AgiloTicketSystem, self).get_ticket_fields()
        if ticket_type is None:
            return all_fields
        return FieldsWrapper(self.env, all_fields, ticket_type)
    
    def _get_ticket_fields_with_deep_copy(self, ticket_type):
        # this method only works for Trac 0.11.2 -> 0.11.x
        # If the type is None there will be a None key in the dictionary 
        # with all the fields inside
        # saving self._fields to a local variable to prevent a race condition
        # between "is None" and "not in" where someone else could set 
        # self._fields to None in between.
        type_to_fields = self._fields
        if (type_to_fields is None) or (ticket_type not in type_to_fields):
            self._fields_lock.acquire()
            if self._fields is None:
                self._fields = dict()
            try:
                self._fields[ticket_type] = \
                    FieldsWrapper(self.env, self._get_ticket_fields(), ticket_type)
                type_to_fields = self._fields
            finally:
                self._fields_lock.release()
        
        # Now deep copy the options fields too
        fields = list()
        for field in type_to_fields[ticket_type]:
            if field[Key.NAME] == Key.TYPE and field.has_key(Key.OPTIONS):
                new_options = list(field[Key.OPTIONS]) #copy
                copied_field = field.copy()
                copied_field[Key.OPTIONS] = new_options
                fields.append(copied_field)
            else:
                fields.append(field.copy())
        return fields
    
    def get_ticket_fieldnames(self, ticket_type):
        fieldnames = []
        for field in self.get_ticket_fields(ticket_type):
            fieldnames.append(field['name'])
        return fieldnames
    
    def valid_ticket_statuses(self):
        valid_statuses = []
        for field in self.get_ticket_fields():
            if field['name'] == 'status':
                valid_statuses = field.get('options')
        return valid_statuses
    
    # IAgiloConfigChangeListener
    def config_reloaded(self):
        self.reset_ticket_fields(notify_other_trac_processes=False)

trac.ticket.api.TicketSystem = AgiloTicketSystem
