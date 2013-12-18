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
#       - Andrea Tomasini <andrea.tomasini__at__agile42.com>

import string

from trac.core import Component, implements
from trac.resource import Resource
from trac.ticket.api import ITicketChangeListener
from trac.ticket.notification import TicketNotifyEmail
from trac.core import TracError

from agilo.core import PersistentObject, Field, PersistentObjectModelManager, \
    safe_execute, add_as_dict
from agilo.utils import BacklogType, Key, Status, Realm
from agilo.utils.compat import exception_to_unicode
from agilo.utils.db import get_db_for_write
from agilo.utils.log import debug, error
from agilo.utils.sorting import By, Attribute, SortOrder
from agilo.utils.days_time import now
from agilo.scrum import BACKLOG_TICKET_TABLE, BACKLOG_TABLE,SprintModelManager,Milestone
from agilo.scrum.backlog.backlog_config import BacklogConfiguration
from agilo.ticket.model import AgiloTicketModelManager, AgiloTicket
from agilo.ticket.links import LINKS_TABLE

# FIXME (AT): We should implement a better Resource Management interface for
# the backlog that should reflect the proper Backlog keys. The name is not
# enough to uniquely identify a Backlog, we need at least also the scope.
def backlog_resource(name, req_scope=None, req_name=None):
    identifier = name
    
    if req_scope:
        identifier += ":" + req_scope

    if req_name:
        identifier += ":" + req_name

    return Resource(Realm.BACKLOG, identifier)


class BacklogTypeError(Exception):
    """Raised when no matching BacklogConfiguration is found"""


class MissingOrInvalidScopeError(Exception):
    """Raised when a scoped backlog is initialized without a scope"""


