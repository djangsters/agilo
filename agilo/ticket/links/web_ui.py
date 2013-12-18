# -*- coding: utf8 -*-
#   Copyright 2007 Andrea Tomasini <andrea.tomasini_at_agile42.com>
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

from pkg_resources import resource_filename

from trac.core import Component, implements, TracError
from trac.web.main import IRequestHandler
from trac.web.chrome import ITemplateProvider

from agilo.utils import Key, Action
from agilo.ticket.links import LINKS_URL


class LinksModule(Component):
    """Links Module, responsible to create links between tickets"""
    
    implements(IRequestHandler, ITemplateProvider)
    
    #=============================================================================
    # ITemplateProvider methods
    #=============================================================================
    def get_htdocs_dirs(self):
        return []
    
    def get_templates_dirs(self):
        return [resource_filename('agilo.ticket.links', 'templates')]
    
    #=============================================================================
    # IRequestHandler methods
    #=============================================================================
    def match_request(self, req):
        return req.path_info.startswith(LINKS_URL)

    def process_request(self, req):
        # Check if it has been called with 'src' and 'dest' arguments or abort
        if not req.args.has_key('src') or not req.args.has_key('dest') or not req.args.has_key('cmd'):
            raise TracError("Links should be called with 'cmd', 'src' and 'dest' parameters",
                            "Links: Source and/or Destination are Missing!")
        else:
            # Flag for ticket update
            update_ticket = False
            # Avoid recursive imports
            from agilo.ticket.model import AgiloTicketModelManager
            tm = AgiloTicketModelManager(self.env)
            try:
                src = int(req.args.get('src'))
                # Now that we have the ticket we can check permission to link or edit
                ticket_perm = req.perm('ticket', src)
                if Action.TICKET_EDIT not in ticket_perm or \
                        Action.LINK_EDIT not in ticket_perm:
                    raise TracError("You (%s) are not authorized to edit this ticket" % \
                                    req.authname)
                dest = int(req.args.get('dest'))
                cmd = req.args.get('cmd')
                url = req.args.get('url_orig') or None
            except:
                raise TracError("Source is not valid: src=%s" % req.args.get('src'))
            # Create the LinkEndPoint for the source and destination if not existing
            sle = tm.get(tkt_id=src)
            dle = tm.get(tkt_id=dest)
            src_type = sle.get_type()
            dest_type = dle.get_type()
            
            if cmd == 'create link':
                if not sle.link_to(dle):
                    raise TracError("Links not allowed between %s->%s! The types are incompatible or" \
                                    " the link already exists" % (src_type, dest_type))
                else:
                    req.args[Key.OUTGOING_LINKS] = 'created link %s(#%s)->%s(#%s)' % \
                                                    (src_type, src, dest_type, dest)
                    req.args['comment'] = 'Added link to %s(#%s)' % \
                                           (dest_type, dest)
                    update_ticket = True   
            elif cmd == 'delete link':
                if not sle.del_link_to(dle):
                    raise TracError("Link not existing! %s(#%s)->%s(#%s)" % \
                                    (src_type, src, dest_type, dest))
                else:
                    req.args[Key.OUTGOING_LINKS] = 'deleted link %s(#%s)->%s(#%s)' % \
                                                    (src_type, src, dest_type, dest)
                    req.args['comment'] = 'Deleted link to %s(#%s)' % (dest_type, dest)
                    update_ticket = True
            else:
                raise TracError("ERROR: Unknown Command %s!" % cmd)
            
            #set the link into the request and let TicketWrapper update the custom field
            if update_ticket:
                req.args['id'] = src
                req.args['summary'] = sle[Key.SUMMARY]
                req.args['ts'] = sle.time_changed
                req.args['action'] = 'leave'
            
            # Redirect to original /ticket url to avoid any change in existing view
            req.redirect(url or req.base_url)

