# -*- encoding: utf-8 -*-
#   Copyright 2009 Agile42 GmbH, Berlin (Germany)
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
#       - Martin Häcker <martin.haecker__at__agile42.com>

from trac.core import Component, ExtensionPoint
from trac.web.chrome import add_script

from agilo.api.view import JSONView

from agilo.scrum.backlog.backlog_toggle_interface import IBacklogToggleViewProvider


__all__ = ['BacklogToggleViewInjector', 'BacklogToggleConfigurationJSONView']

# TODO: create a json view here that the switcher can ask which views it should show
# Then do all the processing / filtering on the server side (also don't call the 
# licenseing thing directly anyomre)

class BacklogToggleViewInjector(Component):
    
    def inject_toggle_view(self, req):
        add_script(req, 'agilo/js/toggleView.js')
    

class BacklogToggleConfigurationJSONView(JSONView):
    
    url = '/json/config/backlog/alternative_views'
    url_regex = ''
    
    views = ExtensionPoint(IBacklogToggleViewProvider)
    
    def reset_known_backlogs(self):
        self.ensure_known_backlog_identifiers()
        # Remove all elements from the array, sneaky I know
        del self.known_backlog_identifiers()[:]
    
    def ensure_known_backlog_identifiers(self):
        if not hasattr(self, '_known_backlog_identifiers'):
            self._known_backlog_identifiers = []
    
    def known_backlog_identifiers(self):
        self.ensure_known_backlog_identifiers()
        return self._known_backlog_identifiers
    
    def register_backlog_with_identifier(self, an_identifier):
        self.ensure_known_backlog_identifiers()
        if an_identifier in self.known_backlog_identifiers():
            return
        
        self.known_backlog_identifiers().append(an_identifier)
    
    def register_new_backlog(self):
        self.register_backlog_with_identifier('new_backlog')
    
    def register_whiteboard(self):
        self.register_backlog_with_identifier('whiteboard')
    
    def discover_backlogs(self):
        for view in self.views:
            view.register_backlog_for_toggling(self)
        return self.known_backlog_identifiers()
    
    def do_get(self, req, data):
        return self.discover_backlogs()
    