class Backlog(object):
    """Represent a Backlog that is a dynamic object that will not persist a
    state directly but only though its configuration and the BacklogItems
    contained. The BacklogConfiguration acts much more as a type definition
    rather than a real configuration object, for this reason makes sense to
    cache it"""
    
    class BacklogItem(PersistentObject):
        """Represent one item of a backlog. It stores the relation between a
        Backlog and a ticket. The Backlog item persist its position too, and it
        is uniquely identified by the tuple(backlog_name, ticket_id). The
        position has to be unique per backlog_name"""
        class Meta(object):
            table_name = BACKLOG_TICKET_TABLE
            backlog_name = Field(primary_key=True, db_name="name")
            scope = Field(primary_key=True)
            ticket = Field(type="ticket", primary_key=True, db_name="ticket_id")
            pos = Field(type="integer") # this should be logically unique
            
        def __init__(self, env, scope=None, **kwargs):
            """Initialize a BacklogItem"""
            if scope is None:
                scope = 'global'
            super(Backlog.BacklogItem, self).__init__(env, 
                                                      scope=scope, 
                                                      **kwargs)
            # flag for ticket changes
            self._ticket_changed = False
                
        @property
        def fields_for_type(self):
            """Returns the fields_for_type of the contained ticket"""
            return self.ticket.fields_for_type
            
        def get(self, key):
            """Returns the value of the key attribute of the ticket or None"""
            value = None
            try:
                value = self[key]
            except KeyError:
                pass
            return value

        def _get_item_id(self, item=None):
            # Returns the id of the given item or of self
            if item is None:
                item = self
            if isinstance(item, Backlog.BacklogItem):
                return item.ticket.id
            elif isinstance(item, AgiloTicket):
                return item.id
            raise ValueError("The given item is neither an AgiloTicket nor a BacklogItem")

        def __setitem__(self, attr, value):
            """Implement the setitem to allow setting property into the
            contained ticket, and set the modified attribute to True
            so that when the backlog is saved also the modified tickets
            will be"""
            if attr == 'id':
                pass
            elif self.ticket[attr] != value:
                self.ticket[attr] = value
                self._ticket_changed = True
        
        def __getitem__(self, attr):
            """implement the getitem to allow retrieving and sorting
            by any ticket property, for pos return the local attribute"""
            if attr == 'id':
                return self.ticket.id
            else:
                return self.ticket[attr]
                
        def __cmp__(self, other):
            """Override standard object comparison, checking that the
            ID of the Backlog Items are matching"""
            if other is None:
                return -1
            if self.ticket.id == self._get_item_id(other):
                return 0
            elif self.ticket.id < self._get_item_id(other):
                return -1
            elif self.ticket.id > self._get_item_id(other):
                return 1
        
        def __unicode__(self):
            return unicode(self.__str__())
            
        def __str__(self):
            return '<BacklogItem(%s), pos: %s scope: %s backlog: %s>' % \
                    (self.ticket, self.pos, self.scope, self.backlog_name)
        
        def __repr__(self):
            return self.__str__()
        
        def save(self, db=None, author='AgiloBacklog', comment='Updated...'):
            """Override the PersistentObject save to save changes to the 
            ticket in case something has been changed"""
            if self._ticket_changed:
                real_now = now()
                self.ticket.save_changes(author, comment, db=db, when=real_now)
                self._ticket_changed = False
                try:
                    tn = TicketNotifyEmail(self.env)
                    tn.notify(self.ticket, newticket=False, modtime=real_now)
                except Exception, e:
                    self.env.log.exception(exception_to_unicode(e))
                    error(self, "Failure sending notification on change to " \
                                "ticket #%s:" % self.ticket.id)
            return super(Backlog.BacklogItem, self).save(db=db) 
    
    def __init__(self, env, name=None, scope=None, load=True):
        """Initialize the backlog for the given name by loading its 
        configuration object and the associated BacklogItems"""
        self.env = env
        self.config = BacklogConfiguration(self.env, name)
        self.secondary_ticket_cache = {}
        if not self.config.exists and load:
            # It is not a valid backlog type
            raise BacklogTypeError("No backlog of type: %s" % name)
        if self.config.type in (BacklogType.SPRINT, BacklogType.MILESTONE):
            self._check_scope_is_valid(scope)
        self.scope = scope or BacklogType.LABELS[BacklogType.GLOBAL]

    def _check_scope_is_valid(self, scope):
        """Checks that the scope is not None and is a valid Sprint or Milestone"""
        if not scope:
            raise MissingOrInvalidScopeError("Missing Scope for backlog: %s" % scope)
        else:
            if self.config.type == BacklogType.MILESTONE:
                milestone = Milestone(self.env, scope)
                if not milestone.exists:
                    raise MissingOrInvalidScopeError("Invalid Milestone name: %s" % scope)
            elif self.config.type == BacklogType.SPRINT:
                sprint = SprintModelManager(self.env).get(name=scope)
                if not sprint:
                    raise MissingOrInvalidScopeError("Invalid Sprint name: %s" % scope)

    @property
    def resource(self):
        """Return the Resource object for this backlog"""
        return backlog_resource(self.config.name)
    
    def _add_backlog_item(self, ticket, backlog_items):
        """Adds the given ticket to the given list of backlog_items if the ticket
        type fits into this Backlog configuration."""
        if ticket.get_type() not in self.config.ticket_types or \
                ticket.id in [bi.ticket.id for bi in backlog_items]:
            return
        
        # FIXME: locking, there is a race condition between getting the new max
        # position and trying to write the new backlog_item at that location
    
        # returns a new backlog item except if there already is a
        # backlog item for that ticket at any position
        bi = self._get_backlog_item(ticket)
        backlog_items.append(bi)
    
    def get_ticket_from_secondary_cache(self, ticket_id):
        if self.secondary_ticket_cache.has_key(ticket_id):
            return self.secondary_ticket_cache[ticket_id]
        
        tm = AgiloTicketModelManager(self.env)
        ticket = tm.get(tkt_id=ticket_id)
        self.secondary_ticket_cache[ticket_id] = ticket 
        return ticket
        
    def get_ticket_from_cache(self, ticket_id, tickets):
        tickets_as_dict = dict([(x.id, x) for x in tickets])
        if tickets_as_dict.has_key(ticket_id):
            return tickets_as_dict[ticket_id]
        return self.get_ticket_from_secondary_cache(ticket_id)
    
    def _load_links_for_backlog(self, tickets, backlog_items):
        tm = AgiloTicketModelManager(self.env)
        
        if len(tickets) == 0:
            return
        
        ticket_ids = [str(x.id) for x in tickets]
        id_values = ",".join(ticket_ids)
        sql_template = "SELECT l.$to, l.$from FROM %s l" % LINKS_TABLE + \
                       " WHERE l.$to in (%s) ORDER BY l.$from;" % id_values
        sql_query = string.Template(sql_template)
        
        db, handle_ta = get_db_for_write(self.env)
        try:
            cursor = db.cursor()
            safe_execute(cursor, sql_query.substitute({'from': 'src', 'to': 'dest'}))
        except Exception, e:
            error(self, exception_to_unicode(e))
            if handle_ta:
                db.rollback()
            raise TracError("An error occurred while loading incoming links: %s" % exception_to_unicode(e))
            
        for t_id, l_src in cursor:
            dest = self.get_ticket_from_cache(t_id, tickets)
            src = self.get_ticket_from_cache(l_src, tickets)
            dest._incoming[l_src] = src
            dest._incoming_loaded = True
            src._outgoing[t_id] = dest
            src._outgoing_loaded = True
    
    def _add_with_parents_to_backlog(self, ticket, backlog_items):
        """Adds the parents to the backlog recursively if they have a type
        allowed to be displayed in this backlog type"""
        # walk through the backlog items and load the parents if the type is
        # in the allowed types for this backlog configuration
        if hasattr(ticket, '_incoming_loaded') and ticket._incoming_loaded:
            parents = ticket.get_incoming()
            for parent in parents:
                self._add_with_parents_to_backlog(parent, backlog_items)
        ticket._incoming_loaded = True
        ticket._outgoing_loaded = True
        self._add_backlog_item(ticket, backlog_items)

    def add(self, ticket_or_backlogItem):
        """Adds the given item to the current backlog, this makes sense only if
        the Backlog is scoped. The add action will also change the scope of the
        ticket, whether it is the milestone or the sprint, to match this backlog"""
        if self.config.type != BacklogType.GLOBAL:
            ticket_or_backlogItem = self._get_backlog_item(ticket_or_backlogItem)
            ticket_or_backlogItem[BacklogType.LABELS[self.config.type]] = self.scope
            ticket_or_backlogItem.save()
    
    def _select_backlog_items(self, order_by=None, limit=None):
        "Can contain items not anymore in the backlog"
        order_by = order_by or [Key.POS]
        bimm = BacklogModelManager.BacklogItemModelManager(self.env)
        criteria = {Key.BACKLOG_NAME: self.config.name, Key.SCOPE: self.scope}
        return bimm.select(criteria=criteria, order_by=order_by, limit=limit)
    
    def _load_tickets_matching_backlog(self, ids_only=False, not_in=None):
        """Returns a list with all the tickets matching the backlog configuration.
        with the option ids_only, returns just a list of ticket_ids"""
        # If there is no ticket type specified we do not load any ticket
        if not self.config.ticket_types:
            return []
        
        criteria = self._build_criteria_for_tickets_matching_backlog(ids_only, not_in);
        # Load all tickets matching backlog criteria or ids only
        return AgiloTicketModelManager(self.env).select(criteria=criteria,
                                                        ids_only=ids_only)
        
    def _build_criteria_for_tickets_matching_backlog(self, ids_only=False, not_in=None):
        
        if self.config.type == BacklogType.GLOBAL:
            # load all the non scoped tickets ad add them to the backlog if not
            # already there, and if not closed
            criteria = {Key.STATUS: '!=' + Status.CLOSED}
            if not self.config.include_planned_items:
                criteria.update({Key.MILESTONE: None, Key.SPRINT: None})
        else:
            # it is a scoped backlog, we need to load all the tickets that might
            # match the scope
            ticket_attribute = BacklogType.LABELS[self.config.type]
            criteria = {ticket_attribute: self.scope}
        # Add criteria to honor the ticket types allowed in the current backlog
        if self.config.ticket_types:
            criteria['type'] = "in ('%s')" % "', '".join(self.config.ticket_types)
        if not_in:
            criteria['id'] = "not in %s" % str(not_in) 
        
        return criteria

    
    def _add_with_parents_ids(self, t_id, keys):
        """Adds the ids of the given ticket and the one of its parents
        to the list of ids"""
        ticket = AgiloTicketModelManager(self.env).get(tkt_id=t_id)
        if ticket:
            parents = ticket.get_incoming()
            for parent in parents:
                if parent.get_type() in self.config.ticket_types:
                    self._add_with_parents_ids(parent.id, keys)
            if t_id not in keys:
                keys.append(t_id)
    
    def keys(self):
        """Returns the list of ticket ids, matching the current backlog
        configuration"""
        tickets_ids = self._load_tickets_matching_backlog(ids_only=True)
        # Not using existing backlog items because on removal of backlog items, 
        # they are not cleaned out of the database
        backlog_items = []
        backlog_items_ids = []
        keys = []
        for ticket_id in tickets_ids:
            if ticket_id not in backlog_items_ids:
                self._add_with_parents_ids(ticket_id, keys)
        
        return keys
    
    def values(self):
        """Returns the list of items for this Backlog. If it is a global type 
        it will load all the ticket type that fits to its configuration,
        otherwise it will load the items explicitly planned for the defined
        scope as well as their parents"""
        # REFACT: consider to change this to a lazy getter
        # BUT: check that the request thread is not reused by wsgi request thread workers
        backlog_items = []
        tickets = self._load_tickets_matching_backlog()
        self._load_links_for_backlog(tickets, backlog_items)
        
        for t in tickets:
            # create a backlog item so next time will be already there
            self._add_with_parents_to_backlog(t, backlog_items)
        backlog_items.sort(By(Attribute('pos'), SortOrder.ASCENDING))
        
        return backlog_items
    
    def __getitem__(self, index):
        """Returns the backlog item with the given index, that should be the
        same as the position"""
        return self.values()[index]
    
    def _get_backlog_item(self, ticket_or_backlogItem, pos=None, save=False):
        # Returns the backlog item corresponding to the given ticket or already
        # set backlog item
        # Will also find backlog items with __different__ position!
        if isinstance(ticket_or_backlogItem, AgiloTicket):
            bimm = BacklogModelManager.BacklogItemModelManager(self.env)
            # The backlogItem can be None and override the ticket
            backlogItem = bimm.get(backlog_name=self.config.name,
                                   scope=self.scope,
                                   ticket=ticket_or_backlogItem)
            if backlogItem is not None:
                ticket_or_backlogItem = backlogItem
                if save and pos is not None and \
                        pos != ticket_or_backlogItem.pos:
                    ticket_or_backlogItem.pos = pos
                    ticket_or_backlogItem.save()
            else:
                ticket_or_backlogItem = bimm.create(save=save,
                                                    backlog_name=self.config.name,
                                                    scope=self.scope,
                                                    pos=pos,
                                                    ticket=ticket_or_backlogItem)
        return ticket_or_backlogItem
    
    def remove(self, ticket_or_backlogItem_or_list):
        """Removes a ticket or Backlog Item from the current backlog if it is
        a scoped backlog, by resetting the scope property to None, so that the
        item will not show up anymore in this Backlog."""
        # values returns the backlog items sorted by position
        if not isinstance(ticket_or_backlogItem_or_list, (list, tuple)):
            ticket_or_backlogItem_or_list = [ticket_or_backlogItem_or_list]

        for item in ticket_or_backlogItem_or_list:
            # normalize to a BacklogItem
            bi = self._get_backlog_item(item, save=False)
            # check if the backlog item belongs to the backlog
            if bi is not None:
                # We need to reset the scope or the ticket will appear again
                # in the backlog
                self._reset_scope_in_ticket(bi.ticket)
                bi.delete()

    def _reset_scope_in_ticket(self, ticket):
        """Reset the scope if matching this backlog scope and value"""
        if ticket:
            changed = False
            if self.config.type == BacklogType.MILESTONE and \
                    ticket[Key.MILESTONE] == self.scope:
                ticket[Key.MILESTONE] = ''
                changed = True
            elif self.config.type == BacklogType.SPRINT and \
                    ticket[Key.SPRINT] == self.scope:
                ticket[Key.SPRINT] = ''
                changed = True
            if changed:
                ticket.save_changes(author='Agilo Backlog',
                                    comment='Removed from %s backlog...' % \
                                    self.config.name)

    def _update_position_in_backlog(self, item, position, backlog):
        # update the position of the item in the given backlog
        try:
            # remove the item if existing from its current position
            backlog.remove(item)
        except ValueError:
            # not found in backlog, we just insert
            pass
        backlog.insert(position, item)

    # insert operation that updates the position numbers of every existing 
    # ticket after the inserted one. The Backlog query will resort the ticket
    # correctly next time it loads
    def insert(self, pos, ticket_or_backlogItem):
        """Insert the given ticket or backlog item in the given position in the
        current backlog"""
        # values returns the backlog items sorted by position
        current_backlog = self.values()
        # normalize to a BacklogItem
        existing_item = self._get_backlogItem_from_backlog(ticket_or_backlogItem,
                                                           current_backlog)
        if not existing_item:
            existing_item = self._get_backlog_item(ticket_or_backlogItem)

        pos = self._normalize_postion(pos, current_backlog)
        self._update_position_in_backlog(existing_item, pos, current_backlog)
        self._update_db_positions(current_backlog)
        # Updates the position of the given backlog item if possible, this is
        # needed as now we do not use the Object Identity anymore as we reload
        # every ticket as such and not as BacklogItem. So the caller might
        # expect that after a call to inster the position attribute is changed
        if isinstance(ticket_or_backlogItem, Backlog.BacklogItem):
            ticket_or_backlogItem.pos = pos
        return pos

    def _get_backlogItem_from_backlog(self, ticket_or_backlogItem, backlog):
        # returns the item with the given ticket_or_backlogItem if present in the backlog
        item_id = None
        if isinstance(ticket_or_backlogItem, Backlog.BacklogItem):
            item_id = ticket_or_backlogItem.ticket.id
        elif isinstance(ticket_or_backlogItem, AgiloTicket):
            item_id = ticket_or_backlogItem.id
        # REFACT: think about using a dictionary to store the backlog items and
        # return them with values() sorted to optimize getting by id
        for item in backlog:
            if item.ticket.id == item_id:
                return item

    def set_ticket_positions(self, positions):
        """Sets the ticket positions according to the given list of sorted ids"""
        positions = list(positions)
        backlog = self.values()
        for item in backlog:
            if item.ticket.id in positions:
                self._set_db_position(backlog, positions.index(item.ticket.id), item)
        # TODO: return the backlog as sorted to the client, may be is not needed
                
    def index(self, ticket_or_backlogItem):
        """Returns the index in which the given ticket or backlog item is found
        in this backlog. In case the item doesn't belong to the backlog will 
        raise a ValueError"""
        ticket_or_backlogItem = self._get_backlog_item(ticket_or_backlogItem)
        return self.values().index(ticket_or_backlogItem)

    def _update_db_positions(self, backlog):
        # Updates the position of all the db ticket affected by the move
        # Make sure we are working with a static copy of the Backlog
        if isinstance(backlog, Backlog):
            backlog = backlog.values()
        # AT: we assume that the backlog items are in the right order, we do
        # not 
        for index, item in enumerate(backlog):
            if item.pos != index:
                item.pos = index
                item.save()

    def _normalize_postion(self, target_position, backlog):
        # Returns the normalized position in respect to the current backlog
        # size.
        if target_position < 0:
            target_position = 0
        elif target_position > len(backlog):
            # reset to the last for appending
            target_position = len(backlog)
        return target_position

    # Returns new position (may have been normalized)
    def _set_db_position(self, backlog, target_position, bi):
        if isinstance(backlog, Backlog):
            backlog = backlog.values()

        target_position = self._normalize_postion(target_position, backlog)
        # REFACT: this should happen in the persistent object prop setter to simplify this code
        if target_position == bi.pos:
            return target_position

        # safely update the current item position
        bi.pos = target_position
        bi.save()
        return target_position

    # Utility methods to identify the backlog type
    def is_sprint_backlog(self):
        return self.config.type == BacklogType.SPRINT

    def is_milestone_backlog(self):
        return self.config.type == BacklogType.MILESTONE

    def is_global_backlog(self):
        return self.config.type == BacklogType.GLOBAL

    def sprint(self):
        if not self.is_sprint_backlog():
            raise ValueError("No sprint for backlog of type: %s" % self.config.type)
        return SprintModelManager(self.env).get(name=self.scope)

    # REFACT: remove
    def backlog_info(self):
        return dict(type=BacklogType.LABELS[self.config.type],
                    name=self.config.name,
                    sprint_or_release=self.scope)

    # Iterator methods, to allow the Backlog to be used directly in for loops
    def __iter__(self):
        """Returns the iterator"""
        self.__next = 0
        # reinitialize the backlog values at every iteration call
        self.__values = self.values()
        return self
        
    def next(self):
        """Returns the next item from the list of tickets, according
        to the actual sorting"""
        if self.__next < len(self.__values):
            self.__next += 1
            return self.__values[self.__next - 1]
        raise StopIteration
    
    def __len__(self):
        return len(self.values())
    
    def __contains__(self, item):
        item_id = None
        if isinstance(item, AgiloTicket):
            item_id = item.id
        elif isinstance(item, Backlog.BacklogItem):
            item_id = item.ticket.id
        else:
            return False
        return item_id in [bi.ticket.id for bi in self.values()]

    def __getattr__(self, name):
        # REFACT: remove, because compatibility should not be needed anymore
        # forward attributes missing to the config
        return getattr(self.config, name)

    def __str__(self):
        return "<%s (%s)>" % (self.config.name, self.scope)


