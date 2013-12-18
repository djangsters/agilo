# -*- coding: utf8 -*-
#   Copyright 2009 agile42 GmbH All rights reserved
#   Copyright 2011 Agilo Software GmbH All rights reserved
#
#   Authors:
#        - Felix Schwarz <felix.schwarz__at__agile42.com>

import re
import time

from trac.core import TracError
from trac.resource import Resource
from trac.web.api import RequestDone

from agilo.api.view import JSONView
from agilo.ticket import AgiloTicket, AgiloTicketModelManager, \
    AgiloTicketSystem, TicketController
from agilo.ticket.web_ui import AgiloTicketModule
from agilo.ticket.workflow_support import TicketStatusManipulator
from agilo.utils import Action, Key, Status, Realm
from agilo.utils.compat import exception_to_unicode

__all__ = ['TicketDetailView', 'TicketUpdateView', 'TicketCreateView']


class RequestWrapper(object):
    """In order to send a JSON request to trac's TicketModule we need to 
    manipulate some request parameters. This class guards the original request
    so that we don't have to do any cleanup afterwards."""
    
    def __init__(self, req, args):
        self.__dict__['_req'] = req
        self.__dict__['args'] = args
        
        for name in ('method', 'authname'):
            self.__dict__[name] = getattr(req, name)
        
        self.__dict__['_url'] = None
        self.__dict__['_start_response'] = None
    
    def __getattr__(self, name):
        return getattr(self._req, name)
    
    def __setattr__(self, name, value):
        if name in self.__dict__:
            self.__dict__[name] = value
        else:
            setattr(self._req, name, value)
    
    def redirect(self, url, permanent=False):
        self._url = url
        raise RequestDone


class TicketDetailView(JSONView):
    
    url = '/json/tickets'
    url_regex = '/(?P<id>\d+)?$'
    
    def do_get(self, req, args):
        """
        Perform a get for the given ticket id, or all the tickets if 
        no id is provided.
        """
        ticket_id = args.get('id')
        command = None
        if ticket_id:
            command = TicketController.GetTicketCommand(self.env, ticket=ticket_id)
            command.native = True
        else:
            # Now artificially limited to 20 to avoid explosion
            # TODO: support paging here
            command = TicketController.ListTicketsCommand(self.env, limit=20)
        result = TicketController(self.env).process_command(command)
        # AT: really needed?
        assert result != None
        if not isinstance(result, list):
            result = [result]
        # send the serialized list back
        ticket_module = AgiloTicketModule(self.env)
        return [ticket_module.ticket_as_json(req, ticket.id) for ticket in result]


class AbstractJSONTicketModuleView(JSONView):
    
    url = ''
    url_regex = '^$'
    
    def rename_fields(self, req, ticket_type=None):
        fields = AgiloTicketSystem(self.env).get_ticket_fields(ticket_type)
        for field in fields:
            name = field[Key.NAME]
            if name in req.args:
                value = req.args[name]
                if not isinstance(value, basestring):
                    value = str(value)
                del req.args[name]
                req.args['field_' + name] = value
    
    def _ticket_without_cache(self, ticket_id):
        ticket = AgiloTicket(self.env, ticket_id)
        return ticket
    
    def get_ticket_as_json(self, req, ticket_id):
        # trac's TicketModule will instantiate a ticket directly which 
        # circumvents all our caches so we need to ignore the caches
        # as well...
        ticket = self._ticket_without_cache(ticket_id)
        return AgiloTicketModule(self.env).ticket_as_json(req, ticket)
    
    def call_ticket_module(self, req, method_name):
        ticket_module = AgiloTicketModule(self.env)
        try:
            getattr(ticket_module, method_name)(req)
            return False
        except RequestDone:
            return True
    
    def get_ticket_id(self, args):
        ticket_id = args.get('ticket_id')
        if ticket_id is None:
            return None
        return int(ticket_id)
    
    def get_ticket_as_json_if_allowed(self, req):
        ticket_id = self.get_ticket_id(req.args)
        if ticket_id is None:
            return {}
        ticket = AgiloTicketModelManager(self.env).get(tkt_id=ticket_id)
        if not req.perm.has_permission(Action.TICKET_VIEW, ticket.resource):
            return {}
        
        return self.get_ticket_as_json(req, ticket.id)
    
    def error_response(self, req, current_data, errors, code=500):
        if current_data is None or 0 == len(current_data):
            current_data = self.get_ticket_as_json_if_allowed(req)
        
        return super(AbstractJSONTicketModuleView, self).error_response(req, current_data, errors, code)


