# -*- encoding: utf-8 -*-
#   Copyright 2008-9 Agile42 GmbH, Berlin (Germany)
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


from agilo.test.functional.agilo_functional_testcase import *
from agilo.test.functional.agilo_environment import *
from agilo.test.functional.agilo_tester import *
from agilo.test.functional.api import *
from agilo.test.functional.even_better_twill import *
from agilo.test.functional.json_tester import *
from agilo.test.functional.multi_environment import *
from agilo.test.functional.trac_compat import *
from agilo.test.functional.trac_environment import *
from agilo.test.functional.windmill_tester import *

# do not import nose_environment_manager here - otherwise nose will become a 
# direct dependency for running Agilo functional tests


def build_suite():
    return FunctionalTestSuite()


