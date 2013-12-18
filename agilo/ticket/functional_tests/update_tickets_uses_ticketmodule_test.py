# -*- coding: utf8 -*-
#   Copyright 2009 Agile42 GmbH, Berlin (Germany)
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
#   Authors:
#        - Felix Schwarz <felix.schwarz__at__agile42.com>
#        - Martin Häcker <martin.haecker__at__agile42.com>

import email
import random

from trac.tests.functional import tc
from trac.ticket.tests.notification import SMTPThreadedServer

from agilo.test import Usernames
from agilo.ticket.functional_tests.json_functional_testcase import JSONFunctionalTestCase
from agilo.utils import Key
from agilo.utils.config import AgiloConfig



class UpdatingATicketWithJSONSendsNotificationEmail(JSONFunctionalTestCase):
    
    def _set_configuration(self, section, property, value):
        env = self.testenv.get_trac_environment()
        config = AgiloConfig(env)
        self._old_configuration[(section, property)] = value
        config.change_option(property, value, section, save=True)
    
    def _restore_old_configuration(self):
        env = self.testenv.get_trac_environment()
        config = AgiloConfig(env)
        for (section, property), value in self._old_configuration.items():
            config.change_option(property, value, section)
        config.save()
    
    def _enable_ticket_notifications(self, smtp_port):
        def config_set(property, value):
            self._set_configuration('notification', property, value)
        config_set('smtp_enabled', 'true')
        config_set('smtp_port', str(smtp_port))
        config_set('smtp_server','localhost')
        config_set('always_notify_reporter', 'true')
        config_set('smtp_always_cc', 'foo@example.com')
    
    def setUp(self, *args, **kwargs):
        super(UpdatingATicketWithJSONSendsNotificationEmail, self).setUp(*args, **kwargs)
        self._old_configuration = {}
        
        smtp_port = random.randint(20000, 30000)
        self.smtpd = SMTPThreadedServer(smtp_port)
        self.smtpd.start()
        self._enable_ticket_notifications(smtp_port)
    
    def tearDown(self, *args, **kwargs):
        self.smtpd.cleanup()
        self.smtpd.stop()
        self._restore_old_configuration()
        super(UpdatingATicketWithJSONSendsNotificationEmail, self).tearDown(*args, **kwargs)
    
    def _consume_ticket_creation_notification_mail(self, task_id):
        message = self.smtpd.get_message()
        title = '#%s: My first task' % task_id
        self.assertTrue(title in message, message)
        self.smtpd.store.reset(None)
    
    def _subject(self, raw_message):
        message = email.message_from_string(raw_message)
        # If the subject line is too long, the line will we wrapped
        # Python's email module does not remove the line endings automatically
        subject = message['Subject'].replace('\n', '').replace('\r', '')
        return subject
    
    def runTest(self):
        self.tester.login_as(Usernames.team_member)
        task_id = self.tester.create_new_agilo_task('My first task')
        self._consume_ticket_creation_notification_mail(task_id)
        
        self.json_tester.login_as(Usernames.team_member)
        new_summary = 'Notification Task'
        new_task_attributes = {Key.SUMMARY: new_summary}
        self.json_tester.edit_ticket(task_id, **new_task_attributes)
        
        self.tester.go_to_view_ticket_page(task_id)
        tc.find(new_summary)
        
        self.assertTrue('foo@example.com' in self.smtpd.get_recipients())
        subject = self._subject(self.smtpd.get_message())
        self.assertTrue(new_summary in subject, repr(subject))


if __name__ == '__main__':
    from agilo.test import run_all_tests
    run_all_tests(__file__)

