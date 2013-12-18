# -*- encoding: utf-8 -*-
#   Copyright 2009 Agile42 GmbH, Berlin (Germany)
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
#   Author: Felix Schwarz <felix.schwarz_at_agile42.com>

from pkg_resources import resource_filename

from trac.core import Component, implements
from trac.web.chrome import ITemplateProvider

__all__ = ['FlotJSProvider']

class FlotJSProvider(Component):
    
    implements(ITemplateProvider)
    
    def get_htdocs_dirs(self):
        return [('agilo', resource_filename('agilo.charts', 'htdocs'))]
    
    def get_templates_dirs(self):
        return list()

