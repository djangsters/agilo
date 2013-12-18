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
#   Authors:
#       - Felix Schwarz <felix.schwarz__at__agile42.com>

from pkg_resources import Distribution, DistributionNotFound, FileMetadata, \
    get_distribution, Requirement, VersionConflict, WorkingSet
import sys


__all__ = ['VersionChecker']


class InMemoryMetadataStub(FileMetadata):
    
    def __init__(self, name='Baz', version='1.0'):
        self._name = name
        self._version = version
    
    def get_metadata(self, metadata_filename):
        return '''Metadata-Version: 1.0
Name: %s
Version: %s
Summary: Just a fake package
Author: Foo Bar
Author-email: foo@example.com
License: GPL
Description: UNKNOWN
Platform: UNKNOWN
''' % (self._name, self._version)


class VersionChecker(object):
    def __init__(self, python=None, trac=None):
        self._python = python
        self._trac = trac
    
    def python_version_tuple(self):
        if self._python is None:
            return sys.version_info[:3]
        # just for testing
        version_info = self._python.split('.')
        while len(version_info) < 3:
            version_info.append(0)
        return tuple(map(int, version_info))
    
    def python_version(self):
        return '.'.join(map(str, self.python_version_tuple()))
    
    def trac_version(self):
        if self._trac is None:
            return self.installed_version('trac')
        return self._trac
    
    def genshi_version(self):
        return self.installed_version('genshi')
    
    def setuptools_version(self):
        return self.installed_version('setuptools')
    
    def is_trac_compatible_with_python(self):
        if self.python_version_tuple() < (2, 6, 0):
            return True
        
        min_trac_version_for_python26 = Requirement.parse('trac >= 0.11.4')
        try:
            self._working_set().find(min_trac_version_for_python26)
            return True
        except VersionConflict:
            return False
    
    def is_trac_incompatible_with_python(self):
        return not self.is_trac_compatible_with_python()
    
    def installed_version(self, distribution_name):
        "Return None if the distribution_name is not found."
        try:
            return get_distribution(distribution_name).version
        except DistributionNotFound:
            return None
    
    def agilo_version(self):
        """Return the version of Agilo (or Agilo Pro), 'unknown' if neither 
        Agilo nor Agilo Pro are installed"""
        version = self.installed_version('agilo')
        if version is None:
            version = self.installed_version('binary-agilo')
        if version is None:
            version = 'unknown'
        return version
    
    def _working_set(self):
        trac_version = self.trac_version()
        metadata = InMemoryMetadataStub(name='trac', version=trac_version)
        trac_distribution = Distribution('/invalid/path', metadata, project_name='trac', version=trac_version)
        working_set = WorkingSet(entries=())
        working_set.add(trac_distribution)
        return working_set

    def print_version_info(self):
        """Prints out the version informations for Python and Trac"""
        info = """
Python:     %s
Trac:       %s
Genshi:     %s
Setuptools: %s
""" % (self.python_version(), self.trac_version(), self.genshi_version(),
       self.setuptools_version())
        print info


if __name__ == '__main__':
    VersionChecker().print_version_info()