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
#   Author: Andrea Tomasini <andrea.tomasini_at_agile42.com>


# Definition for Sorting
class SortOrder(object):
    ASCENDING = False
    DESCENDING = True
    

def _convert(elem):
    """Converts items into comparable types"""
    if elem is not None and isinstance(elem, basestring):
        if elem.isdigit():
            return int(elem)
        elif (elem.replace('.', '').isdigit() or \
              elem.replace(',','').isdigit()):
            return float(elem)
    return elem

def By(accessor, desc=SortOrder.ASCENDING, should_put_none_at_end=True):
    """
    Closure to build a comparator function generically using accessors and
    Attribute and Columns.
    """
    def _cmp_type(elem1, elem2):
        """Compares, but if none return 1"""
        #print "Compares: %s(%s) <=> %s(%s)" % (elem1, type(elem1), elem2, type(elem2))
        if type(elem1) == type(elem2) or \
                (isinstance(elem1, basestring) and \
                 isinstance(elem2, basestring)):
            return cmp(elem1, elem2)
        elif elem2 in (None, ''):
            return desc and 1 or -1
        elif elem1 in (None, ''):
            return desc and -1 or 1
        else:
            raise ValueError("Elements are not comparable")
        
    def compare(left, right):
        if desc:
            return _cmp_type(accessor(right), accessor(left))
        else: 
            return _cmp_type(accessor(left), accessor(right))
    return compare
    
def Attribute(name):
    """Attribute on the Object to check for"""
    def get(obj):
        value = _convert(getattr(obj, name))
        return value
    return get

def Column(key):
    """Column, or index accessor for a list or dictionary"""
    def get(obj):
        try:
            value = _convert(obj[key])
            return value
        except KeyError:
            return None
    return get
    
def Method(name, params):
    """Method call on the object, with parameters dictionary"""
    def get(obj):
        if hasattr(obj, name) and callable(getattr(obj, name)):
            value = _convert(getattr(obj, name)(**params))
            return value
    return get