class BacklogModelManager(PersistentObjectModelManager):
    """Manager for the Backlog model object. It allows to store and
    retrieve Backlogs, as well as creating new ones. The Manager also
    guarantees the Object identity"""
    model = Backlog
    
    class BacklogItemModelManager(PersistentObjectModelManager):
        model = Backlog.BacklogItem

    def create(self, save=True, **kwargs):
        """In case of a Backlog object we create a new type and we reload that
        type instace"""
        m = None #real backlog instance
        name = kwargs.pop(Key.NAME)
        config = BacklogConfiguration(self.env, name=name)

        if config.exists:
            # Already existing, we return None, it can be recreated
            return None
        # Now should set all the attribute passed into the parameters which are
        # not None, in the creation of a model may overwrite automatically set
        # values.
        for attr, value in kwargs.items():
            if value and hasattr(config, attr) and not callable(getattr(config, attr)):
                setattr(config, attr, value)
        # check if we have to save it or return it as is
        if save:
            # It is a new model we save it
            config.save()
        # check the scope of the backlog
        scope = kwargs.get(Key.SCOPE)
        if config.type in (BacklogType.SPRINT, BacklogType.MILESTONE) and scope:
            m = self.get(name=config.name, scope=scope)
        elif config.type == BacklogType.GLOBAL:
            m = self.get(name=config.name)
        return m

    def get(self, **kwargs):
        """Needs to set the scope to global if None, or the cache for global backlogs
        wouldn't work"""
        if Key.SCOPE in kwargs and kwargs[Key.SCOPE] is None or not Key.SCOPE in kwargs:
            kwargs[Key.SCOPE] = Key.GLOBAL
        return super(BacklogModelManager, self).get(**kwargs)

    def delete(self, model_instance, db=None):
        """This deletes also the configuration of a backlog type"""
        if model_instance is not None:
            model_instance.config.delete()
        super(BacklogModelManager, self).delete(model_instance=model_instance, db=db)

    def select(self, criteria=None, order_by=None, limit=None, db=None):
        """In case of backlog needs to return a list of Backlog types configured"""
        return BacklogConfiguration.select(self.env, criteria=criteria,
                                           order_by=order_by or [Key.NAME], limit=limit, db=db)

    def _get_model_key(self, model_instance=None):
        """Private method to return either a list of primary keys or a 
        tuple with all the primary keys and unique constraints needed 
        to identify a backlog."""
        if isinstance(model_instance, Backlog):
            return ((model_instance.name, 
                     model_instance.scope or 'global'), 
                     None)
        else:
            return [['name', 'scope'], None]
    

