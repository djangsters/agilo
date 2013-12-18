# -*- encoding: utf-8 -*-
#   Copyright 2008 Agile42 GmbH, Berlin (Germany)
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
#   Author: Felix Schwarz <felix.schwarz_at_agile42.com>

from pkg_resources import resource_filename
from random import randint

from genshi.template import TemplateLoader, MarkupTemplate
from trac.util.translation import _
from trac.web.chrome import add_script, Chrome

from agilo.utils.simple_super import SuperProxy


class Widget(object):
    """Widgets encapsulate HTML+Javascript+CSS for commonly used building 
    blocks like charts."""
    
    super = SuperProxy()
    
    # REFACT: should not have chart resources in general widget / rename?
    def _define_chart_resources(self, env, template_filename, kwargs, scripts=None):
        """Helper method for inherited class that removes template_filename and
        scripts from kwargs if present."""
        # Remove template_file and scripts so that we don't get a duplicate
        # keyword exception
        kwargs.pop('template_filename', None)
        kwargs.pop('scripts', None)
    
    def __init__(self, env, template_filename, scripts=None, **kwargs):
        # env is pretty much a requirement for most widgets so for convenience,
        # I'm just saving it here
        self.env = env
        self.template_filename = template_filename
        
        # REFACT: self.data is quite a non obvious way to get data into the widgegs.
        # It would be way better for each widget to override the constructor and just set it's instance variables
        # That way we can also get nice exceptions if a widget is called with data it doesn't understand
        self.data = kwargs.copy()
        # Every widget instance needs to have a unique id so that you can have 
        # multiple graphs from the same widget on one page.
        self.data['unique_id'] = randint(0,1000000) # REFACT: shouldn't we use one of the UUID libraries here?
        
        self.scripts = scripts or list()
        self.rendering_prepared = False
    
    def copy(self):
        """Return a shallow copy of this widget (env will not be copied!)"""
        new_widget = self.__class__(self.env, template_filename=self.template_filename, 
                                    scripts=self.scripts, **self.data)
        return new_widget
    
    def update_data(self, *args, **kwargs):
        """Be careful when adding additional data after the widget was 
        generated - many widgets (actually all so far ;-) have a custom 
        initialization method that adds all necessary information given a 
        special key. This method is on a lower level so you may need to set 
        quite a lot of variables if you do it on your own."""
        if len(args) > 0:
            for item in args:
                assert isinstance(item, dict)
                self.data.update(item)
        self.data.update(kwargs)
    
    def _merge_data(self, data):
        real_data = self.data.copy()
        real_data.update(data)
        # in Trac 0.12 we need to provide this symbol for the templates
        real_data['_'] = _
        return real_data
    
    def prepare_rendering(self, req):
        """This method must be called before Trac started rendering the template
        so that we can add items to the global header."""
        for script_filename in self.scripts:
            add_script(req, script_filename)
        self.data['req'] = req
        self.rendering_prepared = True
    
    def _get_all_widget_template_directories(self):
        # AT: must be a real path not . or .. in eggs will not work
        trac_template_dirs = Chrome(self.env).get_all_templates_dirs()
        template_directories = [resource_filename('agilo', '')] + trac_template_dirs
        return template_directories
    
    def _assert_rendering_was_prepared(self):
        if len(self.scripts)> 0:
            assert self.rendering_prepared, 'You have to prepare_rendering before you can display things.'
    
    def display(self, **kwargs):
        """Return the HTML code for the given widget."""
        self._assert_rendering_was_prepared()
        templateloader = TemplateLoader(self._get_all_widget_template_directories(),
                                        auto_reload=True, variable_lookup='lenient')
        template = templateloader.load(self.template_filename, cls=MarkupTemplate)
        template_data = self._merge_data(kwargs)
        return template.generate(**template_data)
    
    def transform_to_js_ready_dict(self, data):
        return data
    
    def json_data(self):
        return self._merge_data(dict())
    
    def data_as_json(self):
        "Returns a json dict containing all data needed to render the widget"
        self._assert_rendering_was_prepared()
        json_data = self.json_data()
        return self.transform_to_js_ready_dict(json_data)