class TicketUpdateView(AbstractJSONTicketModuleView):
    
    url = '/json/tickets'
    url_regex = '/(?P<ticket_id>\d+)/?$'
    
    def _ticket(self, ticket_id, native=False):
        command = TicketController.GetTicketCommand(self.env, ticket=ticket_id)
        command.native = native
        return TicketController(self.env).process_command(command)
    
    def _rename_field_names(self, req, ticket_id):
        ticket = self._ticket(ticket_id, native=True)
        ticket_type = ticket[Key.TYPE]
        self.rename_fields(req, ticket_type)
    
    def _modify_ticket_attributes(self, req, args):
        ticket_id = args['ticket_id']
        wrapped_request = RequestWrapper(req, args)
        wrapped_request.args.update(dict(id=ticket_id, action='leave'))
        self._rename_field_names(wrapped_request, ticket_id)
        
        # FIXME (AT): we need to increase granularity here, calling the process ticket
        # request is very expensive and fills the req with a lot of genshi things that
        # we do not need. Can we reduce the scope of this call? May be refactor the
        # AgiloTicketModule?
        update_was_successful = self.call_ticket_module(wrapped_request, '_process_ticket_request')
        warnings = wrapped_request.chrome['warnings']
        return update_was_successful, warnings
    
    def _ticket_owner_should_be_changed(self, args, ticket):
        return (Key.OWNER in args) and (args[Key.OWNER] != ticket[Key.OWNER])
    
    def _get_username_of_acting_user(self, req, args, ticket):
        authname = req.authname
        # Sometimes the logged in user is not part of the team but should be 
        # able to change owners by dragging the tasks (e.g. Scrum Master during
        # the daily standup).
        if Key.OWNER in args:
            authname = args[Key.OWNER]
        return authname
    
    def _simulate_status_change_and_update_request_parameters(self, req, args, ticket_id):
        # TicketStatusManipulator will change the ticket and we don't want to pollute
        # the cache
        ticket = self._ticket_without_cache(ticket_id)
        wrapped_request = RequestWrapper(req, args)
        wrapped_request.authname = self._get_username_of_acting_user(req, args, ticket)
        manipulator = TicketStatusManipulator(self.env, wrapped_request, ticket)
        ticket_changed = manipulator.change_status_to(args['simple_status'])
        if ticket_changed:
            for attribute_name in ticket._old:
                args[attribute_name] = ticket[attribute_name]
    
    def get_last_changetime(self, ticket_json):
        return ticket_json['time_of_last_change']
    
    def wait_if_last_change_was_within_this_second(self, req, ticket_id, args):
        if AgiloTicketSystem(self.env).is_trac_012():
            return
        # Trac can't save two ticket changes within one second
        last_changetime = self.get_last_changetime(self.get_ticket_as_json(req, ticket_id))
        if last_changetime == self.get_last_changetime(args):
            time.sleep(1)
    
    def _send_error(self, req, ticket_id, errors, code=500):
        json_ticket = self.get_ticket_as_json(req, ticket_id)
        return self.error_response(req, json_ticket, errors, code=code)
    
    def is_unknown_status(self, status):
        known_statuses = AgiloTicketSystem(self.env).valid_ticket_statuses()
        known_statuses = known_statuses + TicketStatusManipulator.DEFAULT_SIMPLE_STATUSES
        return not status in known_statuses
    
    def do_post(self, req, args):
        # FIXME(AT): in this method the same ticket is loaded twice it is an expensive
        # operation that we could limit. The resource is loading the ticket using the
        # Trac introspection, and later in the _simulate_sta... it is loaded again. As
        # the ticket is also a Resource of itself this can be changed by loading it
        # directly from here and pass it through instead of ticket_id
        ticket_id = self.get_ticket_id(args)
        ticket_resource = Resource(Realm.TICKET)(id=ticket_id)
        req.perm.assert_permission(Action.TICKET_VIEW, ticket_resource)

        self.wait_if_last_change_was_within_this_second(req, ticket_id, args)
        # we pack all changes in one transaction to minimize waiting times
        if 'simple_status' in args:
            if not req.perm.has_permission(Action.TICKET_EDIT, ticket_resource):
                error = 'AGILO_TICKET_EDIT privileges are required to perform this operation on Ticket #%s' % ticket_id
                self._send_error(req, ticket_id, [error], 403)
            
            status = args['simple_status']
            if self.is_unknown_status(status):
                error_message = 'Invalid status: %s. Try to configure a workflow that includes this status.' % status
                self._send_error(req, ticket_id, [error_message])
            self._simulate_status_change_and_update_request_parameters(req, args, ticket_id)
        try:
            success, errors = self._modify_ticket_attributes(req, args)
        # REFACT: mixing success boolean and exception is confusing
        except TracError, e:
            success = False
            errors = [exception_to_unicode(e)]
        if not success:
            # REFACT: If this was not caused by a TracError (but, for instance,
            # by a RuleValidationException), return code should be 400.
            self._send_error(req, ticket_id, errors)
        
        return self.get_ticket_as_json(req, ticket_id)
    

