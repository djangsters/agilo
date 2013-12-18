# -*- encoding: utf-8 -*-
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
#   
#   Author: 
#       - Felix Schwarz <felix.schwarz__at__agile42.com>

import twill
from twill.errors import TwillAssertionError
from trac.tests.functional import tc
import trac.tests.functional.better_twill
from trac.tests.functional.better_twill import twill_write_html

__all__ = []


# Copied over from trac, because nose wraps all testcases in an instance of it's 
# own test, so _testenv is not available anymore.
# REFACT: we could probably just create a stack frame of the form that this method
# expects and then call the original... That way we at least have less duplication.
def twill_write_html():
    """Write the current html to a file.  Name the file based on the
    current testcase.
    """
    import sys, os
    frame = sys._getframe()
    while frame:
        if frame.f_code.co_name in ('runTest', 'setUp', 'tearDown'):
            testcase = frame.f_locals['self']
            if hasattr(testcase, 'test'): testcase = testcase.test
            testname = testcase.__class__.__name__
            tracdir = testcase._testenv.tracdir
            break
        frame = frame.f_back
    else:
        # We didn't find a testcase in the stack, so we have no clue what's
        # going on.
        raise Exception("No testcase was found on the stack.  This was "
            "really not expected, and I don't know how to handle it.")

    filename = os.path.join(tracdir, 'log', "%s.html" % testname)
    html_file = open(filename, 'w')
    b = trac.tests.functional.better_twill.b
    html_file.write(b.get_html())
    html_file.close()

    return filename


try:
    from _mechanize_dist._mechanize import BrowserStateError
except ImportError:
    # in case you have an unbundled twill which does not ship its own, 
    # private mechanize (like Fedora's python-twill)
    from mechanize import BrowserStateError

def replacement_that_writes_html_on_error(original_twill_function):
    def closure(*args, **kwargs):
        try:
            original_twill_function(*args, **kwargs)
        except (BrowserStateError, TwillAssertionError), e:
            filename = twill_write_html()
            if e.args[-1] == filename:
                raise
            args = e.args + (filename,)
            # REFACT: use only raise?
            raise twill.errors.TwillAssertionError(*args)
    return closure

tc.code = replacement_that_writes_html_on_error(tc.code)
tc.title = replacement_that_writes_html_on_error(tc.title)
tc.follow = replacement_that_writes_html_on_error(tc.follow)

# tidy (even in with the latest version in Fedora 9 which is 
# '0.99.0-17.20070615.fc9') manipulates the HTML source code so that empty 
# options ('<option></option>') will be removed completely. That affects our
# unit tests because you get always a sprint set etc.
# So we have to make sure that tidy is not used at all. We add this to 
# _orig_options so that the value is added again as soon as the browser is 
# reset without special action on our side.
#
# Actually the trac guys found the problem too (#5497) but they only added it to
# the options which are lost after a reset_browser.
twill.commands._orig_options['use_tidy'] = False
# ------------------------------------------------------------------------------

# tc.fv is just a shortcut to formvalue - but its initialized before better_twill
# monkey-patches it - so we have to do it ourselves (see #8331)
tc.fv = tc.formvalue

# ------------------------------------------------------------------------------
# Taken from trac (http://trac.edgewall.org/changeset/7606) so that we don't 
# have to patch our local trac installations.
class _BrowserProxy(object):
    def __getattribute__(self, name):
        return getattr(twill.get_browser(), name)
    
    def __setattr(self, name, value):
        setattr(twill.get_browser(), name, value)

trac.tests.functional.better_twill.b = _BrowserProxy()
# ------------------------------------------------------------------------------

