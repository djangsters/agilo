# -*- coding: utf-8 -*-
#   Copyright 2008 Agile42 GmbH - Andrea Tomasini
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
# Authors:
#     - Andrea Tomasini <andrea.tomasini__at__agile42.com>

import datetime
from decimal import Decimal
import re

from trac.util.translation import _
from trac.util import datefmt

from agilo.utils import Key
from agilo.utils.config import AgiloConfig


class BasePropertyRenderer(object):
    """
    A property renderer, it allows to render a ticket
    property, or whatever else, including HTML tags
    """
    def __init__(self, env, value):
        """Initialize with the given property name"""
        self.env = env
        # Need to set the empty string because Genshi is
        # trying to convert with unicode any value...
        if value in [None, '']:
            self.value = _(u'n.a.')
        else:
            self.value = value
        
    def render(self):
        """
        Returns the rendered property, in this case
        just return the property, if None returns the
        empty string.
        """
        return self.value
    
    def value_is_a_number(self):
        """Returns True if the current set value is a number"""
        if isinstance(self.value, basestring):
            return re.match(r'[0-9]+(?:\.[0-9]+)?', self.value) is not None
        return False
    
    def __call__(self):
        return self.render()

    __unicode__ = __str__ = __call__


class FloatPropertyRenderer(BasePropertyRenderer):
    """
    A renderer for float or other decimal type. 
    It rounds to 2 decimals.
    """
    def render(self):
        """Returns the property rendered to only 2 decimals"""
        if self.value_is_a_number():
            try:
                self.value = float(self.value)
            except ValueError:
                pass
        if isinstance(self.value, (float, Decimal)):
            self.value = round(self.value, 2)
        return str(self.value)


class TimePropertyRenderer(BasePropertyRenderer):
    """Represents a Renderer to show the estimated time data in the proper unit"""
    def render(self):
        """Returns the rendered property with a d or h"""
        if self.value_is_a_number() or isinstance(self.value, (float,int,Decimal)):
            if AgiloConfig(self.env).use_days:
                return u"%sd" % round(float(self.value), 2)
            else:
                return u"%sh" % round(float(self.value), 1)
        return self.value


class DatetimePropertyRenderer(BasePropertyRenderer):
    """
    Represents a renderer to show a datetime in a localized format, 
    it takes a timezone object as additional optional parameter in
    the constructor, if omitted it returns in the standard locale
    """
    def __init__(self, env, value, tzinfo=None):
        """Initialize with the timezone too"""
        super(DatetimePropertyRenderer, self).__init__(env, value)
        self.tzinfo = tzinfo
        
    def render(self):
        """Returns a formatted string representing the datetime"""
        if isinstance(self.value, (datetime.date, 
                                   datetime.datetime,
                                   datetime.time)):
            return datefmt.format_datetime(self.value, 
                                           tzinfo=self.tzinfo)
        return self.value


# add the type and the Renderer here 
class Renderer(object):
    """A factory returning Renderer based on the property value type"""
    renderers_by_property = {Key.REMAINING_TIME: TimePropertyRenderer,
                             Key.TOTAL_REMAINING_TIME: TimePropertyRenderer,
                             Key.ESTIMATED_TIME: TimePropertyRenderer,
                             Key.ESTIMATED_REMAINING_TIME: TimePropertyRenderer,
                             Key.COMMITMENT: TimePropertyRenderer,
                             Key.CAPACITY: TimePropertyRenderer}
    # less restrictive
    renderers_by_type = {float: FloatPropertyRenderer,
                         datetime.datetime: DatetimePropertyRenderer,
                         datetime.date: DatetimePropertyRenderer}
    
    def __init__(self, dbobj, property_name, env=None):
        self.env = env or getattr(dbobj, 'env', None)
        self.dbobj = dbobj
        self.name = property_name
    
    def get_renderer(self, key):
        """
        Returns the appropriate renderer for the given key, if not
        existing a specific property renderer
        """
        renderer = None
        if self.name in Renderer.renderers_by_property:
            renderer = Renderer.renderers_by_property[self.name]
        elif key in Renderer.renderers_by_type:
            renderer = Renderer.renderers_by_type[key]
        return renderer
    
    def render(self):
        """Returns the rendered Property"""
        try:
            value = self.dbobj[self.name]
        except TypeError:
            value = self.dbobj
        except KeyError:
            value = None
        renderer = self.get_renderer(type(value))
        if renderer is None:
            renderer = BasePropertyRenderer
        obj = renderer(self.env, value)
        return obj.render()
    
    def __call__(self):
        """Returns the rendered value"""
        return self.render()
    
    __str__ = __unicode__ = __call__


