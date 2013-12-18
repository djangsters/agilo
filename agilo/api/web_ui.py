#   Copyright 2007 Andrea Tomasini <andrea.tomasini__at__agile42.com>
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
#        - Andrea Tomasini <andrea.tomasini__at__agile42.com>

from trac.core import Component, implements, ExtensionPoint
from trac.web.api import IRequestFilter

from agilo.api import IModelManager


class HttpRequestCacheManager(Component):
    """
    Implement object identity caching per HTTP Request so that an object
    will be loaded only once per HTTP Request
    """
    implements(IRequestFilter)
    
    managers = ExtensionPoint(IModelManager)
    
    def _reset_thread_local_cache(self):
        """
        Reset the thread local cache for the current Thread, to avoid
        that Thread re-usage in an HTTP server will access old cached data
        """
        for manager in self.managers:
            manager.get_cache().invalidate()
    
    def pre_process_request(self, req, handler):
        """Called after initial handler selection, and can be used to change
        the selected handler or redirect request.
        
        Always returns the request handler, even if unchanged.
        """
        self._reset_thread_local_cache()
        return handler
    
    def post_process_request(self, req, template, data, content_type):
        """Do any post-processing the request might need; typically adding
        values to the template `data` dictionary, or changing template or
        mime type.
        
        `data` may be update in place.

        Always returns a tuple of (template, data, content_type), even if
        unchanged.

        Note that `template`, `data`, `content_type` will be `None` if:
         - called when processing an error page
         - the default request handler did not return any result

        (Since 0.11)
        """
        return (template, data, content_type)
