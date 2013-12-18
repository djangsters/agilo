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
#   
#   Authors:
#       - Andrea Tomasini <andrea.tomasini__at__agile42.com>

import re
from base64 import urlsafe_b64decode, urlsafe_b64encode

from pkg_resources import resource_filename
from trac.core import Component, implements
from trac.util.compat import set
from trac.web.chrome import ITemplateProvider, add_script
from trac.web.api import IRequestFilter

from agilo.utils import Key, Action
from agilo.utils.ajax import is_ajax
from agilo.utils.command import CommandParser
from agilo.utils.compat import add_stylesheet
from agilo.utils.config import AgiloConfig, IAgiloConfigChangeListener
from agilo.utils.days_time import now
from agilo.utils.log import debug
from agilo.utils.version_check import VersionChecker

# Attribute to store performance time
START_TIME = 'agilo_start_time'


def calculate_rgb(colorstring, diff=20):
    """
    Utility that returns a tuple of RGB color starting from the current,
    incremented of the supplied diff parameter. If the diff parameter is
    negative the color returned will be darker, otherwise lighter.
    """
    colorstring = colorstring.strip()
    if colorstring[0] == '#': colorstring = colorstring[1:]
    if len(colorstring) != 6:
        raise ValueError, "input #%s is not in #RRGGBB format" % colorstring
    r, g, b = colorstring[:2], colorstring[2:4], colorstring[4:]
    c_rgb = [int(n, 16) for n in (r, g, b)]
    for i in range(3):
        c_rgb[i] = abs(int(c_rgb[i]) + diff)
        if c_rgb[i] > 255: c_rgb[i] -= 255
    return '#%02x%02x%02x' % (c_rgb[0], c_rgb[1], c_rgb[2])

def url_encode(a_string):
    """Return an URL-safe base64 encoding of a string."""
    if a_string:
        if isinstance(a_string, unicode):
            a_string = a_string.encode('utf8')
        return urlsafe_b64encode(a_string).strip('=')

def url_decode(an_encoded_string):
    """Restore a string from its base64 encoding that may be url-safe."""
    if an_encoded_string:
        if isinstance(an_encoded_string, unicode):
            an_encoded_string = an_encoded_string.encode('utf8')
        return urlsafe_b64decode(an_encoded_string + \
                                 '=' * (4 - len(an_encoded_string) % 4))


