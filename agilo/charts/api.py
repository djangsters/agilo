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
#
#   Authors:
#        - Felix Schwarz <felix.schwarz__at__agile42.com>

from trac.core import Interface

__all__ = ['IAgiloWidgetGenerator']


class IAgiloWidgetGenerator(Interface):
    """Every widget generator can generate widgets for one or more charts.
    
    Why WidgetGenerators and Widgets are separate objects?
    - I wanted to have loose coupling with minimal knowlegde which widgets are
      available. Therefore we need to use Interfaces which requires Components.
    - One widget can exist in multiple instances at the same time because they 
      contain different data (e.g. sprint backlog widgets for different 
      sprints). Implementing this inside of a component (Singleton per 
      environment (would be quite hard.
    - It's much easier for caching if there is a kind of 'data object'.
    """
    
    def can_generate_widget(name):
        """Returns True if this WidgetGenerator can generate a widget for the
        given chart type."""
    
    def generate_widget(name, **kwargs):
        """Generate a widget with the given name. All data for this widget is
        in kwargs (it will be fed to the widget directly after the generation
        but the WidgetGenerator may decide to pick out some values and 
        initialize the widget already before returning it."""
    
    def get_cache_components(keys):
        """Return a tuple of which parameter names should go into the cache_key.
        @keys is an iterable with the names of the current parameters (some 
        generators may decide to have a variable number of caching components). 
        Default cache_key is (name, sprint_name).
        
        This method is optional, an implementor is not required to have it.
        """
    
    def get_backlog_information():
        """Returns a dict of widget name -> tuple of BacklogTypes 
        (agilo.scrum.backlog) which specify for which type of backlogs the 
        widgets can be used.
        
        This method is optional, an implementor is not required to have it 
        (especially widgets that are not locaed below agilo.scrum will probably
        don't have it).
        """

