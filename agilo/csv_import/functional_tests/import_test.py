# -*- coding: utf-8 -*-

import re

from trac.tests.functional import tc

from agilo.test import Usernames
from agilo.test.functional import AgiloFunctionalTestCase
from agilo.utils import Status


GOOD_CSV_DATA = u'''summary,some,customer,businessvalue,keywords
Umlaut check äöü,foo,XYZ Bank,,data_check
Import data from CSV with €,,ABC Ltd.,,import'''

GOOD_CSV_DATA_FOR_ISO = u'''summary,some,customer,businessvalue,keywords
Umlaut check äöü,foo,XYZ Bank,,data_check
Import data from CSV with ,,ABC Ltd.,,import'''

GOOD_CSV_DATA_SETTING_OWNER = u"""__color__,ticket,summary,version,milestone,type,owner,status,created,_changetime,description,reporter
3,1,Fix the CSV import,None,None,requirement,,new,2008-08-07T10:12:52Z+0200,2008-08-07T10:12:52Z+0200,This is the CSV import,fs
"""

UNKNOWN_TYPE_CSV_DATA = u"""__color__,ticket,summary,version,milestone,type,owner,status,created,_changetime,_description,_reporter
3,1,Fix the CSV import,None,None,unknown_type,,new,2008-08-07T10:12:52Z+0200,2008-08-07T10:12:52Z+0200,This is the CSV import,fs
"""


class TestImportPreviewFromCSV(AgiloFunctionalTestCase):
    def runTest(self):
        self._tester.login_as(Usernames.product_owner)
        self._tester.upload_csv_for_import(GOOD_CSV_DATA, 'UTF-8')
        tc.find('<h1>Import Preview</h1>')
        tc.find('File contents read with encoding <b>UTF-8</b>.')
        
        tc.find('businessvalue')
        tc.find(u'Umlaut check äöü'.encode('UTF-8'))
        tc.find(u'Import data from CSV with €'.encode('UTF-8'))
        
        match = re.search('<input type="submit" .*?value="Import".*?/>', tc.show())
        self.assertNotEqual(None, match)


class TestImportPreviewFromCSVWrongEncoding(AgiloFunctionalTestCase):
    def runTest(self):
        self._tester.login_as(Usernames.product_owner)
        file_encoding = 'ISO-8859-1'
        user_encoding = 'UTF-8'
        self._tester.upload_csv_for_import(GOOD_CSV_DATA_FOR_ISO, file_encoding)
        tc.find('<h1>Import Preview</h1>')
        
        guessed_encoding_from_chardet = 'WINDOWS-1255'
        tc.find('File contents read with encoding <b>%s</b>.' % guessed_encoding_from_chardet)
        tc.find('<strong>Warning:</strong>')
        tc.notfind(u'Umlaut check äöü'.encode('UTF-8'))
        
        tc.formvalue('import_preview', 'file_encoding', user_encoding)
        tc.submit('Preview')
        tc.find('File contents read with encoding <b>%s</b>.' % user_encoding)
        tc.find('heuristic suggests <b>%s</b> for decoding' % guessed_encoding_from_chardet)
        
        tc.formvalue('import_preview', 'file_encoding', file_encoding)
        tc.submit('Preview')
        
        tc.notfind('<strong>Warning:</strong>')
        #tc.find('File contents read with encoding <b>%s</b>.' % file_encoding)
        tc.notfind(u'Umlaut check äöü'.encode(file_encoding))


class TestImportPreviewFromCSVBinaryData(AgiloFunctionalTestCase):
    def runTest(self):
        binary_data = '\xcf\xd0\xe0\x11\xb1\xa1\xe1\x1a\x00\x00'
        self._tester.upload_csv_for_import(binary_data, file_encoding=None)
        tc.find('<h1>Import Preview</h1>')
        
        tc.find('<strong>Warning:</strong>')
        tc.notfind('businessvalue')
        tc.notfind(u'Umlaut check äöü'.encode('UTF-8'))
        tc.find("Import not available, errors detected.")


class TestImportPreviewEmptyFile(AgiloFunctionalTestCase):
    def runTest(self):
        self._tester.upload_csv_for_import('', 'ISO-8859-15')
        tc.find('<h1>Import New Tickets from CSV</h1>')
        
        tc.find('<strong>Warning:</strong>')
        tc.find('Uploaded file is empty.')


class TestCorrectImport(AgiloFunctionalTestCase):
    def runTest(self):
        import_user = Usernames.product_owner
        self._tester.login_as(import_user)
        ticket_list = [(u"Umlaut check äöü", "requirement"), 
                       (u"Import data from CSV with €", "requirement"), ]
        ticket_info = self._tester.perform_import(GOOD_CSV_DATA, "UTF-8",
                                                  expected_tickets=ticket_list)
        
        for (ticket_id, summary, type, state) in ticket_info:
            self.assertEqual("new", state)
            reporter = self._tester.get_reporter_of_ticket(ticket_id)
            self.assertEqual(import_user, reporter)


class TestNoPermissionsAtAll(AgiloFunctionalTestCase):
    def runTest(self):
        self._tester.login_as(Usernames.team_member)
        changed_tickets = self._tester.perform_import(GOOD_CSV_DATA, "UTF-8")
        self.assertEqual(0, len(changed_tickets))
        tc.find("No permission to create a requirement.")


class TestClickCancelReturnsToFileUpload(AgiloFunctionalTestCase):
    def runTest(self):
        self._tester.login_as(Usernames.product_owner)
        self._tester.upload_csv_for_import(GOOD_CSV_DATA, 'UTF-8')
        tc.find('<h1>Import Preview</h1>')
        
        # Select one form for twill
        tc.formvalue('cancel_import', 'cancel', '1')
        tc.submit('Cancel')
        
        tc.notfind('<strong>Warning:</strong>')
        tc.find('<h1>Import New Tickets from CSV</h1>')


class TestCatchExceptionsForUnknownTypes(AgiloFunctionalTestCase):
    """If a ticket with an unknown type is imported, we should catch all 
    exceptions so that the user does not get a TracError with stack trace
    (see bug #230)."""
    def runTest(self):
        self._tester.login_as(Usernames.product_owner)
        
        self._tester.perform_import(UNKNOWN_TYPE_CSV_DATA, "UTF-8", 
                                    expected_tickets=[])


class TestCanSetOwnerAndStatusDuringImport(AgiloFunctionalTestCase):
    """A user can set owner and status of a ticket when importing it."""
    
    def runTest(self):
        self._tester.login_as(Usernames.product_owner)
        imported_tickets = self._tester.perform_import(GOOD_CSV_DATA_SETTING_OWNER, "UTF-8")
        self.assertEqual(1, len(imported_tickets))
        
        requirement_id = imported_tickets[0][0]
        ticket_page = self.tester.navigate_to_ticket_page(requirement_id)
        self.assertEqual('fs', ticket_page.reporter())
        self.assertEqual('', ticket_page.owner())
        self.assertEqual(Status.NEW, ticket_page.status())



if __name__ == '__main__':
    from agilo.test.testfinder import run_all_tests
    run_all_tests(__file__)

