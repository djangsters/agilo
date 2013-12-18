#!/usr/bin/env python

import pstats
import sys

if len(sys.argv) < 2:
    print 'Usage %s <filename>' % sys.argv[0]
    sys.exit(0)

filename = sys.argv[1]

s = pstats.Stats(filename)
s.sort_stats('time').print_stats(40)


