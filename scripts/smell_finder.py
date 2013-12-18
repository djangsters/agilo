#!/usr/bin/env python

import os
import re
import sys

rootdir = sys.argv[1]
pattern = 'print'
if len(sys.argv) >= 3:
    pattern = sys.argv[2]

convert_to_path_pattern = lambda path: os.sep + path + os.sep
ignore_patterns = map(convert_to_path_pattern, ('.svn', 'design', 'AgiloApp', 'scripts',))


def file_should_be_ignored(filename):
    for ignore_pattern in ignore_patterns:
        if ignore_pattern in filename:
            return True
    return False


regex = re.compile('^\s*%s' % pattern)
for root, dirs, files in os.walk(rootdir):
    for filename in files:
        fn = os.path.join(root, filename)
        if file_should_be_ignored(fn):
            continue
        for line in open(fn).readlines():
            if regex.search(line):
                print fn
                print '    ', line,


