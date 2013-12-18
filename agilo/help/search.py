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
#   
#   Author: 
#       - Felix Schwarz <felix.schwarz_at_agile42.com>

import re

from pkg_resources import resource_string
from trac.core import Component, implements
from trac.search.api import ISearchSource, shorten_result
from trac.util.translation import _

from agilo.help.util import get_all_help_pages
from agilo.utils.days_time import now


class AgiloHelpSearcher(Component):
    
    implements(ISearchSource)
    
    # --------------------------------------------------------------------------
    # ISearchSource methods
    def get_search_filters(self, req):
        yield ('agilo-help', _('Agilo Help'))
    
    def _look_for_terms(self, contents, terms):
        contains_all_terms = True
        search_content = contents.lower()
        for term in terms:
            if term.lower() not in search_content:
                contains_all_terms = False
                break
        return contains_all_terms
    
    def _build_href(self, req, pkg, name):
        page_name = name[:-len('.txt')]
        web_path = pkg.replace('agilo.help.contents', '').replace('.', '/')
        web_components = []
        if web_path != '':
            web_components.append(web_path)
        web_components.append(page_name)
        href = req.href('agilo-help', *web_components)
        return href
    
    def _extract_title(self, wiki_markup):
        parsing_regex = re.compile(r'.*?^\s*=+\s+([^\n\r]+?)\s+=+\s*(.*?$.*)',
                                        re.MULTILINE|re.DOTALL)
        match = parsing_regex.match(wiki_markup)
        return match.group(1)
    
    def get_search_results(self, req, terms, filters):
        if 'agilo-help' not in filters:
            return []
        
        results = []
        for pkg, name in get_all_help_pages():
            contents = resource_string(pkg, name).decode('UTF-8')
            if self._look_for_terms(contents, terms):
                title = self._extract_title(contents)
                author = 'agile42'
                excerpt = shorten_result(contents, terms)
                
                href = self._build_href(req, pkg, name)
                result = [href, title, now(), author, excerpt]
                results.append(result)
        
        return results
    # --------------------------------------------------------------------------


