# -*- encoding: utf-8 -*-
#   Copyright 2009-2010 Agile42 GmbH, Berlin (Germany)
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

from StringIO import StringIO

from trac.tests.functional import tc
from trac.util.text import unicode_quote

from agilo.test import Usernames
from agilo.test.functional import AgiloFunctionalTestCase
from agilo.utils import Key
from agilo.csv_import.csv_file import CSVFile

from agilo.scrum import BACKLOG_URL

class TestBacklogCanBeExportedInCSV(AgiloFunctionalTestCase):
    
    def tearDown(self):
        self.tester.delete_sprints_and_milestones()
        self.super()
    
    def _find_requirement_info(self, csvfile, req_id):
        req_info = None
        for row in csvfile:
            if int(row.get(Key.ID)) == req_id:
                req_info = row
                break
        self.assert_not_none(req_info)
        return req_info
    
    def assert_csv_file_contains_ticket(self, csvfile, req_id, req_title, properties):
        req_info = self._find_requirement_info(csvfile, req_id)
        #self.assert_dict_contains({Key.BUSINESS_VALUE: '1200', Key.SUMMARY: req_title}, req_info)
        self.assert_equals(req_title, req_info.get(Key.SUMMARY))
        for key in properties:
            self.assert_equals(properties[key], req_info.get(key))

    def download_as_csv(self):
        url_template = '%(prefix)s/%(backlog)s'
        backlog_path = url_template % dict(prefix=BACKLOG_URL, backlog='Product Backlog')
        url = self.tester.url + unicode_quote(backlog_path) + '?format=csv'
        tc.go(url)
        tc.code(200)
        csv_export = tc.show()
        csvfile = CSVFile(StringIO(csv_export), None, 'UTF-8')
        return csvfile
    
    def runTest(self):
        self.tester.login_as(Usernames.admin)
        req_title = 'Requirement 1'
        req_properties = {Key.BUSINESS_VALUE: '1200'}
        story_title = 'Story 1'
        story_properties = {Key.STORY_POINTS: '13'}
        req_id = self.tester.create_new_agilo_requirement(req_title, **req_properties)
        story_id = self.tester.create_new_agilo_userstory(story_title, **story_properties)
        
        self.tester.go_to_product_backlog()
        csvfile = self.download_as_csv()
        self.assert_contains(Key.SUMMARY, csvfile.get_headings())
        self.assert_contains(Key.DESCRIPTION, csvfile.get_headings())
        self.assert_contains(Key.BUSINESS_VALUE, csvfile.get_headings())
        self.assert_csv_file_contains_ticket(csvfile, req_id, req_title, req_properties)
        self.assert_csv_file_contains_ticket(csvfile, story_id, story_title, story_properties)

