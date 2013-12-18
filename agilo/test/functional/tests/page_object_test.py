# -*- encoding: utf-8 -*-
#   Copyright 2008 Agile42 GmbH, Berlin (Germany)
#   Copyright 2007 Andrea Tomasini <andrea.tomasini_at_agile42.com>
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
#   Author: 
#       - Felix Schwarz <felix.schwarz__at__agile42.com>
#       - Martin Häcker <martin.haecker__at__agile42.com>

import agilo.utils.filterwarnings

from agilo.test import AgiloTestCase
from agilo.test.functional.agilo_tester import PageObject


class PageObjectTest(AgiloTestCase):
    
    warning = """<body>
    	<div class="main" style="left: 249px;"><!-- Main Content -->
    	    <div class="nav" id="ctxtnav">
    	    </div>
    	    <div class="system-message warning">
    			    <strong>Warning:</strong> fnord warning
    	    </div>
            <div class="admin" id="content">
              <h1>Administration</h1>
            </div>
    	</div>
    </body>
    """
    notice = """<body>
    	<div class="main" style="left: 249px;"><!-- Main Content -->
    	    <div class="nav" id="ctxtnav">
    	    </div>
    	    <div class="system-message notice">
    			    <strong>Notice:</strong> fnord notice one
    	    </div>
    	    <div class="system-message notice">
    			    <strong>Notice:</strong> fnord notice two
    	    </div>
            <div class="admin" id="content">
              <h1>Administration</h1>
            </div>
    	</div>
    </body>
    """
    
    def test_can_find_notice_on_page(self):
        page = PageObject()
        page.set_html(self.notice)
        self.assert_true(page.has_notice('fnord notice one'))
        self.assert_true(page.has_notice('fnord notice two'))
    
    def test_can_find_warnings_on_page(self):
        page = PageObject()
        page.set_html(self.warning)
        self.assert_true(page.has_warning('fnord warning'))
        
    def test_can_remove_html_formatting(self):
        page = PageObject()
        warning_without_html = page.remove_html_and_whitespace(self.warning)
        self.assert_equals("Warning: fnord warning Administration", warning_without_html)


# TODO: has_no_notice_or_warning, etc.
