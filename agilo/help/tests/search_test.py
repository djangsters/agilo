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

from agilo.help.search import AgiloHelpSearcher
from agilo.test import AgiloTestCase


class TestHelpSearch(AgiloTestCase):
    """Tests for searching help contents"""
    
    def setUp(self):
        self.super()
        self.searcher = AgiloHelpSearcher(self.env)
        req = self.teh.mock_request()
        self.get_search_results = \
            lambda terms: self.searcher.get_search_results(req, terms, ['agilo-help'])
    
    def _find_result(self, results, page_name):
        page_name = 'agilo-help' + page_name.lower()
        for hit in results:
            link_target = str(hit[0]).lower()
            if link_target.endswith(page_name):
                return hit
        return None
    
    def _assert_hit_with_title(self, hit, expected_title):
        self.assert_not_none(hit)
        title = hit[1]
        self.assert_equals(expected_title, title)
    
    def test_search_with_simple_terms(self):
        results = self.get_search_results(['Agilo for trac'])
        hit = self._find_result(results, '/index')
        self._assert_hit_with_title(hit, 'Agilo Documentation')
    
    def test_find_text_in_subpages(self):
        results = self.get_search_results(['three Scrum Ceremonies'])
        hit = self._find_result(results, '/scrum/SprintPlanningMeeting')
        self._assert_hit_with_title(hit, 'Sprint Planning Meeting')
    
    def test_use_unicode_for_help_contents(self):
        results = self.get_search_results([u'Sprint Planning Meeting'])
        hit = self._find_result(results, '/scrum/SprintPlanningMeeting')
        self._assert_hit_with_title(hit, 'Sprint Planning Meeting')
    
    def test_find_is_case_insensitive(self):
        results = self.get_search_results(['SPRINT PLANNING MEETING'])
        hit = self._find_result(results, '/scrum/SprintPlanningMeeting')
        self._assert_hit_with_title(hit, 'Sprint Planning Meeting')



