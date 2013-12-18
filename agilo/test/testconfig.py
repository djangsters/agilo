# -*- coding: utf-8 -*-
#   Copyright 2010 Agile42 GmbH, Berlin (Germany)
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

from ConfigParser import SafeConfigParser
from StringIO import StringIO

from agilo.api import ValueObject


__all__ = ['TestConfiguration']


class TestConfiguration(object):
    def __init__(self):
        self._db = self._db_defaults()
    
    def _db_defaults(self):
        return ValueObject(scheme='sqlite', host='localhost', user=None, password=None)
    
    def db(self):
        return self._db
    
    def _update_from_parser(self, parser, section, option, targetattr):
        if parser.has_option(section, option):
            setattr(targetattr, option, parser.get(section, option))
    
    def fill_db_config(self, parser):
        self._db = self._db_defaults()
        if not parser.has_section('db'):
            return
        self._update_from_parser(parser, 'db', 'scheme', self._db)
        self._update_from_parser(parser, 'db', 'host', self._db)
        self._update_from_parser(parser, 'db', 'user', self._db)
        self._update_from_parser(parser, 'db', 'password', self._db)
    
    @classmethod
    def from_configstring(cls, configstring):
        config = TestConfiguration()
        parser = SafeConfigParser()
        parser.readfp(StringIO(configstring))
        config.fill_db_config(parser)
        return config


