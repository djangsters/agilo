# -*- encoding: utf-8 -*-
#   Copyright 2009 Agile42 GmbH, Berlin (Germany)
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
#   Author: Felix Schwarz <felix.schwarz_at_agile42.com>


from agilo.utils import Key
from agilo.utils.widgets import Widget

__all__ = ['FlotChartWidget']


class FlotChartWidget(Widget):
    """The FlotChartWidget is a special widget which contains some helper 
    methods suited for flot charts."""
    
    def _add_flot_js(self, scripts):
        flot_files = ['agilo/js/lib/jquery.flot.js',
                      'agilo/js/jquery.flot.grouped_charts.js',
                      'agilo/js/lib/excanvas.min.js']
        if scripts is None:
            scripts = []
        scripts = list(scripts)
        for filename in flot_files:
            if filename not in scripts:
                scripts.append(filename)
        return scripts
    
    def __init__(self, env, template_filename, scripts=None, **kwargs):
        if hasattr(self, Key.DEFAULT_WIDTH):
            kwargs.setdefault(Key.WIDTH, self.default_width)
        if hasattr(self, Key.DEFAULT_HEIGHT):
            kwargs.setdefault(Key.HEIGHT, self.default_height)
        scripts = self._add_flot_js(scripts)
        self.super(env, template_filename, scripts=scripts, **kwargs)
    
    def set_dimensions(self, width, height):
        self.data.update(dict(width=width, height=height))


