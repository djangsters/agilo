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
#        Jonas von Poser <jonas.vonposer__at__agile42.com>
#        Andrea Tomasini <andrea.tomasini__at__agile42.com>

from trac.core import TracError
from trac.util.translation import _
from trac.web.chrome import add_script, add_warning

from agilo.api.admin import AgiloAdminPanel
from agilo.scrum.backlog.controller import BacklogController
from agilo.utils import Key, ajax, BacklogType
from agilo.utils.config import AgiloConfig
from agilo.utils.sorting import By, Column, SortOrder


class BacklogAdminPanel(AgiloAdminPanel):
    """Administration panel for backlogs."""
    
    _type = 'backlogs'
    _label = ('Backlogs', _('Backlogs'))
    
    def _get_backlog_configuration(self, name):
        from agilo.scrum.backlog.backlog_config import BacklogConfigurationModelManager
        return BacklogConfigurationModelManager(self.env).get(name=name)

    def _create_backlog_configuration(self, name):
        from agilo.scrum.backlog.backlog_config import BacklogConfigurationModelManager
        return BacklogConfigurationModelManager(self.env).create(name=name)
        
    def _get_backlogs(self):
        select_cmd = BacklogController.ListBacklogsCommand(self.env)
        return BacklogController(self.env).process_command(select_cmd)
    
    def _parse_boolean_option(self, req, key, value, conf_fields):
        assert value in ['True', 'False']
        value = (value == 'True')
        # All properties with True or False starts with a 4 letter_ now
        prop = key[5:]
        if key.startswith('show_'):
            # It is a show field, so add show to the fields_config dictionary
            # Sorting out properties for show_ and edit_ the length of the
            # strings is the same
            if not conf_fields.has_key(prop):
                conf_fields[prop] = {}
            conf_fields[prop]['show'] = value
    
    
    def detail_save_view(self, req, cat, page, name):
        backlog_config = self._get_backlog_configuration(name)
        if not backlog_config:
            return req.redirect(req.href.admin(cat, page))

        # update values from request
        backlog_config.type = int(req.args.get('scope'))
        backlog_config.include_planned_items = bool(req.args.get('include_planned_items'))

        # don't save as unicode, cpickle/sqlite don't like it
        # FIXME: What if there are unicode characters in the ticket 
        # type? It may be a problem, but we need to use the Alias to
        # make the name nice, not the ticket type, or Pickle won't 
        # always work...
        backlog_config.ticket_types = [str(t) for t in \
                                       req.args.getlist('ticket_types')]

        if 'preview' in req.args:
            return self.detail_view(req, cat, page, name, backlog_config)
        
        # REFACT: BacklogConfig should be able to serialize itself
        conf_fields = {}
        
        for key, value in req.args.items():
            # loop over all POST values
            if value in ['True', 'False']:
                self._parse_boolean_option(req, key, value, conf_fields)
            elif key.startswith(Key.ALTERNATIVE + '_'):
                # These are the alternative fields to show, it is one per type
                prop = key[len(Key.ALTERNATIVE + '_'):]
                if value not in [None, '']:
                    if not conf_fields.has_key(prop):
                        conf_fields[prop] = {}
                    conf_fields[prop][Key.ALTERNATIVE] = value
            elif key.startswith(Key.ORDER + '_'):
                prop = key[len(Key.ORDER + '_'):]
                if isinstance(value, list):
                    # add warning and set the first value
                    value = value[0]
                    add_warning(req, _("Please make sure orders are unique, " \
                                       "there is more than one property with " \
                                       "order: %s" % value[0]))
                if value not in [None, ''] and value.isdigit():
                    if not conf_fields.has_key(prop):
                        conf_fields[prop] = {}
                    conf_fields[prop][Key.ORDER] = int(value)
        # Now sort the conf_fields according to the order first
        conf_sorted = sorted(conf_fields.iteritems(), 
                             cmp=By(Column(Key.ORDER), SortOrder.ASCENDING), 
                             key=lambda(t):t[1])
        columns = []
        for col, props in conf_sorted:
            if props.get(Key.SHOW):
                alt = props.get(Key.ALTERNATIVE)
                if alt is not None:
                    col += u'|%s' % alt
                columns.append(col)
        
        # Now save the changes to the config file and to the Database
        backlog_config.backlog_columns = columns
        backlog_config.save()
        
        if req.chrome[Key.WARNINGS]:
            return self.detail_view(req, cat, page, name, backlog_config)
        req.redirect(req.href.admin(cat, page))
    
    def _backlog_config_with_changed_ticket_types(self, req, cat, page, name, backlog_config=None):
        ticket_types = req.args.getlist(Key.TICKET_TYPES)
        if not backlog_config:
            backlog_config = self._get_backlog_configuration(name)
            if not backlog_config:
                return req.redirect(req.href.admin(cat, page))
        if ticket_types:
            backlog_config.ticket_types = ticket_types
        return backlog_config
    
    def detail_view(self, req, cat, page, name, backlog_config=None):
        backlog_config = self._backlog_config_with_changed_ticket_types(req, cat, page, name, backlog_config=backlog_config)
        
        # REFACT: Maybe we should use JSON here rather than xml?
        if ajax.is_ajax(req):
            # we got called by an Ajax request -> get available fields
            fields_for_selected_types = backlog_config.columns_as_fields(all_fields=False)
            items = [field[Key.NAME] for field in fields_for_selected_types]
            return 'ajax_response.xml', {'items': items}
        
        # TODO: Go for ticket configuration
        agilo_config = AgiloConfig(self.env)
        data = {
            'view': 'detail',
            'backlog': backlog_config,
            'backlog_types' : BacklogType.LABELS,
            't_types' : [(t_type, 
                          t_type in backlog_config.ticket_types,
                          agilo_config.ALIASES.get(t_type, t_type))
                         for t_type in agilo_config.TYPES.keys()],
            'fields' : backlog_config.columns_as_fields(all_fields=True),
        }
        add_script(req, 'agilo/js/backlog_admin.js')
        add_script(req, 'common/js/wikitoolbar.js')
        return 'agilo_admin_backlog.html', data
    
    def list_view(self, req, cat, page):
        data = {
            'view': 'list',
            'backlogs': self._get_backlogs(),
            'backlog_types' : BacklogType.LABELS,
        }
        return 'agilo_admin_backlog.html', data
    
    def list_save_view(self, req, cat, page):
        # TODO: better sanity checks for input, show error in form
        name = req.args.get('name')
            
        if req.args.get('add') and name:
            backlog_config = self._get_backlog_configuration(name)
            if backlog_config:
                #  backlog already exists, redirect to it
                return req.redirect(req.href.admin(cat, page, name))
            backlog_config = self._create_backlog_configuration(name)
            backlog_config.save()
            req.redirect(req.href.admin(cat, page, name))

        # Remove components
        if req.args.get('remove'):
            sel = req.args.get('sel')
            if not sel:
                raise TracError(_('No backlog selected'))
            if not isinstance(sel, list):
                sel = [sel]
            for name in sel:
                backlog_config = self._get_backlog_configuration(name)
                backlog_config.delete()
               
        return req.redirect(req.href.admin(cat, page))