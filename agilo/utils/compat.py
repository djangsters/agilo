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
#       - Felix Schwarz <felix.schwarz__at__agile42.com>

from trac.web.href import Href
from trac.util.text import to_unicode

__all__ = ['add_link', 'add_stylesheet', 'exception_to_unicode', 'json']


try:
    from trac.util.text import exception_to_unicode
except ImportError:
    def exception_to_unicode(e, traceback=""):
        message = '%s: %s' % (e.__class__.__name__, to_unicode(e))
        if traceback:
            from trac.util import get_last_traceback
            traceback_only = get_last_traceback().split('\n')[:-2]
            message = '\n%s\n%s' % (to_unicode('\n'.join(traceback_only)), message)
        return message

# ------------------------------------------------------------------------------
# copied from trac 0.11.6 until #8881 is fixed.
def add_link(req, rel, href, title=None, mimetype=None, classname=None, **link_attributes):
    """Add a link to the chrome info that will be inserted as <link> element in
    the <head> of the generated HTML
    """
    linkid = '%s:%s' % (rel, href)
    linkset = req.chrome.setdefault('linkset', set())
    if linkid in linkset:
        return # Already added that link

    link = {'href': href, 'title': title, 'type': mimetype, 'class': classname}
    link.update(link_attributes)
    links = req.chrome.setdefault('links', {})
    links.setdefault(rel, []).append(link)
    linkset.add(linkid)

def add_stylesheet(req, filename, mimetype='text/css', media=None):
    """Add a link to a style sheet to the chrome info so that it gets included
    in the generated HTML page.
    
    If the filename is absolute (i.e. starts with a slash), the generated link
    will be based off the application root path. If it is relative, the link
    will be based off the `/chrome/` path.
    """
    if filename.startswith('common/') and 'htdocs_location' in req.chrome:
        href = Href(req.chrome['htdocs_location'])
        filename = filename[7:]
    else:
        href = req.href
        if not filename.startswith('/'):
            href = href.chrome
    # The media parameter may be passed to the template even for media=None
    # because Genshi will not add the attribute if its value is None
    add_link(req, 'stylesheet', href(filename), mimetype=mimetype, media=media)
# ------------------------------------------------------------------------------


try:
    import json
except ImportError:
    import simplejson as json

