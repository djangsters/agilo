#!/usr/bin/env python
# -*- coding: utf-8 -*-
#   Copyright 2008 Agile42 GmbH - Andrea Tomasini
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
# Authors:
#     - Felix Schwarz


from trac.core import TracError

from agilo.test import AgiloTestCase
from agilo.ticket.links import LinkOption
from agilo.ticket.links.search import LinksSearchModule
from agilo.utils import Key, Type
from agilo.utils.config import AgiloConfig


class TestSearchLinks(AgiloTestCase):
    
    def setUp(self):
        self.super()
        links = AgiloConfig(self.env).get_section(AgiloConfig.AGILO_LINKS)
        links.change_option(LinkOption.ALLOW, 'story-task, bug-task, bug-story')
        
        # Creates tickets
        self.t1 = self.teh.create_ticket(Type.USER_STORY, props={Key.SUMMARY: u"User Story"})
        self.t2 = self.teh.create_ticket(Type.TASK, props={Key.SUMMARY: u"First Task"})
        self.t3 = self.teh.create_ticket(Type.TASK, props={Key.SUMMARY: u"Second Task"})
        self.linksearch = LinksSearchModule(self.env)
    
    def testSearchNoLinks(self):
        results = self.linksearch.get_tickets_matching(self.t1.id, "task")
        self.assert_equals(2, len(results))
        res_t2 = {Key.TYPE: self.t2.get_type(), Key.ID: self.t2.get_id(), 
                   Key.SUMMARY: self.t2[Key.SUMMARY]}
        self.assert_true(res_t2 in results)
        res_t3 = {Key.TYPE: self.t3.get_type(), Key.ID: self.t3.get_id(), 
                   Key.SUMMARY: self.t3[Key.SUMMARY]}
        self.assert_true(res_t3 in results)
    
    def testSearchExcludeLinkedTickets(self):
        self.t1.link_to(self.t2)
        results = self.linksearch.get_tickets_matching(self.t1.id, "task")
        self.assert_equals(1, len(results))
        res_t3 = {Key.TYPE: self.t3.get_type(), Key.ID: self.t3.get_id(), 
                   Key.SUMMARY: self.t3[Key.SUMMARY]}
        self.assert_true(res_t3 in results)
        
    def testInvalidId(self):
        self.assert_raises(TracError, self.linksearch.get_tickets_matching, 
                          "invalid", "task")
        
    def testNoTicketWithId(self):
        self.assert_raises(TracError, self.linksearch.get_tickets_matching, 
                          "4711", "task")


