#   Copyright 2008 Agile42 GmbH, Berlin (Germany)
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
#   Author: 
#            - Felix Schwarz <felix.schwarz__at__agile42.com>

import warnings

# will be fixed in MySQLdb-python 1.2.3
# https://bugzilla.redhat.com/show_bug.cgi?id=505611
warnings.filterwarnings('ignore', '.*the sets module is deprecated.*', DeprecationWarning, 'MySQLdb')

# http://trac.edgewall.org/ticket/8160
warnings.filterwarnings('ignore', 'BaseException.message has been deprecated as of Python 2.6', DeprecationWarning, 'trac.core')

# This will not be fixed for Subversion 1.5 because upstream does not consider
# this a bug.
# http://subversion.tigris.org/ds/viewMessage.do?dsForumId=462&dsMessageId=1427466
# https://bugzilla.redhat.com/show_bug.cgi?id=487732
warnings.filterwarnings('ignore', 'BaseException.message has been deprecated as of Python 2.6', DeprecationWarning, 'svn.core')

# twill 0.9 includes an old mechanize version which in turn uses deprecated modules
# This will be fixed in twill 0.9.2 which however is incompatible with trac...
warnings.filterwarnings('ignore', 'the md5 module is deprecated')
warnings.filterwarnings('ignore', 'the sha module is deprecated')
