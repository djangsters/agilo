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
#   Author: Felix Schwarz <felix.schwarz__at__agile42.com>


from trac.core import Component, implements

from agilo.charts.api import IAgiloWidgetGenerator
from agilo.charts import ChartGenerator, FlotChartWidget
from agilo.scrum.sprint import SprintModelManager
from agilo.test import AgiloTestCase
from agilo.utils.days_time import now


class DummyWidget(FlotChartWidget):
    pass


class DummyChart(Component):
    implements(IAgiloWidgetGenerator)
    
    def __init__(self, *args, **kwargs):
        super(DummyChart, self).__init__(*args, **kwargs)
        self.reset_caching_components()
    
    def can_generate_widget(self, name):
        return (name == 'dummy')
    
    def get_cache_components(self, keys):
        return tuple(self.caching_components)
    
    def generate_widget(self, name, **kwargs):
        return DummyWidget(self.env, 'no_template', **kwargs)
    
    def reset_caching_components(self):
        self.caching_components = ['name']
    
    def set_caching_components(self, components):
        self.caching_components = components


class TestChartGenerator(AgiloTestCase):
    def setUp(self):
        self.super()
        self.chartgenerator = ChartGenerator(self.env)
        self.component_manager = self.chartgenerator.compmgr
        self.component_manager.enabled[DummyChart] = True
    
    def tearDown(self):
        # This should not be needed because we delete DummyChart from the
        # component manager (so it will create a new instance for the next test)
        # but better save than sorry.
        DummyChart(self.env).reset_caching_components()
        del self.component_manager.enabled[DummyChart]
        self.teh.cleanup()
        self.super()
    
    def test_find_widgetgenerators_with_extensionpoint(self):
        generated_widget = self.chartgenerator.get_chartwidget('dummy')
        self.assert_true(isinstance(generated_widget, DummyWidget))
    
    def test_dimensions_not_set_if_not_specified_by_user(self):
        """The idea is that every widget has its own default dimensions. 
        Therefore the ChartGenerator must not only the dimensions if the user
        specified them explicitely (either as parameter or in the 
        configuration)."""
        widget = self.chartgenerator.get_chartwidget('dummy')
        self.assert_false('width' in widget.data)
        self.assert_false('height' in widget.data)
    
    def test_can_have_two_widget_instances_with_different_parameters(self):
        w1 = self.chartgenerator.get_chartwidget('dummy', sprint_name='foo_sprint')
        w2 = self.chartgenerator.get_chartwidget('dummy', sprint_name='foo_sprint')
        
        w1.update_data(width=200, height=200)
        self._assert_not_equal_widget_data(w1, w2)
    
    def _clean_data(self, widget_a, widget_b, excluded_items):
        if excluded_items == None:
            excluded_items = list()
        data_a = widget_a.data.copy()
        data_b = widget_b.data.copy()
        
        for item in ['unique_id'] + excluded_items:
            data_a.pop(item, None)
            data_b.pop(item, None)
        return (data_a, data_b)
    
    def _assert_equal_widget_data(self, widget_a, widget_b, excluded_items=None):
        (data_a, data_b) = self._clean_data(widget_a, widget_b, excluded_items)
        self.assert_equals(data_a, data_b)
    
    def _assert_not_equal_widget_data(self, widget_a, widget_b, excluded_items=None):
        (data_a, data_b) = self._clean_data(widget_a, widget_b, excluded_items)
        self.assert_not_equals(data_a, data_b)
    
    def test_widgets_are_cached(self):
        # foobar must not be a cache key so we can check that the second widget
        # is really the cached one
        generated_widget = self.chartgenerator.get_chartwidget('dummy', foobar=43)
        second_widget = self.chartgenerator.get_chartwidget('dummy')
        self._assert_equal_widget_data(generated_widget, second_widget)
        self.assert_true('foobar' in second_widget.data)
        
        another_widget = self.chartgenerator.get_chartwidget('dummy', 
                                                             use_cache=False)
        self.assert_false('foobar' in another_widget.data)
    
    def test_complete_cache_can_be_invalidated_by_explicit_call(self):
        DummyChart(self.env).set_caching_components(['name', 'sprint_name'])
        # foobar is no cache key but sprint_name must be one
        w1 = self.chartgenerator.get_chartwidget('dummy', sprint_name='foo_sprint', foobar=42)
        w2 = self.chartgenerator.get_chartwidget('dummy', sprint_name='bar_sprint', foobar=17)
        self.chartgenerator.invalidate_cache()
        
        w1b = self.chartgenerator.get_chartwidget('dummy', sprint_name='foo_sprint')
        self._assert_not_equal_widget_data(w1, w1b)
        w2b = self.chartgenerator.get_chartwidget('dummy', sprint_name='bar_sprint')
        self._assert_not_equal_widget_data(w2, w2b)
    
    def test_per_sprint_cache_can_be_invalidated_by_explicit_call(self):
        DummyChart(self.env).set_caching_components(['name', 'sprint_name'])
        # foobar is no cache key but sprint_name must be one
        w1 = self.chartgenerator.get_chartwidget('dummy', sprint_name='foo_sprint', foobar=42)
        w2 = self.chartgenerator.get_chartwidget('dummy', sprint_name='bar_sprint', foobar=17)
        self.chartgenerator.invalidate_cache(sprint_name='foo_sprint')
        
        w1b = self.chartgenerator.get_chartwidget('dummy', sprint_name='foo_sprint')
        self._assert_not_equal_widget_data(w1, w1b)
        w2b = self.chartgenerator.get_chartwidget('dummy', sprint_name='bar_sprint')
        self._assert_equal_widget_data(w2, w2b)
    
    def test_pass_persistent_objects_to_invalidate_cache(self):
        sprint = self.teh.create_sprint(name="foo_sprint", start=now(), duration=10)

        DummyChart(self.env).set_caching_components(['name', 'sprint_name'])
        # foobar is no cache key but sprint_name must be one
        w1 = self.chartgenerator.get_chartwidget('dummy', sprint_name='foo_sprint', foobar=42)
        w2 = self.chartgenerator.get_chartwidget('dummy', sprint_name='bar_sprint', foobar=17)
        self.chartgenerator.invalidate_cache(sprint=sprint)
        
        w1b = self.chartgenerator.get_chartwidget('dummy', sprint_name='foo_sprint')
        self._assert_not_equal_widget_data(w1, w1b)
        w2b = self.chartgenerator.get_chartwidget('dummy', sprint_name='bar_sprint')
        self._assert_equal_widget_data(w2, w2b)
    
    def test_changing_widget_data_does_not_affect_cache(self):
        """Check that data from a widget can be changed afterwards without 
        affecting the cached version. This is essentially also a test that we
        can have multiple instances of the same widget with different data."""
        w1 = self.chartgenerator.get_chartwidget('dummy', sprint_name='foo_sprint')
        w1.update_data(width=200, height=200)
        w2 = self.chartgenerator.get_chartwidget('dummy', sprint_name='foo_sprint')
        
        self._assert_not_equal_widget_data(w1, w2)
    
    def test_generator_can_decide_about_caching_key(self):
        """Test that the generator can decide about what caching key should be 
        used given some parameters. That means that width/height might not be
        used as part of the caching key."""
        w1 = self.chartgenerator.get_chartwidget('dummy', bar=12, foobar=37)
        w2 = self.chartgenerator.get_chartwidget('dummy', bar=13)
        self.assert_equals(w1.data['foobar'], w2.data['foobar'])
        
        DummyChart(self.env).set_caching_components(['name', 'bar'])
        self.chartgenerator.get_chartwidget('dummy', bar=12, foobar=37)
        w2b = self.chartgenerator.get_chartwidget('dummy', bar=13)
        self.assert_false('foobar' in w2b.data)
    
    def test_generator_can_decide_not_to_cache(self):
        DummyChart(self.env).set_caching_components(['name', 'bar'])
        self.chartgenerator.get_chartwidget('dummy', foobar=37)
        w2 = self.chartgenerator.get_chartwidget('dummy')
        self.assert_false('foobar' in w2.data)
    
    def test_cached_widget_uses_own_size(self):
        # width, height and foobar are not used in the cache key
        w1 = self.chartgenerator.get_chartwidget('dummy', width=42, height=15, foobar=37)
        w2 = self.chartgenerator.get_chartwidget('dummy', width=84, height=30)
        
        self.assert_equals(37, w2.data['foobar'])
        self.assert_equals(84, w2.data['width'])
        self.assert_equals(30, w2.data['height'])
        
        self._assert_not_equal_widget_data(w1, w2)
    
    def test_cached_widget_gets_his_own_parameters(self):
        # foobar is not part of the cache key
        self.chartgenerator.get_chartwidget('dummy', foobar=37, bar=12)
        w2 = self.chartgenerator.get_chartwidget('dummy', foobar=38)
        self.assert_equals(12, w2.data['bar']) # This one is inherited from w1
        self.assert_equals(38, w2.data['foobar']) # This is the one from w2

