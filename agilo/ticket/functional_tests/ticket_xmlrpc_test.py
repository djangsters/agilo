# -*- encoding: utf-8 -*-
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

import urllib2, base64
import xmlrpclib

from agilo.test.functional import AgiloFunctionalTestCase
from agilo.test import Usernames
from agilo.utils.config import AgiloConfig

class TestXMLRPC(AgiloFunctionalTestCase):
    
    def setUp(self):
        self.super()
        self.tester.login_as(Usernames.admin)
        

        components = AgiloConfig(self.env).get_section('components')
        components.change_option("tracrpc.*", 'enabled')
        components.save()
        
        self.ticket1_id = self.tester.create_new_agilo_task('foo', 'abc')
        self.ticket2_id = self.tester.create_new_agilo_task('bar', 'def')
        
    def _should_skip_test(self):
        try:
            import tracrpc
        except:
            return True
        return False
    
    def _send_rpc_request(self, body):
        request = urllib2.Request(self.tester.url + self.env.base_url + '/login/rpc', data=body)
        request.add_header('Content-Type', 'application/xml')
        request.add_header('Content-Length', str(len(body)))
        request.add_header('Authorization', 'Basic %s' \
                                 % base64.encodestring('admin:admin')[:-1])
        self.assertEquals('POST', request.get_method())
        response = urllib2.urlopen(request)
        self.assertEquals(200, response.code)
        return response

    def _request_body_for_fetch(self, ticket_id):
        return """<?xml version="1.0"?>
                    <methodCall>
                        <methodName>ticket.get</methodName>
                        <params>
                            <param><int>%s</int></param>
                        </params>
                    </methodCall>""" % ticket_id

    def test_can_fetch_a_ticket(self):
        if self._should_skip_test():
            return
        body = self._request_body_for_fetch(self.ticket1_id)
        response = self._send_rpc_request(body)
        response_body = response.read()
        self.assertRegexpMatches(response_body, "<int>%s</int>" % self.ticket1_id)
        self.assertRegexpMatches(response_body, "<value><string>foo</string></value>")
        self.assertRegexpMatches(response_body, "<value><string>abc</string></value>")
        
    def test_can_fetch_ticket_list(self):
        if self._should_skip_test():
            return
        body = """<?xml version="1.0"?>
                    <methodCall>
                        <methodName>ticket.query</methodName>
                            <params>
                                <param><string>max=0</string></param>
                            </params>
                    </methodCall>""" 
        response = self._send_rpc_request(body)
        response_body = response.read()
        self.assertRegexpMatches(response_body, "<int>%s</int>" % self.ticket1_id)
        self.assertRegexpMatches(response_body, "<int>%s</int>" % self.ticket2_id)
        
    def test_can_create_tickets(self):
        if self._should_skip_test():
            return
        self.tester.delete_all_tickets()
        
        body = """<?xml version="1.0"?>
                    <methodCall>
                        <methodName>ticket.create</methodName>
                        <params>
                            <param><value>ticket to sniff</value></param>
                            <param><value></value></param>
                            <param><value><struct>
                                <member><name>keywords</name><value></value></member>
                                <member><name>type</name><value>task</value></member>
                                <member><name>remaining_time</name><value></value></member>
                                <member><name>drp_resources</name><value></value></member>
                                <member><name>version</name><value></value></member>
                                <member><name>milestone</name><value></value></member>
                                <member><name>component</name><value>component1</value></member>
                                <member><name>priority</name><value>blocker</value></member>
                                <member><name>owner</name><value></value></member>
                                <member><name>action</name><value></value></member>
                                <member><name>cc</name><value></value></member>
                                </struct></value></param>
                            <param><value><boolean>1</boolean></value></param>
                        </params>
                    </methodCall>"""
            
        response = self._send_rpc_request(body)
        response_body = response.read()
        self.assertRegexpMatches(response_body, "<int>1</int>")

    def test_can_update_tickets(self):
        if self._should_skip_test():
            return
        
        # in order to update a ticket, its timestamp is needed
        body = self._request_body_for_fetch(self.ticket1_id)
        response = self._send_rpc_request(body)
        response_body = response.read()
        response_object = xmlrpclib.loads(response_body)
        ts = response_object[0][0][3]['_ts']
        
        body = """<?xml version="1.0"?>
                    <methodCall>
                        <methodName>ticket.update</methodName>
                        <params>
                            <param><value><i4>%s</i4></value></param>
                            <param><value></value></param>
                            <param><value><struct>
                                <member><name>summary</name><value>new summary</value></member>
                                <member><name>action_resolve_resolve_resolution</name><value>fixed</value></member>
                                <member><name>action_reassign_reassign_owner</name><value>admin</value></member>
                                <member><name>keywords</name><value></value></member>
                                <member><name>status</name><value>new</value></member>
                                <member><name>type</name><value>task</value></member>
                                <member><name>remaining_time</name><value>11</value></member>
                                <member><name>drp_resources</name><value></value></member>
                                <member><name>version</name><value></value></member>
                                <member><name>milestone</name><value></value></member>
                                <member><name>component</name><value>component1</value></member>
                                <member><name>description</name><value></value></member>
                                <member><name>priority</name><value>blocker</value></member>
                                <member><name>action</name><value>leave</value></member>
                                <member><name>owner</name><value>somebody</value></member>
                                <member><name>cc</name><value></value></member>
                                <member><name>_ts</name><value>%s</value></member>
                            </struct></value></param>
                            <param><value><boolean>1</boolean></value></param>
                            </params></methodCall>""" % (self.ticket1_id, ts)
            
        response = self._send_rpc_request(body)
        response_body = response.read()
        self.assertRegexpMatches(response_body, "<member>\n<name>remaining_time</name>\n<value><string>11</string></value>\n</member>")

    def test_can_close_tickets(self):
        if self._should_skip_test():
            return
        
        # in order to update a ticket, its timestamp is needed
        body = self._request_body_for_fetch(self.ticket1_id)
        response = self._send_rpc_request(body)
        response_body = response.read()
        response_object = xmlrpclib.loads(response_body)
        ts = response_object[0][0][3]['_ts']
        
        body = """<?xml version="1.0"?>
                    <methodCall>
                        <methodName>ticket.update</methodName>
                        <params>
                            <param><value><i4>%s</i4></value></param>
                            <param><value></value></param>
                            <param><value><struct>
                                <member><name>summary</name><value>new summary</value></member>
                                <member><name>action_resolve_resolve_resolution</name><value>fixed</value></member>
                                <member><name>action_reassign_reassign_owner</name><value>admin</value></member>
                                <member><name>keywords</name><value></value></member>
                                <member><name>status</name><value>closed</value></member>
                                <member><name>resolution</name><value></value></member>
                                <member><name>type</name><value>task</value></member>
                                <member><name>remaining_time</name><value>2</value></member>
                                <member><name>drp_resources</name><value></value></member>
                                <member><name>version</name><value></value></member>
                                <member><name>milestone</name><value></value></member>
                                <member><name>component</name><value>component1</value>
                                </member><member><name>description</name><value></value>
                                </member><member><name>priority</name><value>blocker</value>
                                </member><member><name>action</name><value>resolve</value></member>
                                <member><name>owner</name><value>somebody</value></member>
                                <member><name>cc</name><value></value></member>
                                <member><name>_ts</name><value>%s</value></member>
                            </struct></value></param>
                            <param><value><boolean>1</boolean></value></param>
                        </params>
                    </methodCall>""" % (self.ticket1_id, ts)
            
        response = self._send_rpc_request(body)
        response_body = response.read()
        self.assertRegexpMatches(response_body, "<member>\n<name>status</name>\n<value><string>closed</string></value>\n</member>")
            
    def test_can_delete_tickets(self):
        if self._should_skip_test():
            return
        body = """<?xml version="1.0"?>
            <methodCall>
                <methodName>ticket.delete</methodName>
                <params>
                    <param><int>%s</int></param>
                </params>
            </methodCall>""" % self.ticket1_id
        self._send_rpc_request(body)

        response = self._send_rpc_request(self._request_body_for_fetch(self.ticket1_id))
        response_body = response.read()
        self.assertRegexpMatches(response_body, "Ticket %s does not exist" % self.ticket1_id )

    def test_can_restrict_to_task_tickets(self):
        if self._should_skip_test():
            return
        body = """<?xml version="1.0"?>
                    <methodCall>
                        <methodName>ticket.type.getAll</methodName>
                        <params/>
                    </methodCall>"""
        
        response = self._send_rpc_request(body)
        response_body = response.read()
        self.assertRegexpMatches(response_body, "<methodResponse>\n<params>\n<param>\n<value><array><data>\n<value><string>task</string></value>\n</data></array></value>\n</param>\n</params>\n</methodResponse>\n")


        