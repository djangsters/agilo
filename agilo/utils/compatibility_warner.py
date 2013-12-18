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

from pkg_resources import resource_filename
from trac.core import Component, implements
from trac.util.translation import _
from trac.web.api import IRequestFilter
from trac.web.chrome import add_warning

from agilo.utils.version_check import VersionChecker

__all__ = ['WarnAboutIncompatibleEnvironment']



class WarnAboutIncompatibleEnvironment(Component):
    implements(IRequestFilter)
    
    def __init__(self):
        # try to minimize the performance penalty for every request - this
        # will not change anyway during the lifetime of this Component
        self._uses_incompatible_trac_version = VersionChecker().is_trac_incompatible_with_python()
        self._is_bad_path = PathNameChecker().is_bad_path()
        if self._uses_incompatible_trac_version:
            self.env.log.error(self._warn_message_about_old_trac())
        if self._is_bad_path:
            self.env.log.error(self._warn_message_about_unicode_path())
    
    # IRequestFilter methods
    
    def pre_process_request(self, req, handler):
        return handler
    
    def post_process_request(self, req, template, data, content_type):
        if self._uses_incompatible_trac_version:
            add_warning(req, self._warn_message_about_old_trac())
        if self._is_bad_path:
            add_warning(req, self._warn_message_about_unicode_path())
        return (template, data, content_type)
    
    # Internal methods
    
    def _warn_message_about_old_trac(self):
        checker = VersionChecker()
        msg = _('Your version of of trac (%s) is not compatible with your '
              'Python version (%s)') % (checker.trac_version(), checker.python_version())
        return msg
    
    def _warn_message_about_unicode_path(self):
        msg_template = _("Some parts of Agilo are loaded from a path (%s) that "
                         "contains non ascii characters which is unsupported by "
                         "Trac. Please move Agilo's installation directory "
                         "and/or the PYTHON_EGG_CACHE environment variable to "
                         "a different location.")
        return msg_template % repr(PathNameChecker().path())


class PathNameChecker(object):
    def __init__(self, path=None):
        self._path = path or self.standard_path()
    
    def is_bad_path(self):
        # os.listdir() - and therefore pkg_resources.resource_filename -doesn't 
        # always return unicode filenames - therefore many os.path operations 
        # will fail later.
        # => trac / Agilo can not run from within a path that contains non-ascii
        # characters which leads to UnicodeDecodeError when it tries to find 
        # templates / static resources.
        # fs/mh: To us it looks like there is no real solution, but at least we
        # try to warn the user.
        try:
            unicode(self._path)
            return False
        except:
            return True
    
    def standard_path(self):
        return resource_filename('agilo', 'ticket')
    
    def path(self):
        return self._path


