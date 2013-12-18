#   Copyright 2007 Andrea Tomasini <andrea.tomasini_at_agile42.com>
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


from agilo import AGILO_TABLE_PREFIX

LINKS_TABLE = AGILO_TABLE_PREFIX + 'link'
LINKS_URL = '/links'
LINKS_SEARCH_URL = '/search-links'


# Config file trac.ini special keywords
class LinkOption(object):
    ALLOW       = 'allow'
    CALCULATE   = 'calculate'
    COPY        = 'copy'
    SHOW        = 'show'
    SORT        = 'sort'
    DELETE      = 'delete'


from agilo.ticket.links.admin import *
from agilo.ticket.links.model import *
from agilo.ticket.links.search import *
from agilo.ticket.links.web_ui import *

