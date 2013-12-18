# -*- coding: utf-8 -*-

from trac.tests.functional import tc

from agilo.test import Usernames
from agilo.test.functional import AgiloFunctionalTestCase
from agilo.csv_import.functional_tests.import_test import GOOD_CSV_DATA


class TestUpdatePreviewFromCSV(AgiloFunctionalTestCase):
    def runTest(self):
        self._tester.login_as(Usernames.product_owner)
        ticket_info = self._tester.perform_import(GOOD_CSV_DATA)
        csv_delete_data = self._tester.build_csv_for_ticket_deletion_from(ticket_info)
        
        encoding = self._tester.upload_csv_for_update_import(csv_delete_data)
        tc.find('<h1>Update Preview</h1>')
        tc.find('File contents read with encoding <b>%s</b>.' % encoding)


def _change_summaries_and_get_ticket_ids(ticket_info, first_summary=None, second_summary=None):
        first_hit = list(ticket_info[0])
        first_ticket_id = first_hit[0]
        if first_summary != None:
            first_hit[1] = first_summary
        ticket_info[0] = first_hit
        
        second_hit = list(ticket_info[1])
        second_ticket_id = second_hit[0]
        if second_summary != None:
            second_hit[1] = second_summary
        ticket_info[1] = second_hit
        return (first_ticket_id, second_ticket_id)


class TestPerformUpdateFromCSV(AgiloFunctionalTestCase):
    def runTest(self):
        self._tester.login_as(Usernames.product_owner)
        ticket_info = self._tester.perform_import(GOOD_CSV_DATA)
        
        ticket_ids = _change_summaries_and_get_ticket_ids(ticket_info, "new foo", "new bar")
        changed_tickets = self._tester.perform_ticket_update_through_csv_upload(ticket_info)
        self.assertEquals(2, len(changed_tickets))
        self._tester.go_to_view_ticket_page(ticket_ids[0])
        tc.find("new foo")
        
        self._tester.go_to_view_ticket_page(ticket_ids[1])
        tc.find("new bar")


class TestPerformUpdateFromCSVNotAuthorized(AgiloFunctionalTestCase):
    def runTest(self):
        self._tester.login_as(Usernames.product_owner)
        ticket_info = self._tester.perform_import(GOOD_CSV_DATA)
        self._tester.login_as(Usernames.team_member)
        changed_tickets = self._tester.perform_ticket_update_through_csv_upload(ticket_info)
        self.assertEqual(0, len(changed_tickets))


if __name__ == '__main__':
    from agilo.test.testfinder import run_all_tests
    run_all_tests(__file__)

