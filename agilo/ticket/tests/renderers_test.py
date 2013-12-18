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
#     - Andrea Tomasini


from agilo.test import AgiloTestCase
from agilo.ticket.renderers import Renderer, TimePropertyRenderer
from agilo.utils import Key, Type
from agilo.utils.config import AgiloConfig



class TestRenderers(AgiloTestCase):
    
    def testBaseRenderer(self):
        """Tests the basic renderer"""
        story = self.teh.create_ticket(Type.USER_STORY, props={Key.STORY_PRIORITY: 'Mandatory'})
        r = Renderer(story, Key.STORY_PRIORITY)
        self.assert_equals('Mandatory', r())
        self.assert_equals('Mandatory', '%s' % r)
        
    def testFloatDecimalRenderer(self):
        """Tests the float and decimal renderer"""
        req = self.teh.create_ticket(Type.REQUIREMENT, props={Key.BUSINESS_VALUE: '2000'})
        story = self.teh.create_ticket(Type.USER_STORY, props={Key.STORY_POINTS: '20',
                                                               Key.STORY_PRIORITY: 'Mandatory'})
        req.link_to(story)
        r = Renderer(req, Key.ROIF)
        self.assert_equals('100.0', r())
        self.assert_equals('100.0', '%s' % r)
        
    def testTimeRenderer(self):
        """Tests the time renderer"""
        task = self.teh.create_ticket(Type.TASK, props={Key.REMAINING_TIME: '2.5'})
        r = Renderer(task, Key.REMAINING_TIME)
        # force hours
        AgiloConfig(self.teh.get_env()).use_days = False
        self.assert_equals('2.5h', r())
        self.assert_equals('2.5h', '%s' % r)
        # force days
        AgiloConfig(self.teh.get_env()).use_days = True
        self.assert_equals('2.5d', r())
        self.assert_equals('2.5d', '%s' % r)
        
    def testTimeRendererWithIntegers(self):
        task = self.teh.create_ticket(Type.TASK, props={Key.REMAINING_TIME: '2'})
        r = Renderer(task, Key.REMAINING_TIME)
        # force hours
        AgiloConfig(self.teh.get_env()).use_days = False
        self.assert_equals('2.0h', r())
        
    def testTimeRendererDirectCall(self):
        self.assert_equals('3.6h', '%s' % TimePropertyRenderer(self.teh.get_env(), 3.6))
    
    def testTimeRendererWithCalculatedProperty(self):
        task = self.teh.create_ticket(Type.TASK, props={Key.REMAINING_TIME: '0'})
        story = self.teh.create_ticket(Type.USER_STORY)
        story.link_to(task)
        
        r = Renderer(story, Key.TOTAL_REMAINING_TIME)
        self.assert_equals(0, story[Key.TOTAL_REMAINING_TIME])
        self.assert_equals('0.0h', r())
   
    def testTimeRendererWithNone(self):
        task = self.teh.create_ticket(Type.TASK, props={Key.REMAINING_TIME: None})
        r = Renderer(task, Key.REMAINING_TIME)
        self.assert_equals('n.a.', r())
    
    def testRendererReturnsNAForNone(self):
        renderer = Renderer(None, 'foo')
        self.assert_equals('n.a.', renderer())
    
    def testRenderBasicPythonDatatypes(self):
        renderer = Renderer(12, 'foo')
        self.assert_equals(12, renderer())
        
        renderer = Renderer(12.5, 'foo')
        self.assert_equals('12.5', renderer())


if __name__ == '__main__':
    from agilo.test.testfinder import run_unit_tests
    run_unit_tests(__file__)