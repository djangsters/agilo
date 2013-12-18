# -*- coding: utf-8 -*-

from trac.tests.functional import tc
from agilo.test.functional import AgiloFunctionalTestCase


class TestHelpPageNamesAreCaseInsensitive(AgiloFunctionalTestCase):
    def runTest(self):
        "Tests that help pages names are handled case-insensitively."
        # All help pages are accessible as anonymous too
        self._tester.logout()
        
        def check_page(page_name):
            tc.go(self._tester.url + '/agilo-help/' + page_name)
            tc.code(200)
            tc.find("Agilo for trac user group")
        
        check_page('index')
        check_page('Index')
        check_page('INDEX')
        check_page('')


class TestCallIndexPage(AgiloFunctionalTestCase):
    def runTest(self):
        # All help pages are accessible as anonymous too
        self._tester.logout()
        tc.go(self._tester.url + '/agilo-help/')
        tc.code(200)
        tc.find('Agilo Documentation')


class TestNonExistentPagesAreCatched(AgiloFunctionalTestCase):
    def runTest(self):
        # All help pages are accessible as anonymous too
        self._tester.logout()
        tc.go(self._tester.url + '/agilo-help/does_not_exist')
        tc.code(404)


class TestHelpPagesCanBeOrganizedAsDirectories(AgiloFunctionalTestCase):
    def runTest(self):
        # All help pages are accessible as anonymous too
        self._tester.logout()
        tc.go(self._tester.url + '/agilo-help/admin/index')
        tc.code(200)
        tc.find('Agilo Administration Guide')



if __name__ == '__main__':
    from agilo.test.testfinder import run_all_tests
    run_all_tests(__file__)

