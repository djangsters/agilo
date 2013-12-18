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


from datetime import timedelta

from agilo.test import AgiloTestCase
from agilo.utils.days_time import now
from agilo.utils.geometry import Line, Point

class GeometryTest(AgiloTestCase):
    
    def test_can_instantiate_point(self):
        point = Point(3, 5)
        self.assert_equals(point.x, 3)
        self.assert_equals(point.y, 5)
    
    def test_can_instantiate_line(self):
        point = Point(0,0)
        line = Line(point, 1)
        self.assert_equals(point, line.point)
        self.assert_equals(1, line.slope)
    
    def test_can_instantiate_line_with_two_points(self):
        first = Point(1, 1)
        second = Point(21, 11)
        actual = Line.from_two_points(first, second)
        self.assert_equals(first, actual.point)
        self.assert_almost_equals(0.5, actual.slope, max_delta=0.001)
    
    def test_can_compute_arbitrary_y_from_given_x(self):
        line = Line(Point(20,10), 2)
        self.assert_equals(10, line.y_from_x(20))
        self.assert_equals(30, line.y_from_x(30))
        self.assert_equals(50, line.y_from_x(40))
    
    def test_can_compute_point_at_given_y(self):
        line = Line(Point(20,10), 2)
        self.assert_equals(Point(20,10), line.point_from_x(20))
        self.assert_equals(Point(30,30), line.point_from_x(30))
        self.assert_equals(Point(40,50), line.point_from_x(40))
    
    def test_can_compute_ys_when_points_have_datetimes_as_x(self):
        two_days_ago = now() - timedelta(days=2)
        one_day_ago = now() - timedelta(days=1)
        line = Line.from_two_points(Point(two_days_ago, 1), Point(one_day_ago, 2))
        self.assert_almost_equals(3, line.y_from_x(now()), max_delta=0.1)
    
    def test_can_compute_points_with_datetimes(self):
        two_days_ago = now() - timedelta(days=2)
        one_day_ago = now() - timedelta(days=1)
        today = now()
        line = Line.from_two_points(Point(two_days_ago, 1), Point(one_day_ago, 2))
        expected = Point(today, 3)
        actual = line.point_from_x(today)
        self.assert_equals(expected.x, actual.x)
        self.assert_almost_equals(expected.y, actual.y, max_delta=0.1)
    
    def test_can_initialize_point_from_tupple(self):
        expected = Point(2,3)
        actual = Point.from_tupple((2,3))
        self.assert_equals(expected, actual)
    
    def test_can_initialize_line_from_two_tupples(self):
        line = Line.from_two_tupples((0,0), (1,1))
        self.assert_equals(Point(0,0), line.point)
        self.assert_equals(1, line.slope)
    
    def test_can_create_line_with_no_slope_from_points(self):
        line = Line.from_two_tupples((0,0), (0,10))
        self.assert_equals(0, line.slope)


# TODO: make sure points can be instructed with times and floats