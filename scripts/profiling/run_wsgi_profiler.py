#!/usr/bin/env python

import os
import sys
from wsgiref.simple_server import make_server

from repoze.profile.profiler import AccumulatingProfileMiddleware
import trac.web.main

if len(sys.argv) < 2:
    logfile_name = 'profiling.log'
else:
    logfile_name = sys.argv[1]

if len(sys.argv) < 3:
    trac_env_dir = os.environ['TRAC_ENV']
else:
    trac_env_dir = sys.argv[2]
assert os.path.isdir(trac_env_dir), 'Please point TRAC_ENV to the environment you want to profile'
os.environ['TRAC_ENV'] = trac_env_dir

app = trac.web.main.dispatch_request
middleware = AccumulatingProfileMiddleware(
               app,
               log_filename=logfile_name,
               discard_first_request=False,
               flush_at_shutdown=False,
               path='/profile'
              )

httpd = make_server('', 8011, middleware)
print "Serving on port 8011..."
httpd.serve_forever()

