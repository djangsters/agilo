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
#
#   Authors: 
#       - Martin Häcker <martin.haecker_at_agile42.com>

__all__ = ['use_jquery_13']

# For all the js heavy pages where we controll all the js anyway, we want
# an easy way to get the newest jquery as it has lots of bugfixes for ie,
# is way faster and has some really nice api additions.

from trac.web.chrome import add_script

def use_jquery_13(req):
    """Just call it with the req on any page that you want to use jquery 1.3 with
    and it will replace jquery 1.2 (from trac) with jquery 1.3 (from us)"""
    JQuery13Injector().inject(req)


class JQuery13Injector(object):
    """Trac only ships jQuery 1.2 (at least until 0.11.5). Therefore we remove
    trac's jQuery inject our own. However we can not just put the filename
    in the list of js files to include because some trac scripts will be
    loaded before and they need jQuery already loaded."""
    
    def find_index_for_script(self, scripts, filename):
        for i, script in enumerate(scripts):
            if script['href'].endswith(filename):
                return i
        raise ValueError('%s not found' % filename)
    
    def exchange_jquery_12_with_13_in_scripts(self, req):
        scripts = req.chrome['scripts']
        jquery_12_index = self.find_index_for_script(scripts, 'jquery.js')
        jquery_13_index = self.find_index_for_script(scripts, 'jquery-1.3.2.min.js')
        
        scripts[jquery_12_index] = scripts[jquery_13_index]
        del scripts[jquery_13_index]
        
    def inject(self, req):
        add_script(req, 'agilo/js/lib/jquery-1.3.2.min.js')
        self.exchange_jquery_12_with_13_in_scripts(req)
    
