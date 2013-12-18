# -*- encoding: utf-8 -*-
#   Copyright 2008-2010 Agile42 GmbH, Berlin (Germany)
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
"""
This nose test selector plugin uses the 'AttributeSelector' plugin from 
nose core. However it accepts a class if it has attribute (even if that one
was set by a super class.

The AttributeSelector plugin only selects class which define the attribute 
themselves.
"""
# Be careful not to import symbols from this module in the rest of Agilo 
# - otherwise nose will become a dependency for all Agilo installations!

import os

from trac.test import Mock
from nose.plugins import Plugin
from nose.plugins.attrib import AttributeSelector

from agilo.utils.simple_super import SuperProxy


__all__ = ['NoseClassAttributeSelector', 'NoseExcludeUnittestRunnerFunctions']


class NoseClassAttributeSelector(Plugin):
    
    super = SuperProxy()
    
    def __init__(self):
        self.super()
        self._selector = None
    
    # ------------------------------------------------------------------------
    # Implementations of nose plugin API
    
    def options(self, parser, env=os.environ):
        helptext = 'Run only tests that have the specified attributes (or ' + \
                   'which are in a class with that attribute'
        parser.add_option('--classattr', dest='classattr', action='append',
                          default=env.get('NOSE_ATTR'), help=helptext)
    
    def configure(self, options, config):
        if options.classattr:
            # The AttributeSelector plugin has a very long parsing method so
            # it is hard just to use it standalone - let's fake the complete 
            # parsing process
            fake_options = Mock(attr=options.classattr, eval_attr=None)
            self.selector().configure(fake_options, config)
            self.enabled = self.selector().enabled
    
    def _class_attributes(self, cls):
        attributes = dict()
        for name in dir(cls):
            # private attributes need to be fetched differently and
            # I guess no one will filter based on these...
            if name.startswith('__'):
                continue
            attributes[name] = getattr(cls, name)
        return attributes
    
    def wantClass(self, cls):
        cls_attributes = self._class_attributes(cls)
        if self.satisfies_criteria(cls_attributes) is not False:
            if hasattr(cls, 'should_be_skipped'):
                instance = cls()
                return not instance.should_be_skipped()
            # don't *force* selection of TestCase
            return None
        return False
    
    # ------------------------------------------------------------------------
    # internal convenience functionality
    
    def selector(self):
        if self._selector is None:
            self._selector = AttributeSelector()
        return self._selector
    
    def satisfies_criteria(self, class_attributes):
        return self.selector().validateAttrib(class_attributes)



class NoseExcludeUnittestRunnerFunctions(Plugin):
    """Exclude our unittest-based runner functions - otherwise the test suite
    will be executed multiple times."""
    
    super = SuperProxy()
    
    def options(self, parser, env=None):
        parser.add_option("--only-real-tests", dest="only_real_tests", default=False,
                          help="execute only real tests")
    
    def configure(self, options, config):
        if options.only_real_tests:
            self.enabled = True
            config.getTestCaseNamesCompat = True
    
    def wantClass(self, cls):
        if cls.__dict__.get('is_abstract_test', False):
            return False
        
        CLASS_BLACKLIST = ('TestFinder', )
        if cls.__name__ in CLASS_BLACKLIST:
            return False
        return None
    
    def wantFunction(self, function):
        if function.__name__ in ['run_all_tests', 'run_unit_tests']:
            return False
        return None

