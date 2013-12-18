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
#           Andrea Tomasini <andrea.tomasini__at__agile42.com>

from agilo.api.admin import AgiloAdminPanel
from agilo.utils.config import AgiloConfig
from agilo.utils import Key


class GeneralAdminPanel(AgiloAdminPanel):
    """General Options Panel for Agilo"""
    
    _type = 'general'
    _label = ('General', 'General')
    
    def list_view(self, req, cat, page):
        """Draw the list_view page"""
        config = AgiloConfig(self.env)
        return 'agilo_admin_general.html', {'use_days': config.use_days}
    
    def list_save_view(self, req, cat, page):
        """Stores general preferences for agilo"""
        use_days = (req.args.get('use_days') == 'True')
        # sets the days option
        config = AgiloConfig(self.env)
        # REFACT: Actually we could use config.use_days = use_days but then
        # we don't have any control when the config is actually written...
        config.change_option(Key.USE_DAYS, use_days, 'agilo-general', save=False)
        # Save only once
        self.config.save()
        req.redirect(req.href.admin(cat, page))

