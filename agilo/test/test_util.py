# -*- encoding: utf-8 -*-
#   Copyright 2008. 2009 Agile42 GmbH, Berlin (Germany
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
#       - Martin Häcker <martin.haecker__at__agile42.com>

import sys

__all__ = ['get_instance_of_current_testcase', 'Usernames']

#-------------------------------------------------------------------------------
# extracted (and modified) from trac's better_twill
def get_instance_of_current_testcase():
    frame = sys._getframe()
    while frame:
        if frame.f_code.co_name in ('runTest', 'setUp', 'tearDown'):
            testcase = frame.f_locals['self']
            return testcase
        frame = frame.f_back
    raise Exception("No testcase was found on the stack. This was " + \
        "really not expected, and I don't know how to handle it.")
# ------------------------------------------------------------------------------

class Usernames(object):
    anonymous = 'anonymous'
    
    admin = 'admin'
    scrum_master = 'scrum_master'
    product_owner = 'product_owner'
    team_member = 'team_member'
    second_team_member = 'second_team_member'

