# -*- encoding: utf-8 -*-
#   Copyright 2009 Agile42 GmbH, Berlin (Germany)
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
#   Author: 
#       - Felix Schwarz <felix.schwarz_at_agile42.com>

from pkg_resources import resource_listdir, resource_isdir, resource_exists


def is_python_package(parent_pkg, name):
    try:
        pkg_name = '.'.join((parent_pkg, name))
        return (resource_exists(pkg_name, '__init__.py'))
    except ValueError:
        return False

def find_help_pages_below(parent_pkg, name):
    help_pages = []
    current_pkg = '.'.join((parent_pkg, name))
    for item in resource_listdir(parent_pkg, name):
        if ('.' not in item) and is_python_package(current_pkg, item):
            help_pages.extend(find_help_pages_below(current_pkg, item))
        elif item.endswith('.txt'):
            help_pages.append((current_pkg, item))
    return help_pages

def get_all_help_pages():
    return find_help_pages_below('agilo.help', 'contents')

