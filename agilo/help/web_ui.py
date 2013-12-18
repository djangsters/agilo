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
#     - Felix Schwarz <felix.schwarz__at__agile42.com>
#     - Andrea Tomasini <andrea.tomasini__at__agile42.com>

import re

from pkg_resources import resource_exists, resource_filename, resource_string
from trac.core import implements, Component
from trac.web.chrome import prevnext_nav, add_link
from trac.mimeview.api import Context
from trac.resource import ResourceNotFound
from trac.util.translation import _
from trac.web.main import IRequestHandler
from trac.web.chrome import ITemplateProvider

# The help system for Agilo does not use Wiki pages directly but a separate 
# component which sucks the contents from a directory inside of our egg.
# 
# This has several advantages because help documents needs be updated quite 
# often to reflect changes in the software (and in the beginning, we need to 
# build our docs incrementally):
# - Therefore the user should not edit these pages because we have to overwrite
#   them anyway (updating only our content is hard to impossible). But wiki 
#   pages create the illusion that the user can edit them as he wants.
# - Changing the environment's wiki is not something to be taken lightly because
#   it is easy to delete user content. Therefore we would need a special upgrade
#   process. Using the ISetupParticipant for that would be inconvenient because
#   the system administrator has to issue additional commands for every update
#   and generally this whole process could not benefit from our db version 
#   number.
# - Wiki pages with help contents may clutter the search results.
# - Trac itself tries to get rid of help documents in the Wiki and use a special
#   component instead (NewHelp) which is planned for 0.12. With the  
#   AgiloHelpModule we basically do the same what is planned for trac and we can
#   adapt to the new trac API very easily (once it is completed).
#   Further references:
#   http://trac.edgewall.org/wiki/TracDev/Proposals/NewHelp
#   http://trac.edgewall.org/ticket/2656


class AgiloHelpModule(Component):
    
    implements(IRequestHandler, ITemplateProvider)
    
    def _set_prev_next(self, req):
        """Sets in the chrome links the navigation to previous and next page"""
        next = prev = None
        history = req.session.get('help-history', '').split(',')
        page_url = req.href(req.path_info)
        if page_url in history:
            # user visited the page already
            history_idx = history.index(page_url)
            if history_idx > 0:
                prev = history[history_idx - 1]
            if history_idx + 1 < len(history):
                next = history[history_idx + 1]
        else:
            if len(history) > 0:
                prev = history[-1]
            # add current page to help history
            if len(history) >= 10:
                history = history[1:]
            history.append(page_url)
            req.session['help-history'] = ','.join(history)
        # Now add links if present
        if prev:
            add_link(req, 'prev', prev)
        if next:
            add_link(req, 'next', next)
        # add index link
        add_link(req, 'up', req.href('agilo-help'))
        prevnext_nav(req, 'page', 'index')
    
    def match_request(self, req):
        match = re.match(r'^/agilo-help(?:/(.*))?$', req.path_info)
        if match != None:
            if match.group(1):
                req.args['page_name'] = match.group(1) or ''
            return True
        return False
    
    def _get_package_and_filename(self, page_name):
        page_name = page_name.lower()
        package_name = 'agilo.help.contents'
        if '/' not in page_name:
            module_path, filename = '', page_name
        else:
            module_path, filename = page_name.rsplit('/', 1)
            package_name += '.' + module_path.replace('/', '.')
        filename += '.txt'
        return (package_name, filename)
    
    def _resource_exists(self, package_name, filename):
        # resource_exists does not like non-existent packages, it will throw
        # an ImportError then. But we don't care, we just want to know if this
        # resource exists in this package.
        try:
            file_exists = resource_exists(package_name, filename)
        except ImportError:
            file_exists = False
        return file_exists
    
    def process_request(self, req):
        page_name = req.args.get('page_name', '')
        if page_name == '':
            page_name = 'index'
        
        # Add breadcrumb
        package_name, filename = self._get_package_and_filename(page_name)
        index_file = filename[:-len('.txt')] + '/index.txt'
        
        if not self._resource_exists(package_name, filename):
            # check if it is a folder, then match with index
            if self._resource_exists(package_name, index_file):
                filename = index_file
            else:
                error_msg = _('Page %(page_name)s not found', page_name=page_name)
                raise ResourceNotFound(error_msg)
        
        utf8_string = resource_string(package_name, filename)
        help_contents = utf8_string.decode('UTF-8')
        # add navigation bar
        self._set_prev_next(req)
        
        data = dict(context=Context.from_request(req), contents=help_contents,
                    page_name=page_name)
        return ('agilo_help.html', data, 'text/html')
    
    #=============================================================================
    # ITemplateProvider methods
    #=============================================================================
    def get_templates_dirs(self):
        return [resource_filename('agilo.help', 'templates')]
    
    def get_htdocs_dirs(self):
        return []


