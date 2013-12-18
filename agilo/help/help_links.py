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


from genshi.builder import tag
from trac.core import Component, implements
from trac.wiki import IWikiSyntaxProvider


class AgiloLinks(Component):
    implements(IWikiSyntaxProvider)
    
    # IWikiSyntaxProvider methods
    def get_wiki_syntax(self):
        # We don't define any additional syntax - this module is just about
        # having a new prefix for links.
        return []
    
    def get_link_resolvers(self):
        """Return an iterable over (namespace, formatter) tuples.
        
        Each formatter should be a function of the form
        fmt(formatter, ns, target, label), and should
        return some HTML fragment.
        The `label` is already HTML escaped, whereas the `target` is not.
        """
        def link_resolver(formatter, ns, target, label):
            fragment = None
            if '#' in target:
                target, fragment = target.split('#', 1)
            target = formatter.href('agilo-help', target)
            if fragment != None:
                target = '%s#%s' % (target, fragment)
            return tag.a(label, href=target)
        yield ('agilo-help', link_resolver)