class TicketCreateView(AbstractJSONTicketModuleView):
    
    url = '/json/tickets'
    url_regex = '/?$'
    
    def _prepare_request_for_ticketmodule(self, req):
        req.method = 'POST'
        # AT: we have to add a flag to tell Agilo that this request
        # is not a real one, but is redirected from another component
        req.args['redirected'] = True
        
        if Key.STATUS not in req.args:
            req.args[Key.STATUS] = Status.NEW
    
    def _get_ticket_id_from_urlstring(self, url):
        match = re.search('/ticket/(?P<ticket_id>\d+)$', url)
        assert (match is not None), 'Could not get ticket id ' + repr(url)
        return match.group('ticket_id')
    
    def _create_ticket(self, req, args):
        wrapped_request = RequestWrapper(req, args)
        self._prepare_request_for_ticketmodule(wrapped_request)
        self.rename_fields(wrapped_request)
        
        ticket_id = None
        warnings = None
        update_was_successful = self.call_ticket_module(wrapped_request, '_process_newticket_request')
        if update_was_successful:
            ticket_id = self._get_ticket_id_from_urlstring(wrapped_request._url)
            args['ticket_id'] = ticket_id
            req.args['ticket_id'] = ticket_id
        else:
            warnings = wrapped_request.chrome['warnings']
        return update_was_successful, ticket_id, warnings
    
    def do_put(self, req, args):
        trac_type = AgiloTicketSystem(self.env).normalize_type(args.get(Key.TYPE))
        if trac_type is None:
            self.error_response(req, {}, ['Must specify a type.'])
        
        success, ticket_id, errors = self._create_ticket(req, args)
        if not success:
            self.error_response(req, {}, errors)
        
        ticket_resource = Resource('ticket')(id=ticket_id)
        if not req.perm.has_permission(Action.TICKET_VIEW, ticket_resource):
            self.error_response(req, {}, ['No permission to see ticket %d' % ticket_id])
        return self.get_ticket_as_json(req, ticket_id)

