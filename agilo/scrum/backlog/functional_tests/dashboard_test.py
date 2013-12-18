# -*- coding: utf-8 -*-

from trac.tests.functional import tc

from agilo.test import Usernames
from agilo.test.functional import AgiloFunctionalTestCase
from agilo.scrum import DASHBOARD_URL


class TestViewingTheDashboardRequiresPrivilege(AgiloFunctionalTestCase):
    """Test that the dashboard is not shown if the user does not have the
    DASHBOARD_VIEW privilege."""
    def runTest(self):
        self._tester.login_as(Usernames.product_owner)
        dashboard_url = self._tester.url + DASHBOARD_URL
        tc.go(dashboard_url)
        tc.code(200)
        
        self._tester.logout()
        tc.go(dashboard_url)
        tc.code(403)
        
        self._tester.go_to_front()
        tc.notfind('href="%s"' % DASHBOARD_URL)


if __name__ == '__main__':
    from agilo.test.testfinder import run_all_tests
    run_all_tests(__file__)

