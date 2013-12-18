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

from trac.core import Interface

__all__ = ['IBacklogToggleViewProvider']

class IBacklogToggleViewProvider(Interface):
    
    def register_backlog_for_toggling(self, configuration_view):
        """This is called by the BacklogToggleConfigurationJSONView to 
        get all backlogs that want to be rendered"""
    
