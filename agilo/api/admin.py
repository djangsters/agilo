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

from trac.core import Component, implements, TracError
from trac.web.chrome import add_stylesheet
from trac.admin import IAdminPanelProvider
from trac.util.translation import _


class AgiloAdminPanel(Component):
    abstract = True
    
    implements(IAdminPanelProvider)
    # IAdminPanelProvider methods

    def get_admin_panels(self, req):
        if 'TRAC_ADMIN' in req.perm:
            yield ('agilo', 'Agilo', self._type, _(self._label[1]))

    def render_admin_panel(self, req, cat, page, path_info):
        req.perm.require('TRAC_ADMIN')
        # Send the default agilo_admin.css to the request
        add_stylesheet(req, 'agilo/stylesheet/agilo_admin.css')
        
        # Trap AssertionErrors and convert them to TracErrors
        try:
            if path_info:
                # detail view
                if req.method == 'POST':
                    if req.args.get('cancel'):
                        # pressed the cancel button -> redirect to admin page
                        req.redirect(req.href.admin(cat, page))

                    return self.detail_save_view(req, cat, page, path_info)
                return self.detail_view(req, cat, page, path_info)

            # list view
            if req.method == 'POST':
                return self.list_save_view(req, cat, page)
            return self.list_view(req, cat, page)

        except AssertionError, e:
            raise TracError(e)