class CoreTemplateProvider(Component):
    implements(ITemplateProvider, IRequestFilter, IAgiloConfigChangeListener)
    
    # Condition Regular expression matching
    PROP = re.compile(r'(p)(\[)([\w\.]+|[0-9]+)(\])')
    
    # List with Type -> Alias conversion paths
    # ANdreaT: I want to write something more expressive and intuitive
    # than this mess. Something more like:
    #   ticket:Key.TYPE
    #   fileds@options(item[Key.NAME]==Key.TYPE)
    #   allowed_links:Key.TYPE
    #   available_types
    #   source
    #   target
    #   changes@fileds(item.has_key(Key.FIELDS)):Key.TYPE:'new'
    # Where:
    # @, :, (), |, & are predicates:
    #   @  => in the list
    #   () => if condition is verified
    #   :  => accessing by key, with '*' iterate on all value of a dictionary
    #   |  => or
    #   &  => and
    ALIAS_KEYS = [
        #"'ticket':Key.TYPE",
        "'fields'@'options'(isinstance(item, dict) and item[Key.NAME]==Key.TYPE)",
        #"'type_selection':'options'",
        "'changes'@'fields'(isinstance(item, dict) and item.has_key(Key.FIELDS)):Key.TYPE:'new'|'old'",
        "'available_types'",
        "'row_groups',0,1@'cell_groups',0@'value'(isinstance(item, dict) and item['header']['title']=='Type')",
        "'allowed_links':'*'",
        "'source'",
        "'ticket_types'@'type'",
        "'target'", # String get evaluated, because there may be variable and indexes
    ]
    # List with Alias -> Type values
    TYPE_KEYS = [Key.TYPE, 'field_type', 'source', 'target', 'ticket_types']
    
    def __init__(self, *args, **kwargs):
        """Initialize the template provider for Agilo"""
        super(CoreTemplateProvider, self).__init__(*args, **kwargs)
        self._alias_to_type = {}
        self.config_reloaded()
        self.env.systeminfo.append(('Agilo', VersionChecker().agilo_version()))
    
    def config_reloaded(self):
        """Recreate mapping dictionaries when needed"""
        config = AgiloConfig(self.env)
        if config.ALIASES is not None:
            self._alias_to_type = dict(zip(config.ALIASES.values(), 
                                           config.ALIASES.keys()))
        self.cp = CommandParser(self.env, config.ALIASES, self._alias_to_type)
    
    #=============================================================================
    # IRequestFilter methods
    #=============================================================================            
    
    def pre_process_request(self, req, handler):
        """
        Modifies the data of an HTTP request and substitutes type aliases
        with ticket type names.
        Always returns the request handler unchanged.
        """
        # Performance measurement
        setattr(req, START_TIME, now())
        
        #substitute aliases with ticket types in request arguments
        for typedef in self.TYPE_KEYS:
            if req.args.has_key(typedef):
                typedef_obj = req.args.get(typedef)
                if isinstance(typedef_obj, list):
                    req.args[typedef] = list() # We need a new list
                    for td in typedef_obj:
                        if self._alias_to_type.has_key(td):
                            req.args[typedef].append(self._alias_to_type[td])
                        else:
                            req.args[typedef].append(td)
                elif self._alias_to_type.has_key(req.args[typedef]):
                    # print "!!! Replacing %s with %s" % (req.args[typedef], 
                    #                                     self._alias_to_type[req.args[typedef]])
                    req.args[typedef] = self._alias_to_type[req.args[typedef]]
        return handler
    
    def post_process_request(self, req, template, data, content_type):
        """
        Modify the data of a request and substitutes ticket type names
        with alias names.
        Always returns the request template and content_type unchanged.
        """
        if data is None:
            data = dict()
        self._substitute_ticket_types_with_aliases_in_request_arguments(req)
        self._substitute_ticket_types_with_aliases_in_genshi_data(data)
        config = AgiloConfig(self.env)
        data['agilo_ticket_types'] = config.ALIASES.items()
        data['create_perm'] = self.create_permissions(req)
        data['agilo_version'] = VersionChecker().agilo_version()
        self._inject_agilo_ui_for_this_request(req, data)
        self._inject_processing_time(req, data)
        
        return template, data, content_type
    
    #=============================================================================
    # ITemplateProvider methods
    #=============================================================================
    def get_templates_dirs(self):
        return [resource_filename('agilo', 'templates')]
    
    def get_htdocs_dirs(self):
        return [('agilo', resource_filename('agilo', 'htdocs'))]
    
    #=============================================================================
    # just private instance methods
    #=============================================================================
    
    def _inject_agilo_ui_for_this_request(self, req, data):
        # The idea is that all things here are purely for display purposes so 
        # we don't have to bother for ajax requests. This saves us ~0.2 seconds
        # for every request because loading a backlog (even without the real 
        # tickets does some db queries).
        if is_ajax(req):
            return
        add_stylesheet(req, 'agilo/stylesheet/agilo.css')
        
        config = AgiloConfig(self.env)
        self._remove_trac_stylesheet_for_this_request(req)
        # avoid circular imports
        from agilo.scrum.backlog.web_ui import BacklogModule
        # adds to data the info needed to visualize the Backlog list
        BacklogModule(self.env).send_backlog_list_data(req, data)
        add_script(req, 'agilo/js/sidebar.js')
        add_script(req, 'agilo/js/cookies.js')
        add_script(req, 'agilo/js/settings.js')
        add_script(req, 'agilo/js/collapse.js')
        add_script(req, 'agilo/js/ie-patches.js')
    
    def _inject_processing_time(self, req, data):
        if hasattr(req, START_TIME):
            duration = now() - getattr(req, START_TIME)
            duration_string = '%s.%s' % (duration.seconds, duration.microseconds)
            data['processing_time'] = duration_string
    
    def _substitute_ticket_types_with_aliases_in_request_arguments(self, req):
        if req.args.has_key(Key.TYPE):
            req_value = req.args[Key.TYPE]
            config = AgiloConfig(self.env)
            if isinstance(req_value, list):
                req.args[Key.TYPE] = list()
                for typedef in req_value:
                    prefix = ''
                    if typedef != None and typedef.startswith('!'):
                        prefix = typedef[0]
                        typedef = typedef[1:]
                    if config.ALIASES.has_key(typedef):
                        alias = config.ALIASES[typedef]
                        req.args[Key.TYPE].append(prefix + alias)
                    else:
                        req.args[Key.TYPE].append(typedef)
            elif config.ALIASES.has_key(req_value):
                req.args[Key.TYPE] = config.ALIASES[req_value]
    
    def _substitute_ticket_types_with_aliases_in_genshi_data(self, data, aliases=None):
        if aliases is None:
            aliases = self.ALIAS_KEYS
        if data is not None and aliases is not None:
            for cmd in aliases:
                self.cp.replace(data, cmd)
    
    def _remove_trac_stylesheet_for_this_request(self, req):
        linkset = list(req.chrome.get('linkset'))
        links = req.chrome.get('links')
        if linkset is not None:
            for link in linkset:
                # We must only remove the 'main' trac.css. Syntax
                # highlighting/ pygments come with another css named 
                # 'pygments/trac.css' so we must be careful only to remove 
                # the right trac.css.
                if link.startswith('stylesheet:') and link.find('/css/trac.css') != -1:
                    linkset.remove(link)
                    break
        # remove the link
        if links is not None and links.get('stylesheet', None) is not None:
            for link in links['stylesheet']:
                if link.has_key('href') and link['href'].find('trac.css') != -1:
                    links['stylesheet'].remove(link)
                    break
        req.chrome['linkset'] = set(linkset)
    
    def get_permission_name_to_create(self, trac_type_name):
        permission_name = 'CREATE_%s' % trac_type_name.upper()
        if hasattr(Action, permission_name):
            permission_name = getattr(Action, permission_name)
        return permission_name
    
    def create_permissions(self, req):
        """
        Returns a list of the permissions to create new ticket types for the
        given request object
        """
        create_perms = list()
        # see what ticket types the user has create permissions for
        for t_type, alias in AgiloConfig(self.env).ALIASES.items():
            permission_name = self.get_permission_name_to_create(t_type)
            debug(self, "Type: %s, Alias: %s Permission: %s" % \
                  (t_type, alias, permission_name))
            if permission_name in req.perm:
                create_perms.append(t_type)
        debug(self, "%s has create permission for types: %s" % \
                    (req.authname, create_perms))
        return create_perms
