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
#
# Incorporates BSD-licensed code from http://trac-hacks.org/wiki/CustomFieldAdminPlugin
# (c) 2005-2007 ::: www.CodeResort.com - BV Network AS (simon-code@bvnetwork.no)
# (c) 2007      ::: www.Optaros.com (.....)

import re

from trac.core import Component, TracError
from trac.util.text import to_unicode
from trac.util.translation import _
from trac.web.chrome import add_script

from agilo.api.admin import AgiloAdminPanel
from agilo.ticket.api import AgiloTicketSystem
from agilo.utils import Key
from agilo.utils.config import AgiloConfig


__all__ = ['CustomFieldAdminPanel', 'CustomFields', ]

class CustomFieldAdminPanel(AgiloAdminPanel):
    # CustomFieldAdminPanel methods
    _type = 'fields'
    _label = ('Fields', _('Fields'))

    def __init__(self):
        self.cfapi = CustomFields(self.env)

    def _customfield_from_req(self, req):
        cfdict = {Key.NAME: req.args.get(Key.NAME),
                  Key.LABEL: req.args.get(Key.LABEL),
                  Key.TYPE: req.args.get(Key.TYPE),
                  Key.VALUE: req.args.get(Key.VALUE),
                  Key.OPTIONS: [x.strip() for x in req.args.get(Key.OPTIONS).split("\n")],
                  Key.COLS: req.args.get(Key.COLS),
                  Key.ROWS: req.args.get(Key.ROWS),
                  Key.ORDER: req.args.get(Key.ORDER, 0)}
        return cfdict
    
    def detail_view(self, req, cat, page, field_name):
        add_script(req, 'customfieldadmin/js/CustomFieldAdminPage_actions.js')
        
        cfadmin = {} # Return values for template rendering
        
        # Detail view?
        exists = [True for cf in self.cfapi.get_custom_fields() if cf[Key.NAME] == field_name]
        if not exists:
            raise TracError("Custom field %s does not exist." % field_name)

        currentcf = self.cfapi.get_custom_fields(field_name)
        if currentcf.has_key(Key.OPTIONS):
            optional_line = ''
            if currentcf.get('optional', False):
                optional_line = "\n\n"
            currentcf[Key.OPTIONS] = optional_line + "\n".join(currentcf[Key.OPTIONS])
        cfadmin['customfield'] = currentcf
        cfadmin['display'] = 'detail'
        return ('agilo_admin_customfields.html', {'cfadmin': cfadmin})

    def detail_save_view(self, req, cat, page, customfield):
        cfdict = self._customfield_from_req(req) 
        self.cfapi.update_custom_field(cfdict)
        req.redirect(req.href.admin(cat, page))
    
    def list_save_view(self, req, cat, page):
        # Add Custom Field
        if req.args.get('add') and req.args.get(Key.NAME):
            cfdict = self._customfield_from_req(req)
            self.cfapi.update_custom_field(cfdict, create=True)
            return req.redirect(req.href.admin(cat, page))
                 
        # Remove Custom Field
        if req.args.get('remove') and req.args.get('sel'):
            sel = req.args.get('sel')
            sel = isinstance(sel, list) and sel or [sel]
            if not sel:
                raise TracError, 'No custom field selected'
            for name in sel:
                self.cfapi.delete_custom_field(name)
            return req.redirect(req.href.admin(cat, page))

        if req.args.get('apply'):
            # Change order
            order = dict([(key[6:], req.args.get(key)) for key
                          in req.args.keys()
                          if key.startswith('order_')])
            values = dict([(val, True) for val in order.values()])
            if len(order) != len(values):
                raise TracError, 'Order numbers must be unique.'
            cf = self.cfapi.get_custom_fields()
            for cur_cf in cf:
                cur_cf[Key.ORDER] = order[cur_cf[Key.NAME]]
                self.cfapi.update_custom_field(cur_cf)
                
        return req.redirect(req.href.admin(cat, page))
        
    def list_view(self, req, cat, page):
        """Generate the link view"""
        def _get_order_number(orders):
            """Returns the first available order number or returns a new one"""
            l_orders = len(orders)
            for i in range(l_orders):
                if i not in orders:
                    return i
            return l_orders
            
        cfadmin = dict() # Return values for template rendering
        cf_list = list()
        cf_order = list()
        for item in self.cfapi.get_custom_fields():
            item['href'] = req.href.admin(cat, page, item[Key.NAME])
            if item[Key.ORDER]:
                cf_order.append(item[Key.ORDER])
            cf_list.append(item)
        # Check the free order numbers
        for item in cf_list:
            if not item[Key.ORDER]:
                item[Key.ORDER] = _get_order_number(cf_order)
                cf_order.append(item[Key.ORDER])
        
        cf_list.sort(lambda x,y:cmp(x[Key.ORDER], y[Key.ORDER]))
        cfadmin['customfields'] = cf_list
        cfadmin['display'] = 'list'

        return ('agilo_admin_customfields.html', {'cfadmin': cfadmin})


