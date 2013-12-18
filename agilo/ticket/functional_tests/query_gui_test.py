# -*- coding: utf-8 -*-

from trac.tests.functional import tc

from agilo.test import Usernames
from agilo.test.functional import AgiloFunctionalTestCase


class TestQueryWithMultipleTypeParameters(AgiloFunctionalTestCase):
    """Test that a user build queries with multiple parameters of the same type
    (see bug #363)."""
    def runTest(self):
        self.tester.login_as(Usernames.product_owner)
        query_url = self.tester.url + "/query?type=!bug&type=!enhancement"
        tc.go(query_url)
        tc.code(200)


if __name__ == '__main__':
    from agilo.test.testfinder import run_all_tests
    run_all_tests(__file__)

