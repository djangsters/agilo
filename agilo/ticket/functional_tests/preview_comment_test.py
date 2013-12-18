# -*- encoding: utf-8 -*-
#   Copyright 2008 Agile42 GmbH, Berlin (Germany)
#   Copyright 2007 Andrea Tomasini <andrea.tomasini_at_agile42.com>
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
#   Author: 
#       - Felix Schwarz <felix.schwarz__at__agile42.com>

from trac.tests.functional import tc
from twill.errors import TwillAssertionError

from agilo.test import Usernames
from agilo.test.functional import AgiloFunctionalTestCase


class TestNewCommentWithPreview(AgiloFunctionalTestCase):
    
    def _go_to_comment_form(self, ticket_id):
        page_url = self._tester.url + '/ticket/%d' % ticket_id
        tc.go(page_url)
        tc.url(page_url)
        tc.find(' #%d' % ticket_id)
    
    def _submit_preview(self, ticket_id, comment):
        self._go_to_comment_form(ticket_id)
        tc.formvalue('propertyform', 'comment', comment)
        tc.submit('preview')
        tc.find("preview")
        tc.find(comment)
    
    def _assert_comment_not_saved(self, ticket_id, comment):
        self._go_to_comment_form(ticket_id)
        try:
            tc.find(comment)
        except TwillAssertionError:
            pass
        else:
            self.fail("Comment should not be saved")
            pass
    
    def runTest(self):
        self._tester.login_as(Usernames.admin)
        ticket_id = self._tester.create_new_agilo_task('foo', 'abc')
        comment = 'Another comment'
        self._submit_preview(ticket_id, comment)
        self._assert_comment_not_saved(ticket_id, comment)


if __name__ == '__main__':
    from agilo.test.testfinder import run_all_tests
    run_all_tests(__file__)

