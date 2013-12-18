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

from cStringIO import StringIO
from datetime import datetime
from traceback import print_exc

# When VERBOSE is True and EnvironmentStub is used, convert the debug print
# into normal print to the console... can be annoying
VERBOSE = False
COMMANDS = False


def logger(severity, component, message, stdout=False):
    """
    Logs a message at the given severity, using the component
    instance passed as component to extract the logger and other
    useful information.
    """
    logger = getattr(component, 'log', None)
    if logger is None:
        logger = component.env.log
    # we have to log as str (not unicode) because the some exceptions may come
    # from lower level components (e.g. postgres) with the system encoding.
    if isinstance(message, unicode):
        message = message.encode('UTF-8')
    logformat = "[%s]: %s" % (component.__class__.__name__, message)
    try:
        logformat = "%s %s" % (component._DEBUG, message)
    except:
        pass
    if VERBOSE or stdout:
        # AT: it is not always allowed to print out unicode character to the
        # console, apparently it depends from the character encoding and the
        # python locale settings, so we use repr to print the log
        print ">>> @%s %s" % (datetime.now().time(), repr(logformat))
    elif severity == 'debug':
        # Avoid circular import
        from agilo.utils.command import CommandParser
        if not isinstance(component, CommandParser) or COMMANDS:
            logger.debug(logformat)
    elif severity == 'warning':
        logger.warning(logformat)
    elif severity == 'error':
        logger.error(logformat)
    
def debug(component, message, stdout=False):
    """log a debug message"""
    logger('debug', component, message, stdout=stdout)
    
def info(component, message, stdout=False):
    """log an informational message"""
    logger('info', component, message, stdout=stdout)
    
def warning(component, message, stdout=False):
    """log a warning message"""
    logger('warning', component, message, stdout=stdout)
    
def error(component, message, stdout=False):
    """log an error message"""
    # In case of error print also the stacktrace
    stacktrace = StringIO()
    print_exc(file=stacktrace)
    emessage = "%s\n%s" % (message, stacktrace.getvalue())
    logger('error', component, emessage, stdout=stdout)


def print_http_req_info(component, req, stdout=False):
    """Printing HTTP Request info on log/debug"""
    http_request = """
============= REQUEST PARAMS =============
PATH_INFO: %s METHOD: %s
AUTHNAME: %s
PERMISSION: %s
=============== ARGUMENTS ================\n""" % \
    (req.path_info, req.method, 
     req.authname, req.perm.permissions())   
    for k, v in req.args.items():
        http_request += "PARAM: %s = %s\n" % (k, v)
    #http_request += ("HDF PARAMS: %s" % req.hdf)
    http_request += "=========== END REQUEST PARAMS ===========\n"
    # Now print it
    if stdout:
        print "[%s]: %s" % (component, http_request)
    logger('debug', component, http_request)
