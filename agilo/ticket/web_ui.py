# -*- coding: utf-8 -*-
#   Copyright 2007-2008 Agile42 GmbH - Andrea Tomasini
#   Copyright 2011 Agilo Software GmbH All rights reserved 
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
# 
# Authors:
#     - Andrea Tomasini <andrea.tomasini__at__agile42.com>
#     - Felix Schwarz <felix.schwarz__at__agile42.com>

from datetime import datetime
import re

from pkg_resources import resource_filename
import trac.ticket.web_ui
from trac.core import Component, implements, TracError
from trac.ticket.api import ITicketManipulator
from trac.ticket.notification import TicketNotifyEmail
from trac.util.datefmt import utc
from trac.util.translation import _
from trac.web.chrome import add_ctxtnav, add_script, add_stylesheet, add_notice
from trac.web.main import IRequestHandler

from agilo.ticket.api import AgiloTicketSystem
from agilo.ticket.links import LINKS_SEARCH_URL, LINKS_URL
from agilo.ticket.links.model import LinksConfiguration
from agilo.ticket.model import AgiloTicket, AgiloTicketModelManager
from agilo.ticket.renderers import Renderer
from agilo.utils import Action, Key, MANDATORY_FIELDS
from agilo.utils.config import AgiloConfig
from agilo.utils.compat import exception_to_unicode, json
from agilo.utils.log import debug, error
from agilo.utils.permissions import AgiloPolicy
from agilo.utils.web_ui import CoreTemplateProvider


VIEW_TICKET_TEMPLATE = 'agilo_ticket_view.html'
EDIT_TICKET_TEMPLATE = 'agilo_ticket_edit.html'
NEW_TICKET_TEMPLATE = 'agilo_ticket_new.html'


__all__ = ['AgiloTicketModule', 'CreatePermissionChecker']