class BacklogUpdater(Component):
    
    implements(ITicketChangeListener)
    
    #===========================================================================
    # ITicketChangeListener methods
    #===========================================================================
    def ticket_created(self, ticket):
        """Called when a ticket is created."""
        pass
    
    def ticket_changed(self, ticket, comment, author, old_values):
        """
        Called when a ticket is modified.
        `old_values` is a dictionary containing the previous values of the
        fields that have changed.
        """
        ticket = AgiloTicket.as_agilo_ticket(ticket)
        debug(self, "Invoked for ticket #%s of type %s with: %s" % \
                     (ticket.id, ticket[Key.TYPE], old_values))
        
        if self._sprint_changed(old_values):
            # Load old sprint backlog, remove it
            old_sprint_name = old_values[Key.SPRINT]
            self._remove_from_sprint_backlogs(ticket, old_sprint_name)
        
        if self._milestone_changed(old_values):
            old_milestone_name = old_values[Key.MILESTONE]
            self._remove_from_milestone_backlogs(ticket, old_milestone_name)
        
        # REMOVED because of https://enterprise.hosted.agile42.com/ticket/1905
        # if self._should_remove_from_global_backlogs(ticket, old_values):
        #     # Remove ticket from global backlog
        #     self._remove_from_backlogs(ticket, None, backlog_type=BacklogType.GLOBAL)
    
    def _should_remove_from_global_backlogs(self, ticket, old_values):
        # any child still in backlog would pull it back in
        
        # sprint, milestone or status == closed -> go
        return (not old_values.get(Key.SPRINT) and ticket[Key.SPRINT]) or \
                (not old_values.get(Key.MILESTONE) and ticket[Key.MILESTONE]) or \
                (old_values.get(Key.STATUS) and ticket[Key.STATUS] == Status.CLOSED)
    
    def ticket_deleted(self, ticket):
        """Called when a ticket is deleted."""
        ticket = AgiloTicket.as_agilo_ticket(ticket)
        self._remove_from_all_backlogs(ticket)
    
    def _sprint_changed(self, old_values):
        return (old_values.get(Key.SPRINT, None) != None)
    
    def _milestone_changed(self, old_values):
        return (old_values.get(Key.MILESTONE, None) != None)
    
    def _remove_from_sprint_backlogs(self, ticket, sprint_name, db=None):
        self._remove_from_backlogs(ticket, sprint_name, BacklogType.SPRINT, db)
        debug(self, u"Removed Ticket: %s from all sprint backlogs." % ticket.id)
    
    def _remove_from_milestone_backlogs(self, ticket, milestone_name, db=None):
        self._remove_from_backlogs(ticket, milestone_name, BacklogType.MILESTONE, db)
        debug(self, u"Removed Ticket: %s from all milestone backlogs." % ticket.id)
    
    def _remove_from_backlogs(self, ticket, scope, backlog_type, db=None):
        # We don't know how many backlogs the user configured (e.g. sprint 
        # backlogs) and what's their name so we just get all sprint backlogs.
        sql_args = {}
        subquery_sql = "SELECT name FROM %(btable)s WHERE b_type=%(btype)d"
        sql_template = "DELETE FROM %(bticket)s WHERE ticket_id=%(ticket)s " + \
                        "AND name IN (" + subquery_sql + ")"
        if scope is not None:
            sql_template += " AND scope=%%(scope)s"
            sql_args['scope'] = scope
        parameters = dict(ticket=ticket.id, btype=backlog_type, 
                          bticket=BACKLOG_TICKET_TABLE, btable=BACKLOG_TABLE)
        sql_query = sql_template % parameters
        db, handle_ta = get_db_for_write(self.env, db)
        cursor = db.cursor()
        safe_execute(cursor, sql_query, sql_args)
        if handle_ta:
            db.commit()
    
    def _remove_from_all_backlogs(self, ticket):
        """Removes a ticket from all the backlog where is in"""
        debug(self, u"Called Remove from all Backlogs: %s" % ticket)
        # Not checking if the ticket is in the Backlog, cause it is
        # cheaper to run a delete for nothing than load a whole backlog
        # Get a db connection
        db = self.env.get_db_cnx()
        cursor = db.cursor()
        try:
            safe_execute(cursor, "DELETE FROM %s WHERE ticket_id=%%s" % BACKLOG_TICKET_TABLE, [ticket.id])
            debug(self, u"Removed ticket: %s from all backlogs" % ticket.id)
            db.commit()
        except Exception, e:
            self.env.log.exception(exception_to_unicode(e))
            error(self, "An error occurred while deleting ticket: %s from backlogs:" % ticket)
    # Adds the as_dict behavior to the Backlog
    Backlog = add_as_dict(Backlog)
