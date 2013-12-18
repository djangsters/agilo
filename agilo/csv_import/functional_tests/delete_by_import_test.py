# -*- coding: utf-8 -*-

from trac.tests.functional import tc

from agilo.test import Usernames
from agilo.test.functional import AgiloFunctionalTestCase
from import_test import GOOD_CSV_DATA

class TestDeletePreviewFromCSV(AgiloFunctionalTestCase):
    def runTest(self):
        self._tester.login_as(Usernames.product_owner)
        # create two tickets
        ticket_info = self._tester.perform_import(GOOD_CSV_DATA)
        csv_delete_data = self._tester.build_csv_for_ticket_deletion_from(ticket_info)
        
        encoding = self._tester.upload_csv_for_delete_import(csv_delete_data)
        tc.find('<h1>Delete Preview</h1>')
        tc.find('File contents read with encoding <b>%s</b>.' % encoding)
        tc.notfind('businessvalue')
        tc.notfind('keywords')



class TestPerformDeleteFromCSV(AgiloFunctionalTestCase):
    def runTest(self):
        self._tester.login_as(Usernames.product_owner)
        ticket_info = self._tester.perform_import(GOOD_CSV_DATA)
        changed_tickets = self._tester.perform_ticket_deletion_through_csv_upload(ticket_info)
        self.assertEqual(2, len(changed_tickets))
        for hit in changed_tickets:
            ticket_id = hit[0]
            self._tester.go_to_view_ticket_page(ticket_id, should_fail=True)
            tc.code(404)


def _change_first_hit_and_get_ticket_ids(ticket_info, new_first_ticket_id=None, 
                                         new_first_summary=None):
        first_hit = list(ticket_info[0])
        first_ticket_id = first_hit[0]
        if new_first_ticket_id != None:
            first_hit[0] = new_first_ticket_id
        if new_first_summary != None:
            first_hit[1] = new_first_summary
        ticket_info[0] = first_hit
        
        second_hit = list(ticket_info[1])
        second_ticket_id = second_hit[0]
        second_hit[1] = second_hit[1].decode("UTF-8")
        ticket_info[1] = second_hit
        return (first_ticket_id, second_ticket_id)


class TestPerformDeleteFromCSVSkipMissingTickets(AgiloFunctionalTestCase):
    def runTest(self):
        self._tester.login_as(Usernames.product_owner)
        ticket_info = self._tester.perform_import(GOOD_CSV_DATA)
        
        first_ticket_id, second_ticket_id = \
            _change_first_hit_and_get_ticket_ids(ticket_info, new_first_ticket_id=4711)
        
        changed_tickets = self._tester.perform_ticket_deletion_through_csv_upload(ticket_info)
        self.assertEqual(1, len(changed_tickets))
        tc.find("Ticket 4711 does not exist")
        
        self._tester.go_to_view_ticket_page(first_ticket_id, should_fail=False)
        self._tester.go_to_view_ticket_page(second_ticket_id, should_fail=True)
        tc.code(404)


class TestPerformDeleteFromCSVNonNumericTicketId(AgiloFunctionalTestCase):
    def runTest(self):
        self._tester.login_as(Usernames.product_owner)
        ticket_info = self._tester.perform_import(GOOD_CSV_DATA)
        
        first_ticket_id, second_ticket_id = \
            _change_first_hit_and_get_ticket_ids(ticket_info, new_first_ticket_id="foo")
        
        changed_tickets = self._tester.perform_ticket_deletion_through_csv_upload(ticket_info)
        self.assertEqual(1, len(changed_tickets))
        tc.find("Non-numeric ticket ID")
        
        self._tester.go_to_view_ticket_page(first_ticket_id, should_fail=False)
        self._tester.go_to_view_ticket_page(second_ticket_id, should_fail=True)
        tc.code(404)


class TestPerformDeleteFromCSVDifferentSummary(AgiloFunctionalTestCase):
    def runTest(self):
        self._tester.login_as(Usernames.product_owner)
        ticket_info = self._tester.perform_import(GOOD_CSV_DATA)
        first_ticket_id, second_ticket_id = \
            _change_first_hit_and_get_ticket_ids(ticket_info, new_first_summary=u"Invalid Summary that does not exist")
        changed_tickets = self._tester.perform_ticket_deletion_through_csv_upload(ticket_info)
        
        tc.find('File contents read with encoding <b>UTF-8</b>')
        self.assertEqual(1, len(changed_tickets))
        tc.find("Ticket %s has a different summary" % first_ticket_id)
        self._tester.go_to_view_ticket_page(first_ticket_id, should_fail=False)
        self._tester.go_to_view_ticket_page(second_ticket_id, should_fail=True)
        tc.code(404)



class TestPerformDeleteFromCSVForceDelete(AgiloFunctionalTestCase):
    def runTest(self):
        self._tester.login_as(Usernames.product_owner)
        ticket_info = self._tester.perform_import(GOOD_CSV_DATA)
        first_ticket_id, second_ticket_id = \
            _change_first_hit_and_get_ticket_ids(ticket_info, new_first_summary=u"Invalid Summary that does not exist")
        
        changed_tickets = self._tester.perform_ticket_deletion_through_csv_upload(ticket_info, force=True)
        self.assertEqual(2, len(changed_tickets))
        self._tester.go_to_view_ticket_page(first_ticket_id, should_fail=True)
        tc.code(404)
        self._tester.go_to_view_ticket_page(second_ticket_id, should_fail=True)
        tc.code(404)



class TestPerformDeleteFromCSVNotAuthorized(AgiloFunctionalTestCase):
    def runTest(self):
        self._tester.login_as(Usernames.product_owner)
        ticket_info = self._tester.perform_import(GOOD_CSV_DATA)
        self._tester.login_as(Usernames.team_member)
        changed_tickets = self._tester.perform_ticket_deletion_through_csv_upload(ticket_info)
        self.assertEqual(0, len(changed_tickets))


if __name__ == '__main__':
    from agilo.test.testfinder import run_all_tests
    run_all_tests(__file__)