class AgiloTicketModule(trac.ticket.web_ui.TicketModule):
    implements(IRequestHandler)
    
    def __init__(self, *args, **kwargs):
        """
        Initialize the component and take care of the Monkey Patching
        if the environment is an agilo enabled one
        """
        if AgiloConfig(self.env).is_agilo_enabled:
            # This is some sort of monkey patching for trac's TicketModule so that it 
            # returns AgiloTickets by default and uses the AgiloTicketSystem as well
            trac.ticket.web_ui.Ticket = AgiloTicket
            trac.ticket.web_ui.TicketSystem = AgiloTicketSystem
        else:
            self.__class__ = trac.ticket.web_ui.TicketModule
    
    def ticket_as_json(self, req, ticket_or_ticket_id):
        if isinstance(ticket_or_ticket_id, AgiloTicket):
            ticket = ticket_or_ticket_id
        else:
            # Use the model manager that uses the request cache
            ticket = AgiloTicketModelManager(self.env).get(tkt_id=ticket_or_ticket_id)
        ticket_json = ticket.as_dict()
        ticket_json['can_edit'] = self.can_edit_ticket(req, ticket)
        return ticket_json
    
    def can_edit_ticket(self, req, ticket_or_type):
        """Return True if the current user can edit the given ticket or ticket type"""
        decision = False
        if ticket_or_type and req:
            resource = t_type = None
            if isinstance(ticket_or_type, AgiloTicket):
                resource = ticket_or_type.resource
            else:
                t_type = ticket_or_type
            policy = AgiloPolicy(self.env)
            decision = policy.check_ticket_edit(req.authname, resource, 
                                                req.perm, t_type=t_type)
        return decision
    
    def _edit_page_requested(self, req):
        return False
        # return (req.args.get(Key.PANE) == 'edit')
    
    def _is_new_ticket(self, ticket):
        return (not ticket.exists)
    
    def _display_back_to_url(self, req):
        """
        Check in the session for a back_to_url link to visualize in 
        the Jump Back
        """
        back_to_key = 'back_to_url'
        
        back_to_url = None
        if req.args.has_key(back_to_key):
            back_to_url = req.args.get(back_to_key)
        elif req.session.has_key(back_to_key):
            back_to_url = req.session.get(back_to_key)
            
        debug(self, "$$$ VALUE OF back_to_url: %s $$$" % back_to_url)
        if back_to_url is not None:
            # Add it directly to the context navigation bar
            add_ctxtnav(req, _('Jump Back'), back_to_url)
            
    def _set_back_to_url(self, req):
        """Sets the back_to_url in the session"""
        back_to_key = 'back_to_url'
        referrer_key = 'HTTP_REFERER'
        
        referrer_url = req.environ.get(referrer_key, None)
        if referrer_url is not None and \
                ('/newticket' not in referrer_url and '/ticket' not in referrer_url):
            # There is no existing back_to_url, set it now, for this ticket
            req.session[back_to_key] = req.environ[referrer_key]
    
    def _rendered_ticket_value(self, ticket, field):
            # Trac renders some ticket attributes already:
            # - 'cc' (display only local parts of email address if user has no
            #         EMAIL_VIEW permission)
            # - xyz.format = wiki (use wiki formatting in arbitrary fields)
            # We want to leave these fields untouched
            # 
            # However if there is no content in the field, we'd like to show 'n.a.'
            # anyway. This could be done by: 
            #      if not field.get(Key.RENDERED)
            # Unfortunately, somehow the field value is sometimes empty (don't 
            # know if this is a bug in Agilo or Trac). Trac 0.12 will also 
            # linkify all attributes even if no value was set.
            # Due to these two complications, I had to check explicitely for
            # cc and wiki fields.
            was_rendered_by_trac = field.get(Key.RENDERED)
            is_wiki_field = field.get('format') == 'wiki'
            is_cc_field = field[Key.NAME] == 'cc'
            if was_rendered_by_trac and (is_wiki_field or is_cc_field):
                return field.get(Key.RENDERED)
            
            return Renderer(ticket, field[Key.NAME])
    
    # OVERRIDE
    def _prepare_fields(self, req, ticket, field_changes=None):
        """Set specific renderer for the ticket fields"""
        fields = super(AgiloTicketModule, self)._prepare_fields(req, ticket)
        if not AgiloConfig(self.env).is_agilo_enabled:
            return fields
        
        from agilo.scrum import SprintController
        sp_controller = SprintController(self.env)
        
        for field in fields:
            field[Key.RENDERED] = self._rendered_ticket_value(ticket, field)
            # makes the nice Sprint pulldown to emulate the milestone one
            if field[Key.NAME] == Key.SPRINT:
                get_options = SprintController.GetSprintOptionListCommand(self.env,
                                                                          sprint_names=field[Key.OPTIONS])
                closed, running, to_start = sp_controller.process_command(get_options)
                field[Key.OPTIONS] = []
                field[Key.OPTIONS_GROUP] = [
                    {Key.LABEL: _('Running (by Start Date)'),
                     Key.OPTIONS: running},
                    {Key.LABEL: _('To Start (by Start Date)'),
                     Key.OPTIONS: to_start},
                    {Key.LABEL: _('Closed (by Start Date)'),
                     Key.OPTIONS: closed},
                ]
        return fields
    
    def _prepare_create_referenced(self, req, data):
        """
        Prepares the list of create-able referenced ticket for the current ticket
        given the linking rules and the role of the current user, e.g. A product
        owner can edit a task container, but can't create tasks on it.
        """
        ticket = data.get(Key.TICKET)
        if ticket is not None:
            create_referenced = [t_type for t_type in ticket.get_alloweds() \
                                 if self.can_edit_ticket(req, t_type.dest_type)]
            data['create_referenced'] = create_referenced
    
    def _check_if_user_can_create_referenced_tickets(self, req, data):
        if 'ticket' not in data:
            data['can_create_at_least_one_referenced_type'] = False
            return


        ticket = data['ticket']
        ticket_type = ticket[Key.TYPE]

        can_create_at_least_one_referenced_type = False
        for allowed_type in LinksConfiguration(self.env).get_allowed_destination_types(ticket_type):
            permission_name = CoreTemplateProvider(self.env).get_permission_name_to_create(allowed_type)
            if permission_name in req.perm:
                can_create_at_least_one_referenced_type = True
                break
        data['can_create_at_least_one_referenced_type'] = can_create_at_least_one_referenced_type

    # OVERRIDE
    def _process_ticket_request(self, req):
        if not AgiloConfig(self.env).is_agilo_enabled:
            return super(AgiloTicketModule, self)._process_ticket_request(req)
        
        from agilo.scrum.workflow.api import RuleValidationException
        # Compute the back_to_url
        self._set_back_to_url(req)
        # Check if the delete has been called
        if 'delete' in req.args:
            # load the ticket, delete it and change the ID to another one before
            # sending it to trac
            self._do_delete(req)
        # Process the Ticket the TRAC way
        template = data = content_type = None
        try:
            template, data, content_type = super(AgiloTicketModule, self)._process_ticket_request(req)
        except RuleValidationException, e:
            raise TracError(exception_to_unicode(e))
        
        if template in ('diff_view.html', 'history_view.html'):
            # We don't care about these pages, just display them
            return template, data, content_type
        
        # Adds specific agilo ticket CSS
        add_stylesheet(req, "agilo/stylesheet/agilo_ticket.css")
        # Sets the right tab in the pane view
        tab = {'view': 'selected', 'edit': None}
        self._display_back_to_url(req)
        resource = data['ticket'].resource
        can_edit_ticket = req.perm.has_permission(Action.TICKET_EDIT_PAGE_ACCESS, resource)
        may_delete_ticket = req.perm.has_permission(Action.TICKET_DELETE, resource)
        template = VIEW_TICKET_TEMPLATE
        # if self._edit_page_requested(req):
        if not can_edit_ticket:
            msg = 'In order to edit this ticket you need to be either: ' \
                  'a Product Owner, The owner ' \
                  'or the reporter of the ticket, or, in case of a Task ' \
                  'not yet assigned, a team_member"'
            add_notice(req, _(msg))

            # msg = data['edit_permissions_msg']
            # req.perm.assert_permission(msg)
        else:
            add_stylesheet(req, "agilo/stylesheet/jquery.autocomplete.css")
            add_script(req, "agilo/js/lib/jquery.bgiframe.min.js")
            add_script(req, "agilo/js/lib/jquery.dimensions.js")
            add_script(req, "agilo/js/lib/jquery.autocomplete.js")
            add_script(req, "agilo/js/links_autocompletion.js")
            data['LINKS_SEARCH_URL'] = req.href(LINKS_SEARCH_URL)
            data['LINKS_URL'] = req.href(LINKS_URL)
            data['may_edit_links'] = Action.LINK_EDIT in req.perm
            self._prepare_create_referenced(req, data)

        self._check_if_user_can_create_referenced_tickets(req, data)

        # template = EDIT_TICKET_TEMPLATE
        # Sets the right tab in the pane view
        # tab = {'view': None, 'edit': 'selected'}
        # Put the tab in data for Genshi
        # data['tab'] = tab
        data['can_edit_ticket'] = can_edit_ticket
        may_edit_ticket = req.perm.has_permission(Action.TICKET_EDIT, resource)
        data['may_edit_ticket'] = may_edit_ticket
        data['may_delete_ticket'] = may_delete_ticket
        data['may_comment_ticket'] = req.perm.has_permission(Action.TICKET_APPEND, resource)
        self._inject_json_data(req, data['ticket'].id)
        return (template, data, content_type)
    
    def _inject_json_data(self, req, ticket_id):
        raw_json = json.dumps(self.ticket_as_json(req, ticket_id))
        req.send_header('X-Agilo-Ticket-ID', ticket_id)
        req.send_header('X-Agilo-Ticket-JSON', raw_json)
    
    def _do_delete(self, req):
        """Deletes the current ticket and tries to redirect to the 
        previous one, or to the first available ticket, if not 
        existing, redirect to the dashboard"""
        if not Action.TICKET_DELETE in req.perm:
            raise TracError("You don't seem to have TICKET_DELETE rights...")
        t_id = req.args.get('id')
        if t_id is not None:
            t_id = int(t_id)
            db = self.env.get_db_cnx()
            # Need to use Ticket, if agilo is not enabled may crash
            ticket = trac.ticket.web_ui.Ticket(self.env, t_id, db=db)
            n_id = ticket.delete(db=db)
            # Now redirect to the ticket or dashboard
            if n_id is not None:
                url = req.href.ticket(n_id)
            else:
                from agilo.scrum import DASHBOARD_URL
                url = req.href(DASHBOARD_URL)
            # Check if there is a Query Session stored and remove the ticket 
            # form there
            if 'query_tickets' in req.session:
                tickets = req.session['query_tickets'].split()
                if unicode(t_id) in tickets:
                    tickets.remove(unicode(t_id))
                    req.session['query_tickets'] = u' '.join(tickets)
            req.redirect(url)
        
    def _add_linking_source_to_template_data(self, req, data):
        if 'src' in req.args:
            debug(self, "Got SRC: %s" % req.args['src'])
            try:
                data['src'] = int(req.args['src'])
            except (ValueError, TypeError):
                raise TracError("src (%s) must be a valid ticket id!" % req.args['src'])
    
    def _add_links_for_ticket(self, req, ticket):
        try:
            src_ticket_id = int(req.args['src'])
        except:
            pass
        else:
            src_ticket = AgiloTicketModelManager(self.env).get(tkt_id=src_ticket_id)
            if ticket != None and src_ticket != None:
                if src_ticket.is_link_to_allowed(ticket):
                    return src_ticket.link_to(ticket)
                else:
                    msg = 'You may not link #%d (Type %s) to #%d (Type %s)'
                    error(self, msg % (src_ticket.id, src_ticket.get_type(),
                                       ticket.id, ticket.get_type()))
    
    # OVERRIDE
    # force_collision_check is a parameter for Trac 0.12
    def _validate_ticket(self, req, ticket, force_collision_check=False):
        if 'ts' in req.args:
            match = re.search('^(\d+)$', req.args.get('ts') or '')
            if match:
                timestamp = int(match.group(1))
                last_changed = datetime.utcfromtimestamp(timestamp).replace(tzinfo=utc)
                req.args['ts'] = str(last_changed)
        ticket_system = AgiloTicketSystem(self.env)
        trac_ticket_system = super(AgiloTicketModule, self)
        
        if ticket_system.is_trac_012():
            return trac_ticket_system._validate_ticket(req, ticket, force_collision_check=force_collision_check)
        return trac_ticket_system._validate_ticket(req, ticket)
    
    # OVERRIDE
    def _do_create(self, req, ticket):
        if not AgiloConfig(self.env).is_agilo_enabled:
            return super(AgiloTicketModule, self)._do_create(req, ticket)
        # AT: to have full control of the flow we need to rewrite the
        # do create, in this way we will be able to add options to the
        # redirect, rather than only intervening once the request as
        # already been sent out from trac. This needs to be kept under
        # control in case of changes :-)
        from agilo.scrum.workflow.api import RuleValidationException
        try:
            ticket.insert()
            req.perm(ticket.resource).require('TICKET_VIEW')

            # Notify
            try:
                tn = TicketNotifyEmail(self.env)
                tn.notify(ticket, newticket=True)
            except Exception, e:
                self.log.error("Failure sending notification on creation of "
                        "ticket #%s: %s", ticket.id, exception_to_unicode(e))
            
            # AT: if the source of a link is there, means we are
            # coming from the edit panel of a ticket, and that is
            # where we want to go back to after linking
            if 'src' in req.args:
                if self._add_links_for_ticket(req, ticket) and \
                        not 'redirected' in req.args:
                    # redirect to the calling ticket, in edit pane 
                    # after creating the link successfully
                    req.redirect(req.href.ticket(req.args['src'],
                                                 {'pane': 'edit'}))
            
            # Redirect the user to the newly created ticket or add attachment
            if 'attachment' in req.args:
                req.redirect(req.href.attachment('ticket', ticket.id,
                                                 action='new'))
            # if no option is there, than redirect to the normal view
            # page of the ticket
            req.redirect(req.href.ticket(ticket.id))
            
        except RuleValidationException, e:
            raise TracError(e)
    
    def _ticket_types_the_user_can_create_or_modify(self, ticket_type, current_options, create_perms):
        """Returns the list of the allowed ticket types that the current logged
        in user can define or modify"""
        ticket_type_options = list() # make a copy
        for ticket_type in current_options:
            if ticket_type in create_perms:
                ticket_type_options.append(ticket_type)
        return ticket_type_options
    
    def _hide_fields_not_configured_for_this_type(self, req, data):
        ticket_type = req.args[Key.TYPE]
        ats = AgiloTicketSystem(self.env)
        normalized_type = ats.normalize_type(ticket_type)
        data[Key.TYPE] = normalized_type
        fields_for_type = AgiloConfig(self.env).TYPES.get(normalized_type, [])
        create_perms = CoreTemplateProvider(self.env).create_permissions(req)
        
        if normalized_type in create_perms:
            for data_field in data['fields']:
                field_name = data_field[Key.NAME]
                if field_name == Key.TYPE:
                    current_options = data_field.get('options', [])
                    data_field['options'] = \
                        self._ticket_types_the_user_can_create_or_modify(normalized_type, current_options, create_perms)
                    data['type_selection'] = data_field
                    data_field[Key.SKIP] = True
                elif not field_name in fields_for_type:
                    # Skip the field and the value if it's not for this type
                    data_field[Key.SKIP] = True
                elif data_field[Key.SKIP] and (field_name not in MANDATORY_FIELDS):
                    # We have to make all fields visible which belong to 
                    # this ticket type. Unfortunately, Trac just creates 
                    # a Ticket (though an AgiloTicket due to our monkey 
                    # patching) and we can't influence the instantiation 
                    # itself. 
                    # Therefore it just depends on the default ticket type 
                    # set in the environment what fields this ticket has. 
                    # Therefore some fields are marked skipped although they
                    # should be displayed.
                    # trac itself skips some fields because it want to have
                    # more control over the positioning. We have to respect
                    # that.
                    
                    # fs, 04.11.2008: I thought about moving this condition 
                    #  to_prepare_fields where I think this code should live
                    # but then I would have to copy all the conditions and
                    # probably the code is here for a good reason so I'm 
                    # just adding it here.
                    data_field[Key.SKIP] = False
                elif field_name == Key.OWNER and ats.restrict_owner:
                    # we need to transform the field into a list of users
                    ats.eventually_restrict_owner(data_field)
        elif len(create_perms) > 0:
            # Redirect to the first allowed type for the given user.
            first_allowed_type = create_perms[0]
            req.redirect(req.href.newticket(type=first_allowed_type))
        else:
            if ticket_type not in AgiloConfig(self.env).ALIASES:
                raise TracError(u"Unkown type '%s'!" % ticket_type)
            raise TracError("You are not allowed to create a %s!" % ticket_type)
        return data
    
    # OVERRIDE
    def _process_newticket_request(self, req):
        # call trac create ticket
        #from agilo.utils.log import print_http_req_info
        #print_http_req_info(self.env, req, stdout=True)
        
        # FIXME: (AT) The TicketModule call will set the ticket type again via
        # a populate call, that will trigger again the _reset_type_fields()
        template, data, content_type = \
            super(AgiloTicketModule, self)._process_newticket_request(req)
        if not AgiloConfig(self.env).is_agilo_enabled:
            return (template, data, content_type)
        
        if Key.TYPE in req.args:
            data = self._hide_fields_not_configured_for_this_type(req, data)
        self._set_back_to_url(req)
        self._add_linking_source_to_template_data(req, data)
        return (NEW_TICKET_TEMPLATE, data, content_type)
    
    # OVERRIDE
    # AT: We need to check if one of the field sent is the type, in which case
    # we will have to set the type first, than send the other values
    def _populate(self, req, ticket, plain_fields=False):
        fields = req.args
        if not plain_fields:
            fields = dict([(k[6:],v) for k,v in fields.items()
                           if k.startswith('field_')])
        
        if Key.TYPE in fields:
            ticket._reset_type_fields(fields[Key.TYPE])
            
        ticket.populate(fields)
        # special case for updating the Cc: field
        if 'cc_update' in req.args:
            cc_action, cc_entry, cc_list = self._toggle_cc(req, ticket['cc'])
            if cc_action == 'remove':
                cc_list.remove(cc_entry)
            elif cc_action == 'add':
                cc_list.append(cc_entry)
            ticket['cc'] = ', '.join(cc_list)
    
    # overriding the INavigationContributor method from trac's TicketModule 
    # so that the 'new ticket' item is not visible (because agilo has its own
    # methods to create new tickets.
    def get_navigation_items(self, req):
        if not AgiloConfig(self.env).is_agilo_enabled:
            super(AgiloTicketModule, self).get_navigation_items(req)
        return []
    
    
    # Overriding the ITemplateProvider so that we can add our own template 
    # directories here
    def get_htdocs_dirs(self):
        trac_htdocs_dirs = super(AgiloTicketModule, self).get_htdocs_dirs()
        agilo_ticket_htdocs = [('agilo', resource_filename('agilo.ticket', 'htdocs'))]
        agilo_ticket_htdocs.extend(trac_htdocs_dirs)
        return agilo_ticket_htdocs

    def get_templates_dirs(self):
        trac_template_dirs = super(AgiloTicketModule, self).get_templates_dirs()
        agilo_ticket_templates = [resource_filename('agilo.ticket', 'templates')]
        agilo_ticket_templates.extend(trac_template_dirs)
        return agilo_ticket_templates



class CreatePermissionChecker(Component):
    "Check if the user has the permission to create a new ticket of that type."
    
    implements(ITicketManipulator)
    
    def prepare_ticket(self, req, ticket, fields, actions):
        pass

    def validate_ticket(self, req, ticket):
        if not ticket.exists:
            typename = ticket.get_type()
            permission_name = 'CREATE_%s' % typename.upper()
            permission_name = getattr(Action, permission_name, permission_name)
            if permission_name not in req.perm(ticket.resource):
                msg = _("No permission to create or edit a %s.")  % typename
                return [(None, msg)]
        return []

