# -*- encoding: utf-8 -*-
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

__all__ = ['Point', 'Line']

# The idea here is that we want to calculate with lines and intersections
# instead of always having to code this by hand
# Which is why the lines can work with datetime objects as x

from datetime import timedelta

class Point(object):
    
    def __init__(self, x, y):
        "x: horizontal, y: vertical"
        self.x = x
        self.y = y
    
    @classmethod
    def from_tupple(cls, a_tupple):
        return cls(a_tupple[0], a_tupple[1])
    
    def __cmp__(self, other):
        if self.__class__ is not other.__class__:
            return -1
        is_equal = self.x == other.x and self.y == other.y
        if is_equal:
            return 0
        else:
            return -1
    
    def __repr__(self):
        return "Point(%s, %s)" % (self.x, self.y)
    

def force_float(a_value):
    if isinstance(a_value, float):
        return a_value
    if isinstance(a_value, int):
        return float(a_value)
    if isinstance(a_value, timedelta):
        return float(a_value.days * 24 * 60 * 60 * 1000 + a_value.seconds * 1000 + a_value.microseconds)
    else:
        raise ValueError("Type <%s> not yet supported" % a_value.__class__.__name__)

# Doesn't handle 90° slopes...
class Line(object):
    
    def __init__(self, point, slope):
        self.point = point
        self.slope = slope
    
    @classmethod
    def from_two_points(cls, first_point, second_point):
        x_delta = force_float(second_point.x - first_point.x)
        if x_delta == 0:
            slope = 0
        else:
            slope = (float(second_point.y) - first_point.y) / x_delta
        return cls(first_point, slope)
    
    @classmethod
    def from_two_tupples(cls, first_tupple, second_tupple):
        return cls.from_two_points(Point.from_tupple(first_tupple), Point.from_tupple(second_tupple))
    
    def y_from_x(self, x):
        x_offset = x - self.point.x
        y_offset = force_float(x_offset) * self.slope
        return self.point.y + y_offset
    
    def point_from_x(self, x):
        return Point(x, self.y_from_x(x))
    
