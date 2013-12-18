# -*- coding: utf-8 -*-
#   Copyright 2008-2010 Agile42 GmbH, Berlin (Germany)
#   Copyright 2007 Andrea Tomasini <andrea.tomasini__at__agile42.com>
#   Copyright 2011 Agilo Software GmbH All rights reserved
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, 
#   software distributed under the License is distributed on an 
#   "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, 
#   either express or implied. See the License for the specific 
#   language governing permissions and limitations under the License.
#   
#    Authors: 
#         Jonas von Poser (jonas.vonposer__at__agile42.com)

from trac.core import TracError
from trac.util.translation import _

from agilo.api.admin import AgiloAdminPanel
from agilo.ticket.api import AgiloTicketSystem
from agilo.ticket.links import LinkOption
from agilo.ticket.links.configuration_parser import \
    parse_calculated_field
from agilo.utils import MANDATORY_FIELDS, Key
from agilo.utils.config import AgiloConfig, normalize_ticket_type
from agilo.utils.log import warning


__all__ = ['TypesAdminPanel']


class TypesAdminPanel(AgiloAdminPanel):
    """
    Administration panel for different ticket types and their fields.
    Needs to get imported in agilo/admin/__init__.py in order to appear
    on the web interface.
    """
    
    _type = 'types'
    _label = ('Types', _('Types'))

    def __init__(self):
        self.agilo_config = AgiloConfig(self.env)

    def _get_field_labels(self):
        """Returns a dictionary of fields and their labels."""
        labels = {}
        for f_name, label in self.agilo_config.LABELS.items():
            if f_name not in MANDATORY_FIELDS:
                labels[f_name] = label
        return labels

    def _get_fields(self, type_name=None):
        """
        If type_name is not set, return a dictionary of ticket types 
        and the corresponding fields as a list. If a type_name gets 
        passed, return a list of fields corresponding to this ticket 
        type.
        """
        fields = self.agilo_config.get_available_types(with_fields=True)
        if type_name:
            fields = fields.get(type_name)
        return fields
    
    def detail_save_view(self, req, cat, page, ticket_type):
        """Save the detail panel view"""
        # The types will be stored in lowercase and the space is not a
        # valid character for the config file key
        ticket_type = normalize_ticket_type(ticket_type)
        
        alias = req.args.get(Key.ALIAS)
        if alias:
            self.agilo_config.change_option('%s.%s' % (ticket_type, Key.ALIAS), 
                                            alias, 
                                            section=AgiloConfig.AGILO_TYPES,
                                            save=False)
        # save fields as string or comma-separated list of values
        # FIXME: (AT) after going crazy, it came out that some types are not
        # saved because there is no specific field assigned and the config 
        # won't store the property in the trac.ini. So the agilo type will also
        # not be loaded, even if the alias would be set.
        fields = req.args.get(Key.FIELDS, '') 
        # We have to save strings not lists
        if isinstance(fields, list):
            fields = ', '.join(fields)
        self.agilo_config.change_option(ticket_type, 
                                        fields,
                                        section=AgiloConfig.AGILO_TYPES,
                                        save=False)
        calc = []
        for res, func in zip(req.args.getlist('result'), 
                             req.args.getlist('function')):
            if res and func:
                configstring = u'%s=%s' % (res.strip(), func.strip())
                parsed = parse_calculated_field(configstring)
                if parsed == None:
                    msg = u"Wrong format for calculated property '%s'"
                    raise TracError(_(msg) % res)
                calc.append(configstring)
        calc = ','.join(calc)
        if calc:
            self.agilo_config.change_option('%s.%s' % (ticket_type, 
                                                       LinkOption.CALCULATE), 
                                            calc,
                                            section=AgiloConfig.AGILO_LINKS,
                                            save=False)
        self.agilo_config.save()
        
        # on 0.12 we need to reset the ticket fields explicitely as the synchronization 
        # is not done with the trac.ini anymore
        if AgiloTicketSystem(self.env).is_trac_012():
            AgiloTicketSystem(self.env).reset_ticket_fields()
        return req.redirect(req.href.admin(cat, page))
    
    def detail_view(self, req, cat, page, ticket_type):
        # All keys are saved lower-cased, but this is not done 
        # automatically for retrieval
        calc_prop = self.agilo_config.get_list('%s.%s' % (ticket_type, 
                                                          LinkOption.CALCULATE),
                                               section=AgiloConfig.AGILO_LINKS)
        calculated_properties = []
        if len(calc_prop) > 0:
            for definition in calc_prop:
                parts = definition.split('=', 1)
                if len(parts) == 2:
                    property_name, formula = parts
                    calculated_properties.append((property_name.strip(), 
                                                  formula.strip()))
                else:
                    message = u"Ignoring broken definition for " \
                              "calculated property: %s" % definition
                    warning(self, message)
        data = {
            'calculate' : calculated_properties,
            'view': 'detail',
            'type': ticket_type,
            'alias' : self.agilo_config.ALIASES.get(ticket_type, ''),
            'type_fields' : self._get_fields(ticket_type),
            'labels' : self._get_field_labels(),
        }
        return 'agilo_admin_types.html', data
    
    def list_view(self, req, cat, page):
        data = {
            'view': 'list',
            'fields': self._get_fields(),
            'aliases' : self.agilo_config.ALIASES,
            'labels' : self._get_field_labels(),
        }
        return 'agilo_admin_types.html', data
    