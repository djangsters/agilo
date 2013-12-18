#!/usr/bin/env python
# -*- coding: utf-8 -*-
#   Copyright 2007-2008 Agile42 GmbH - Andrea Tomasini
#   Copyright 2011 Agilo Software GmbH All rights reserved 
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
# 
# Authors:
#     - Andrea Tomasini
#     - Felix Schwarz

import re
import string
from trac.core import Component, implements, TracError
from trac.web.main import IRequestHandler

from agilo.ticket.links import LINKS_SEARCH_URL, LINKS_TABLE
from agilo.ticket.links.model import LinksConfiguration
from agilo.utils.log import debug, warning


__all__ = ['LinksSearchModule']

class LinksSearchModule(Component):
    implements(IRequestHandler)
    
    #=============================================================================
    # IRequestHandler methods
    #=============================================================================
    def match_request(self, req):
        return req.path_info.startswith(LINKS_SEARCH_URL)
    
    def process_request(self, req):
        query_parameter = 'q'
        if not req.args.has_key(query_parameter) or not req.args.has_key('id'):
            raise TracError("[%s]: id and %s must be provided as parameters" % \
                         self.__class__.__name__, query_parameter)
        t_sum = req.args.get(query_parameter)
        t_id = int(req.args.get('id'))
        data = dict()
        data["search_results"] = self.get_tickets_matching(t_id=t_id, summary=t_sum)
        return "agilo_search_results.html", data, None
        
    #=============================================================================
    # Class methods
    #=============================================================================
    def get_tickets_matching(self, t_id, summary):
        """
        Returns a list of dictionaries (id: value, summary: value) matching the summary 
        request and excluding the requesting ticket having id = id.
        """
        try:
            t_id = int(t_id) # Make sure it is an int :-)
            keyword = re.compile(summary, re.IGNORECASE)
            db = self.env.get_db_cnx()
            
            from agilo.ticket.model import AgiloTicketModelManager
            sql = """SELECT id, type, summary FROM ticket WHERE id != $id $allowed 
                  AND id NOT IN (SELECT dest FROM %s WHERE src = $id UNION
                  SELECT src FROM %s WHERE dest = $id) ORDER BY summary""" \
                    % (LINKS_TABLE, LINKS_TABLE)
            sql_query = string.Template(sql)
            sql_allowed = "AND ticket.type IN ('%s')"
            t_type = AgiloTicketModelManager(self.env).get(tkt_id=t_id).get_type()
            linkconfig = LinksConfiguration(self.env)
            if linkconfig.is_allowed_source_type(t_type):
                allowed_types = linkconfig.get_allowed_destination_types(t_type)
                allowed = sql_allowed % '\', \''.join(allowed_types)
            else:
                debug(self, "No Key found for #%s#" % repr(t_type))
                allowed = ''
                    
            sql_query = sql_query.substitute({'id' : t_id, 'allowed' : allowed})
            debug(self, "SQL: %s" % sql_query)
            cursor = db.cursor()
            cursor.execute(sql_query)
            
            results = []
            for row in cursor:
                if keyword.search(row[2] or ''):
                    results.append({'id': row[0], 'type': row[1], 
                                    'summary': row[2]})  
            
            debug(self, "Search Results: %s" % str(results))
            return results
            
        except Exception, e:
            warning(self, e)
            msg = "[%s]: ERROR: Search module unable to complete query!" % \
                    self.__class__.__name__
            raise TracError(msg) 
      
