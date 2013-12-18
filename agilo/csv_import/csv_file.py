# -*- coding: utf-8 -*-
#   Copyright 2008 Agile42 GmbH - Andrea Tomasini 
#   Copyright 2007 Andrea Tomasini <andrea.tomasini_at_agile42.com>
#                  Alexander Aptus <alexander.aptus_at_gmail.com>
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

from copy import copy
import csv

from trac.util.translation import _

from agilo.utils.log import debug


def columnize(s):
    """Removes all the white spaces and transform the string into lowercase"""
    ret = s.lower().replace(' ','').strip()
    return ret


class CSVFile(object):
    def __init__(self, fp, performer_name, encoding, delimiter=','):
        self.performer_name = performer_name
        self.encoding = encoding
        self.allowed_fields = None
        self.reader = csv.reader(fp, delimiter=delimiter)
        try:
            self.init_headings()
        except Exception, e:
            raise ValueError(e)
    
    def next(self):
        row = self.reader.next()
        res = {}
        for i, field in enumerate(row):
            if i >= len(self.header):
                break
            if (self.allowed_fields == None) or (self.header[i] in self.allowed_fields):
                res[self.header[i]] = unicode(field, self.encoding)
        return res
    
    def __iter__(self):
        return self
    
    def get_headings(self):
        return self.header
    
    def init_headings(self):
        row_header = self.reader.next()
        headerlist = []
        for c in row_header:
            headerlist.append(columnize(c))
        self.header = headerlist
        
        header_sorted = copy(headerlist)
        header_sorted.sort()
        #debug(FOO, _("Columns in import file: %s") % header_sorted)
    
    def set_allowed_fields(self, allowed_fields):
        self.allowed_fields = allowed_fields
        # Eigentlich nicht direkt nötig!
        assert self.header != None
        if self.header != None:
            for colname in self.header:
                if not colname in self.allowed_fields:
                    msg = _("Column '%s' is not relevant for '%s' and will be ignored.")
                    # debug(FOO, msg % (colname, self.performer_name))
