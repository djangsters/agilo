# -*- coding: utf-8 -*-

from twill.errors import TwillAssertionError
from trac.tests.functional import tc

from agilo.test import Usernames
from agilo.test.functional import AgiloFunctionalTestCase


def login_as(trac_tester, username):
    trac_tester.go_to_front()
    try:
        trac_tester.logout()
    except TwillAssertionError:
        pass
    trac_tester.login(username)

class TestCanStillCreateTicketsInAPlainTracEnvironment(AgiloFunctionalTestCase):
    
    def setUp(self, env_key='agilo_multi'):
        super(TestCanStillCreateTicketsInAPlainTracEnvironment, self).setUp(env_key=env_key)
    
    def runTest(self):
        self.tester.login_as(Usernames.product_owner)
        self.tester.create_new_agilo_requirement('New Task')
        
        trac_tester = self.testenv._trac_functional_test_environment.tester
        login_as(trac_tester, Usernames.team_member)
        ticket_id = trac_tester.create_ticket()
        trac_tester.go_to_ticket(ticket_id)
        tc.code(200)


class TestCanStillAccessCustomQueriesInAPlainTracEnvironment(AgiloFunctionalTestCase):
    
    def setUp(self, env_key='agilo_multi'):
        super(TestCanStillAccessCustomQueriesInAPlainTracEnvironment, self).setUp(env_key=env_key)
    
    def runTest(self):
        trac_tester = self.testenv._trac_functional_test_environment.tester
        login_as(trac_tester, Usernames.team_member)
        trac_tester.go_to_query()


if __name__ == '__main__':
    from agilo.test.testfinder import run_all_tests
    run_all_tests(__file__)

