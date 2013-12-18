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
#   Authors:
#        - Andrea Tomasini <andrea.tomasini__at__agile42.com>
#        - Felix Schwarz <felix.schwarz__at__agile42.com>

import re

from trac.core import TracError
from trac.util.html import html
from trac.wiki.macros import WikiMacroBase

from agilo.utils.log import debug
from agilo.charts.chart_generator import ChartGenerator


__all__ = ['AgiloChartMacro']

class AgiloChartMacro(WikiMacroBase):
    """
    A Small Macro that lets you embed Agilo Charts into Wiki Pages
    Uses as:
     [[AgiloChart(<type>, <sprint>[, <widthxheight>])]]
     [[AgiloChart(sprint_tickets, TestMe, 600x120)]]
     
    Available Charts type:
     sprint_resources
     sprint_tickets
     burndown
    """
    
    def _get_chart_type(self, type_string):
        quoted_re = re.compile("(?:[\"'])(.*)(?:[\"'])$")
        chart_type = type_string.strip()
        match = quoted_re.match(chart_type)
        if match != None:
            chart_type = match.group(1)
        return chart_type
    
    def _get_sprint(self, sprint_string):
        quoted_re = re.compile("(?:[\"'])(.*)(?:[\"'])$")
        sprint = sprint_string.strip()
        match = quoted_re.match(sprint)
        if match != None:
            sprint = match.group(1)
        return sprint
    
    def _get_dimensions(self, macro_args):
        width, height = (None, None)
        # The first argument should be the Chart Type
        size_re = re.compile('([0-9]+)(?:x|X)([0-9]+)$') # Matches 120x130
        
        # Parse all the Arguments
        for arg in macro_args:
            arg = arg.strip()
            match = size_re.match(arg)
            if match != None:
                # extract width and height keyword
                width, height = match.group(1), match.group(2)
                break
        return (width, height)
    
    def expand_macro(self, formatter, name, content):
        req = formatter.req
        # Analyze the arguments list, that should be in content
        args = content.split(',')
        if len(args) == 0:
            raise TracError("No argument provided for %s." % self.__class__.__name__)
        
        # The first must be the type of the chart
        chart_type = self._get_chart_type(args[0])
        # The second the Sprint
        sprint_name = self._get_sprint(args[1])
        width, height = self._get_dimensions(args[2:])
        filter_by = None
        if len(args) >= 4:
            filter_by = args[3]
        
        chart_params = dict(sprint_name=sprint_name, width=width, height=height, 
                            filter_by=filter_by)
        debug(self.env, "Params: %s" % chart_params)
        chart = ChartGenerator(self.env).get_chartwidget(chart_type, **chart_params)
        chart.prepare_rendering(req)
        return html.DIV(chart.display())
