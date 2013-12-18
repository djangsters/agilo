#!/usr/bin/env python
"""This script checks that the egg really contains all necessary files (nothing
was forgotten in setup.py"""

import glob
from optparse import OptionParser
import os
import setuptools
import shutil
import subprocess
import sys
import zipfile

def make_clean():
    for filename in glob.glob('dist/*.egg'):
        os.unlink(filename)
    if os.path.exists('build/lib'):
        shutil.rmtree('build/lib')
    for filename in glob.glob('build/bdist*'):
        shutil.rmtree(filename)

def make_egg():
    python = sys.executable
    subprocess.call([python, 'setup.py', 'bdist_egg'])

def get_created_egg():
    eggs = glob.glob('dist/*.egg')
    if len(eggs) == 0:
        print 'No eggs in dist/ -- please use --build-egg'
    elif len(eggs) > 1:
        print 'Too many eggs in dist/'
    if len(eggs) != 1:
        sys.exit(1)
    eggfile = zipfile.ZipFile(eggs[0])
    return eggfile

def make_relative_name(topdir, filename):
    assert filename.startswith(topdir)
    relative_filename = filename[len(topdir):]
    if relative_filename.startswith(os.sep):
        relative_filename = relative_filename[len(os.sep):]
    return relative_filename

def file_is_only_interesting_for_developers(filename):
    exclusions = ['setup.', 'build', 'tests', 'functional_tests', 'scripts',
                  'CHANGES']
    for exclusion in exclusions:
        if filename.startswith(exclusion):
            return True
    return False

def check_if_egg_is_complete(eggfile):
    egg_items = eggfile.namelist()
    this_dir = os.path.abspath('.')
    
    for filename in setuptools.command.sdist.walk_revctrl(this_dir):
        filename = make_relative_name(this_dir, filename)
        if not file_is_only_interesting_for_developers(filename):
            if filename not in egg_items:
                print 'name not there ', filename


def get_parameters():
    parser = OptionParser()
    parser.add_option("--build-egg", action="store_true", dest="build_egg",
                      default=False, help="clean dist folder an build a new egg")
    (options, args) = parser.parse_args()
    if len(args) == 0:
        topdir = os.getcwd()
    else:
        topdir = args[0]
    return (options.build_egg, topdir)

def main():
    build_egg, topdir = get_parameters()
    os.chdir(topdir)
    if build_egg:
        make_clean()
        make_egg()
    eggfile = get_created_egg()
    check_if_egg_is_complete(eggfile)


if __name__ == '__main__':
    main()


