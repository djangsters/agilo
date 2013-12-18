#!/usr/bin/env python
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
#   Authors:
#       - Felix Schwarz <felix.schwarz__at__agile42.com>

import locale
import os
import shutil
import sys

import pkg_resources
from trac import __version__ as VERSION
from trac.admin.console import copytree, printout, TracAdmin, run
from trac.core import TracError
from trac.util.translation import _

# -----------------------------------------------------------------------------
# Copied from trac 0.11.6dev with my patches from #8622 so that the deploy 
# command can handle multiple htdocs directories with the same prefix:
#    http://trac.edgewall.org/ticket/8622

def makedirs(path, overwrite=False):
    if overwrite and os.path.exists(path):
        return
    os.makedirs(path)

def copytree(src, dst, symlinks=False, skip=[], overwrite=True):
    """Recursively copy a directory tree using copy2() (from shutil.copytree.)

    Added a `skip` parameter consisting of absolute paths
    which we don't want to copy.
    """
    def str_path(path):
        if isinstance(path, unicode):
            path = path.encode(sys.getfilesystemencoding() or
                               locale.getpreferredencoding())
        return path
    skip = [str_path(f) for f in skip]
    def copytree_rec(src, dst):
        names = os.listdir(src)
        makedirs(dst, overwrite=overwrite)
        errors = []
        for name in names:
            srcname = os.path.join(src, name)
            if srcname in skip:
                continue
            dstname = os.path.join(dst, name)
            try:
                if symlinks and os.path.islink(srcname):
                    linkto = os.readlink(srcname)
                    os.symlink(linkto, dstname)
                elif os.path.isdir(srcname):
                    copytree_rec(srcname, dstname)
                else:
                    shutil.copy2(srcname, dstname)
                # XXX What about devices, sockets etc.?
            except (IOError, OSError), why:
                errors.append((srcname, dstname, str(why)))
            # catch the Error from the recursive copytree so that we can
            # continue with other files
            except shutil.Error, err:
                errors.extend(err.args[0])
        try:
            shutil.copystat(src, dst)
        except WindowsError, why:
            pass # Ignore errors due to limited Windows copystat support
        except OSError, why:
            errors.append((src, dst, str(why)))
        if errors:
            raise shutil.Error(errors)
    copytree_rec(str_path(src), str_path(dst))

def do_deploy(self, line):
    argv = self.arg_tokenize(line)
    if not argv[0]:
        self.do_help('deploy')
        return

    target = os.path.normpath(argv[0])
    if os.path.exists(target):
        raise TracError('Destination already exists. Remove and retry.')
    chrome_target = os.path.join(target, 'htdocs')
    script_target = os.path.join(target, 'cgi-bin')

    # Copy static content
    os.makedirs(target)
    os.makedirs(chrome_target)
    from trac.web.chrome import Chrome
    env = self.env_open()
    printout(_("Copying resources from:"))
    for provider in Chrome(env).template_providers:
        paths = list(provider.get_htdocs_dirs())
        if not len(paths):
            continue
        printout('  %s.%s' % (provider.__module__, 
                              provider.__class__.__name__))
        for key, root in paths:
            source = os.path.normpath(root)
            printout('   ', source)
            if os.path.exists(source):
                dest = os.path.join(chrome_target, key)
                copytree(source, dest, overwrite=True)
    
    # Create and copy scripts
    os.makedirs(script_target)
    printout(_("Creating scripts."))
    data = {'env': env, 'executable': sys.executable}
    for script in ('cgi', 'fcgi', 'wsgi'):
        dest = os.path.join(script_target, 'trac.'+script)
        template = Chrome(env).load_template('deploy_trac.'+script, 'text')
        stream = template.generate(**data)
        out = open(dest, 'w')
        stream.render('text', out=out)
        out.close()
# -----------------------------------------------------------------------------


def do_monkey_patching():
    import trac.admin.console
    trac.admin.console.copytree = copytree
    TracAdmin.do_deploy = do_deploy

def run_trac_admin():
    pkg_resources.require('Trac==%s' % VERSION)
    sys.exit(run())

if __name__ == '__main__':
    do_monkey_patching()
    run_trac_admin()

