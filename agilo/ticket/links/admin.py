# -*- coding: utf-8 -*-
#   Copyright 2008 Agile42 GmbH, Berlin (Germany)
#   Copyright 2007 Andrea Tomasini <andrea.tomasini__at__agile42.com>
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
#    Authors: 
#           Jonas von Poser (jonas.vonposer__at__agile42.com)

from trac.core import TracError
from trac.util.translation import _

from agilo.api.admin import AgiloAdminPanel
from agilo.ticket.api import AgiloTicketSystem
from agilo.ticket.links import LinkOption
from agilo.ticket.links.model import LinksConfiguration
from agilo.utils.config import AgiloConfig


class LinksAdminPanel(AgiloAdminPanel):
    """Administration panel for links.
    Needs to get imported in agilo/admin/__init__.py in order to appear
    on the web interface."""
    
    _type = 'links'
    _label = ('Links', _('Links'))

    def __init__(self):
        self.config = AgiloConfig(self.env)
        self.links = self.config.get_section(AgiloConfig.AGILO_LINKS)
        self.allowed_links = self._get_allowed_links()
    
    def _get_allowed_links(self):
        """Returns the dictionary containing the allowed links pairs"""
        links_configuration = LinksConfiguration(self.env)
        return dict([(l, list(links_configuration.extract_types(l))) for l in self.links.get_list(LinkOption.ALLOW)])

    def _get_delete_pairs(self):
        """Returns the dictionary containing the cascade delete pairs"""
        links_configuration = LinksConfiguration(self.env)
        return dict([(l, list(links_configuration.extract_types(l))) for l in self.links.get_list(LinkOption.DELETE)])

    def detail_view(self, req, cat, page, link):
        links_configuration = LinksConfiguration(self.env)
        (source, target) = links_configuration.extract_types(link)
        copy_fields = [f.strip() for f in self.links.get('%s.%s.%s' % \
                                                         (source, target, LinkOption.COPY), 
                                                         default='').split(',')]
        show_fields = [f.strip() for f in self.links.get('%s.%s.%s' % \
                                                         (source, target, LinkOption.SHOW), 
                                                         default='').split(',')]
        ticket_system = AgiloTicketSystem(self.env)
        # dict of name->label for all core and custom fields
        labels = dict([(f['name'], f['label']) for f in ticket_system.get_ticket_fields()])
        cascade_delete = source+'-'+target in self._get_delete_pairs()
        data = {
            'view': 'detail',
            'link': link,
            'source' : source,
            'target' : target,
            'source_fields' : self.config.TYPES[source],
            'target_fields' : self.config.TYPES[target],
            'labels' : labels,
            'copy_fields' : copy_fields,
            'show_fields' : show_fields,
            'cascade_delete': cascade_delete
        }
        return 'agilo_admin_links.html', data
        
    def detail_save_view(self, req, cat, page, link):
        links_configuration = LinksConfiguration(self.env)
        (source, target) = links_configuration.extract_types(link)
        fields = req.args.get('copy_fields', [])
        if type(fields) != type([]):
            fields = [fields]
        # set copy options for this link
        self.links.change_option('%s.%s.%s' % (source, target, LinkOption.COPY),
                                 ', '.join(fields))
        
        fields = req.args.get('show_fields', [])
        if type(fields) != type([]):
            fields = [fields]
        # set show options for this link
        self.links.change_option('%s.%s.%s' % (source, target, LinkOption.SHOW),
                                 ', '.join(fields))
        
        cascade_delete = req.args.get('cascade_delete')
        delete_pairs = self._get_delete_pairs()
        if cascade_delete and source+'-'+target not in delete_pairs:
            delete_pairs[source+'-'+target] = (source, target)
            self.links.change_option(LinkOption.DELETE, 
                                     ', '.join(delete_pairs.keys()))

        elif not cascade_delete and source+'-'+target in self._get_delete_pairs():
            del delete_pairs[source+'-'+target]
            self.links.change_option(LinkOption.DELETE, 
                                     ', '.join(delete_pairs.keys()))
            
        
        # saved it, redirect back to admin view
        self.links.save()
        req.redirect(req.href.admin(cat, page))
   
    def list_view(self, req, cat, page):
        data = {
            'view': 'list',
            'allowed_links': self._get_allowed_links(),
            'available_types' : self.config.get_available_types(strict=True),
        }
        return 'agilo_admin_links.html', data
        
    def list_save_view(self, req, cat, page):
        source = req.args.get('source')
        target = req.args.get('target')
        if req.args.get('add') and source and target:
            if (source, target) in self.allowed_links:
                # link already exists, redirect to it
                req.redirect(req.href.admin(cat, page, '%s-%s' % (source, target)))
            # Set, save because there is the redirect
            self.links.change_option(LinkOption.ALLOW, '%s, %s-%s' % \
                                     (self.links.get(LinkOption.ALLOW, default=''), 
                                      source, target), save=True)
            return req.redirect(req.href.admin(cat, page, '%s-%s' % (source, target)))

        # Remove components
        if req.args.get('remove'):
            sel = req.args.get('sel')
            if not sel:
                raise TracError(_('No link selected'))
            if not isinstance(sel, list):
                sel = [sel]

            # delete selection from allowed links
            for s in sel:
                del self.allowed_links[s]
                
            # write new value back to config, and save
            self.links.change_option(LinkOption.ALLOW, 
                                     ', '.join(self.allowed_links.keys()),
                                     save=True)
        return req.redirect(req.href.admin(cat, page))