class CustomFields(Component):
    """ These methods should be part of TicketSystem API/Data Model.
    Adds update_custom_field and delete_custom_field methods.
    (The get_custom_fields is already part of the API - just redirect here,
     and add option to only get one named field back.)
    """
    def __init__(self, *args, **kwargs):
        """Initialize the component and set a TracConfig"""
        self.ticket_custom = \
            AgiloConfig(self.env).get_section(AgiloConfig.TICKET_CUSTOM)
        
    def get_custom_fields(self, field_name=None):
        """
        Returns the custom fields from TicketSystem component.
        Use a field name to find a specific custom field only
        """
        if not field_name:    # return full list
            return AgiloTicketSystem(self.env).get_custom_fields()
        else:                  # only return specific item with cfname
            all = AgiloTicketSystem(self.env).get_custom_fields()
            for item in all:
                if item[Key.NAME] == field_name:
                    return item
            return None        # item not found
    
    def _store_all_options_for_custom_field(self, customfield):
        added_keys = list()
        changed = False
        for key in customfield:
            if key == Key.NAME:
                continue
            elif key == Key.TYPE:
                config_key = customfield[Key.NAME]
            else:
                config_key = '%s.%s' % (customfield[Key.NAME], key)
            value = customfield[key]
            if isinstance(value, list):
                value = '|'.join(value)
            if value not in ['', None]:
                changed = True
                self.ticket_custom.change_option(config_key, value, save=False)
                added_keys.append(key)
        if changed:
            self._remove_old_keys(customfield[Key.NAME], added_keys)
            self.ticket_custom.save()
    
    def _del_custom_field_value(self, customfield, prop=None):
        """Deletes a property from a custom field"""
        if not prop:
            self.ticket_custom.remove_option(customfield[Key.NAME])
        else:
            self.ticket_custom.remove_option('%s.%s' % (customfield[Key.NAME], prop))
    
    def _validate_input(self, customfield, create):
        """Checks the input values and raises a TracError if severe problems
        are detected."""
        # Name, Type are required
        if not (customfield.get(Key.NAME) and customfield.get(Key.TYPE)):
            raise TracError("Custom field needs at least a name and type.")
        
        # Use lowercase custom fieldnames only
        f_name = unicode(customfield[Key.NAME]).lower()
        # Only alphanumeric characters (and [-_]) allowed for custom fieldname
        if re.search('^[a-z0-9-_]+$', f_name) == None:
            raise TracError("Only alphanumeric characters allowed for custom field name (a-z or 0-9 or -_).")
        # If Create, check that field does not already exist
        if create and self.ticket_custom.get(f_name):
            raise TracError("Can not create as field already exists.")
        
        # Check that it is a valid field type
        f_type = customfield[Key.TYPE]
        if not f_type in ('text', 'checkbox', 'select', 'radio', 'textarea'):
            raise TracError("%s is not a valid field type" % f_type)
        
        if (Key.ORDER in customfield) and (not str(customfield.get(Key.ORDER)).isdigit()):
            raise TracError("%s is not a valid number for %s" % (customfield.get(Key.ORDER), Key.ORDER))
        
        customfield[Key.NAME] = f_name
    
    def update_custom_field(self, customfield, create=False):
        """
        Update or create a new custom field (if requested).
        customfield is a dictionary with the following possible keys:
            name = name of field (alphanumeric only)
            type = text|checkbox|select|radio|textarea
            label = label description
            value = default value for field content
            options = options for select and radio types (list, leave first empty for optional)
            cols = number of columns for text area
            rows = number of rows for text area
            order = specify sort order for field
        """
        
        self._validate_input(customfield, create)
        f_type = customfield[Key.TYPE]
        if f_type == 'textarea':
            def set_default_value(key, default):
                if (key not in customfield) or \
                        (not unicode(customfield[key]).isdigit()):
                    customfield[key] = unicode(default)
            # dwt: why is this called twice?
            set_default_value(Key.COLS, 60)
            set_default_value(Key.COLS, 5)
        
        if create:
            number_of_custom_fields = len(self.get_custom_fields())
            # We assume that the currently added custom field is not present in 
            # the return value of get_custom_fields and we start counting from 0
            customfield[Key.ORDER] = str(number_of_custom_fields)
        
        self._store_all_options_for_custom_field(customfield)
        AgiloTicketSystem(self.env).reset_ticket_fields()
        # TODO: Check that you can change the type from select to something different
        # and the options are gone afterwards
    
    
    def _set_custom_field_value(self, customfield, prop=None):
        """Sets a value in the custom fields for a given property key"""
        config_key = value = None
        if prop:
            value = customfield.get(prop)
            if isinstance(value, list):
                value = '|'.join(value)
            config_key = '%s.%s' % (customfield[Key.NAME], prop)
        else:
            # Used to set the type
            config_key = customfield[Key.NAME]
            value = customfield[Key.TYPE]
        self.ticket_custom.change_option(config_key, value)
    
    def _remove_old_keys(self, fieldname, added_keys):
        for key in (Key.VALUE, Key.OPTIONS, Key.COLS, Key.ROWS):
            if key not in added_keys:
                self.ticket_custom.remove_option('%s.%s' % (fieldname, key), 
                                                 save=False)
    
    def delete_custom_field(self, field_name):
        """Deletes a custom field"""
        if not self.ticket_custom.get(field_name):
            return # Nothing to do here - cannot find field
        # Need to redo the order of fields that are after the field to be deleted
        order_to_delete = self.ticket_custom.get_int('%s.%s' % (field_name, Key.ORDER))
        cfs = self.get_custom_fields()
        for field in cfs:
            if field[Key.ORDER] > order_to_delete:
                field[Key.ORDER] -= 1
                self._set_custom_field_value(field, Key.ORDER)
            elif field[Key.NAME] == field_name:
                # Remove any data for the custom field (covering all bases)
                self._del_custom_field_value(field)
        # Save settings
        self.ticket_custom.save()
        AgiloTicketSystem(self.env).reset_ticket_fields()
