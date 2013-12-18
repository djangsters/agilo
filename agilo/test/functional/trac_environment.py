# -*- coding: utf-8 -*-
#   Copyright 2008-2009 Agile42 GmbH, Berlin (Germany)
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
"""
This module contains functional test infrastructure to test trac projects.
"""

import errno
import locale
import os
import random
import signal
# For Python 2.3 you need this as an external module.
from subprocess import call, Popen, PIPE
import subprocess
import sys
from tempfile import mkdtemp
import time

try:
    from _mechanize_dist._mechanize import BrowserStateError
except ImportError:
    from mechanize._mechanize import BrowserStateError
from trac.db.api import _parse_db_str
from trac.env import open_environment
import trac.tests.functional
from trac.tests.functional import FunctionalTester
from trac.tests.functional.better_twill import tc, twill, ConnectError
from trac.tests.functional.compat import rmtree, close_fds

from agilo.test.functional.api import TestEnvironment
from agilo.ticket.api import AgiloTicketSystem

__all__ = ['TracFunctionalTestEnvironment']


class BetterTracFunctionalTester(FunctionalTester):
    def __init__(self, url, repo_url):
        self.url = url
        self.repo_url = repo_url
        self.ticketcount = 0
        # We don't want to connect to the server right now!
    
    def login(self, username):
        # When we use twill for different hosts, we need to reset the cookies -
        # otherwise twill does not honor the cookie expiry from trac and 
        # continues to send the old cookie.
        tc.clear_cookies()
        return super(BetterTracFunctionalTester, self).login(username)



class TracFunctionalTestEnvironment(TestEnvironment):
    """The test environment manages the creation and removal of real resources 
    (e.g. a trac environment, subversion repository).
    
    If you want to test software that is not part of Trac itself (e.g. Trac 
    plugins), you should subclass this environment and override the methods to 
    customize the behavior (template class pattern). The idea is that all 
    methods are small enough so that most customizations can be done without 
    duplicating/copying code from this class.
    
    The template class pattern was chosen - despite all its short comings - 
    because:
     - It is much closer to trac's initial TestEnvironment so the migration is
       easier.
     - We need to see which changes people need in their use cases before 
       implementing some strategies.
     - Introducing 5-6 different strategy/configuration objects to pass into
       a TracFunctionalTestEnvironment looked a bit like over-engineering to me.
    
    However, the API of the class may change. Be prepared for some changes.
    """
    
    def __init__(self, config):
        self.super()
        self.port = self.create_random_port_for_server()
        self.hostname = 'localhost'
        self.url = 'http://%s:%d' % (self.hostname, self.port)
        
        # This is the directory from which all external commands are launched
        # (this is important because all commands will use relative paths)
        self.command_cwd = self._get_trac_source_dirname()
        
        self.repo_type = self.get_repo_type()
        self.use_single_env = True
        self.use_basic_auth = True
        
        self.dirname = None
        # tracdir in trac's testsuite - using envdir to not confuse with source 
        # location
        self._db_url = None
        self.envdir = None
        self.logfile = None
        self.pid = None
        self.repo_url = None
        self.tester = None
        locale.setlocale(locale.LC_ALL, '')
    
    # -------------------------------------------------------------------------
    # Configuration parameters
    # 
    # This section contains methods which you can use to 'configure' the 
    # behavior. The signature of these methods will probably stay the same.
    
    def create_random_port_for_server(self):
        return (8000 + random.randint(0, 1000))
    
    def create_tempdir(self, port):
        """Create a directory which will contain all temporary files and
        directories we create in this test environment  (e.g. for the trac 
        environment) and return its name."""
        container_dirname = mkdtemp(prefix='trac_testenv%d_' % port)
        dirname = os.path.join(container_dirname, self.get_key())
        os.mkdir(dirname)
        return dirname
    
    def get_repo_url(self):
        """Returns the url of the Subversion repository for this test
        environment.
        """
        if self._running_on_windows():
            repo_url = 'file:///' + self.repodir.replace("\\", "/")
        else:
            repo_url = 'file://' + self.repodir
        return repo_url
    
    def get_repo_type(self):
        return 'svn'
    
    def get_enabled_components(self):
        """Return a list of components which should be enabled in trac's 
        configuration (this is done after the initial trac environment was 
        created)."""
        return []
    
    def get_disabled_components(self):
        """Return a list of components which should be disabled in trac's 
        configuration (this is done after the initial trac environment was 
        created)."""
        return []
    
    def get_config_options(self):
        """Return a list of tripels (section, option, value) with additional 
        configuration options (this is done after the initial trac environment 
        was created) """
        return [('logging', 'log_type', 'file')]
    
    def _generate_db_url(self):
        # Choose the db string according to the db you want to test.
        # Please note that you have to ensure that the chosen database is empty
        # db_url = 'postgres://trac:trac@localhost/trac'
        # db_url = 'mysql://localhost/trac'
        if self.config() is None or self.config().db().scheme == 'sqlite':
            import os
            return os.path.join('sqlite:%s'% self.tracdir,'db','trac.db')

        db = self.config().db()
        db_url = db.scheme + '://'
        if db.user:
            db_url += db.user
            if db.password:
                db_url += ':' + db.password
            db_url += '@'

        # In mysql>5.6 dash causes problems, so it is better to remove it
        db_url += db.host + '/' + 'trac%d' % random.randint(0,1000)
        if self.config().db().scheme == 'postgres':
            db_url += "?schema=tractest"
        return db_url
    
    def get_db_url(self):
        """Return the db_url which will be put inside trac's configuration."""
        if not self._db_url:
            self._db_url = self._generate_db_url()
        return self._db_url
    
    def get_users_and_permissions(self):
        """Return a list with either usernames as string or tupels (username, 
        list of permissions, [password]). If no password was given, it will be
        the same as the username"""
        return [('admin', ['TRAC_ADMIN']), 'user']
    
    # -------------------------------------------------------------------------
    # Convenience methods?
    
    def _get_trac_source_dirname(self):
        return trac.tests.functional.trac_source_tree
    
    def _running_on_windows(self):
        return (os.name == 'nt')
    
    def get_trac_environment(self):
        """Returns a Trac environment object"""
        return open_environment(self.envdir, use_cache=True)
    
    def tracini_filename(self):
        return os.path.join(self.envdir, 'conf', 'trac.ini')
    
    def build_tester(self):
        """Return a Tester"""
        return BetterTracFunctionalTester(self.url, self.repo_url)
    
    def _ensure_web_access_is_working(self):
        timeout = 30
        while timeout:
            try:
                tc.go(self.url)
                break
            except (ConnectError, BrowserStateError):
                time.sleep(1)
            timeout -= 1
        else:
            raise Exception('Timed out waiting for server to start.')
        tc.url(self.url)
    
    def get_log_dir(self):
        return os.path.join(self.envdir, 'log')
    
    
    # -------------------------------------------------------------------------
    # Interface methods from the TestEnvironment
    
    def environment_information(self):
        return '%s: %s' % (self.get_key(), self.envdir)
    
    def create(self):
        if self.super():
            self.dirname = self.create_tempdir(self.port)
            self.repodir = os.path.join(self.dirname, "repo")
            # Don't use the 'trac' for the environment dir - otherwise it is
            # pretty hard to make a multi-environment configuration where the
            # last part of the directory must be unique.
            self.envdir = os.path.join(self.dirname, self.get_key())
            self.htpasswd = os.path.join(self.dirname, "htpasswd")
            self.repo_url = self.get_repo_url()
            # backwards compatibility with better_twill
            self.tracdir = self.envdir
            
            self._setup_logging()
            self._create_repository(self.repo_type, self.repodir)
            self._create_environment(self.envdir, self.get_db_url(), 
                                     self.repo_type, self.repodir)
            self._upgrade_environment()
            self._setup_users_and_permissions()
            return True
        return False
    
    def _destroy_database(self, db_url):
        if self._is_sqlite_db(db_url):
            return
        if self._is_postgres_db(db_url):
            self._run_postgres_db_command('dropdb', db_url)
        elif self._is_mysql_db(db_url):
            self._run_mysql_db_command('drop', db_url)
    
    def destroy(self):
        self._shutdown_environment()
        self._destroy_database(self.get_db_url())
        if os.path.exists(self.dirname):
            for i in range(5):
                try:
                    rmtree(self.dirname)
                    break
                except OSError:
                    # The idea is that sometimes we need to wait for a short
                    # time until all file handles are closed (e.g. tracd is
                    # really shut down) so that we can delete the files on
                    # Windows.
                    time.sleep(0.5)
    
    def start(self):
        """Starts the tracd server"""
        if self.super():
            self.pid = self._start_standalone_tracd()
            self._ensure_web_access_is_working()
            self.tester = self.build_tester()
            return True
        return False
    
    def stop(self):
        """Stops the tracd server"""
        if self.super() and self.pid:
            if self._running_on_windows():
                call(["taskkill", "/f", "/pid", str(self.pid)],
                     stdin=PIPE, stdout=PIPE, stderr=PIPE)
            else:
                os.kill(self.pid, signal.SIGINT)
                try:
                    os.waitpid(self.pid, 0)
                except OSError, e:
                    if e.errno != errno.ESRCH:
                        raise
            return True
        return False
    
    def restart(self):
        self.stop()
        self.start()
    
    def get_key(cls):
        return 'trac_default'
    get_key = classmethod(get_key)
    # -------------------------------------------------------------------------
    
    # -------------------------------------------------------------------------
    # Wrappers for external methods
    
    def _tracadmin(self, *args):
        """Calls trac-admin via python module instead of external process call"""
        retval = call([sys.executable, "./trac/admin/console.py", self.envdir]
                      + list(args), stdout=self.logfile, stderr=self.logfile,
                      close_fds=close_fds, cwd=self.command_cwd)
        if retval:
            raise Exception('Failed with exitcode %s running trac-admin ' \
                            'with %r' % (retval, args))
    
    def _is_sqlite_db(self, db_url):
        return 'sqlite' == _parse_db_str(db_url)[0]
    
    def _is_postgres_db(self, db_url):
        return 'postgres' == _parse_db_str(db_url)[0]
    
    def _is_mysql_db(self, db_url):
        return 'mysql' == _parse_db_str(db_url)[0]
    
    def _db_info(self, db_url):
        return _parse_db_str(db_url)[1]
    
    def _run_postgres_db_command(self, command, db_url):
        db_info = self._db_info(db_url)
        environ = os.environ.copy()
        parameters = [command]
        if 'host' in db_info:
            parameters.append('--host=%s' % db_info['host'])
        if 'user' in db_info:
            parameters.append('--username=%s' % db_info['user'])
        if 'port' in db_info:
            parameters.append('--port=%s' % db_info['port'])
        if 'password' in db_info:
            environ['PGPASSWORD'] = str(db_info['password'])
        parameters.append(db_info['path'][1:])
        subprocess.check_call(parameters, env=environ, stderr=PIPE, close_fds=close_fds)
    
    def _run_mysql_db_command(self, command, db_url):
        db_info = self._db_info(db_url)
        environ = os.environ.copy()
        parameters = ['mysqladmin', command, '--force']
        if 'host' in db_info:
            parameters.append('--host=%s' % db_info['host'])
        if 'user' in db_info:
            parameters.append('--user=%s' % db_info['user'])
        if 'port' in db_info:
            parameters.append('--port=%s' % db_info['port'])
        if 'password' in db_info:
            parameters.append('--password=%s' % str(db_info['password']))
        parameters.append(db_info['path'][1:])
        subprocess.check_call(parameters, env=environ, stderr=self.logfile, close_fds=close_fds)
    
    def _create_database(self, db_url):
        if self._is_sqlite_db(db_url):
            return
        if self._is_postgres_db(db_url):
            db_info = self._db_info(db_url)
            if 'schema' in db_info['params']:
                schema = db_info['params'].get('schema')
                
            db_url = db_url.split("?")[0]                
            self._run_postgres_db_command('createdb', db_url)
        elif self._is_mysql_db(db_url):
            self._run_mysql_db_command('create', db_url)
    
    def _create_environment(self, env_dir, db_url, repo_type, repodir):
        if self._running_on_windows():
            # On Windows we need to double-escape backslashes - otherwise they 
            # will be used as escape characters when storing the config (repo 
            # dir in trac.ini won't contain any backslashes then).
            repodir = repodir.replace('\\', '\\\\')
        
        self._create_database(db_url)
        self._tracadmin('initenv', env_dir, db_url, repo_type, repodir)
        env = self.get_trac_environment()
        config = env.config
        for component in self.get_enabled_components():
            config.set('components', component, 'enabled')
        for component in self.get_disabled_components():
            config.set('components', component, 'disabled')
        for (section, name, value) in self.get_config_options():
            config.set(section, name, value)
        config.save()
        config.touch()
        if not AgiloTicketSystem(env).is_trac_012():
            env.shutdown()
    
    def _create_repository(self, repo_type, repodir):
        if repo_type != 'svn':
            raise NotImplementedError('Only svn repositories are implemented!')
        if call(["svnadmin", "create", repodir], stdout=self.logfile,
                stderr=self.logfile, close_fds=close_fds):
            raise Exception('unable to create subversion repository')
    
    def _create_user(self, username, password):
        flags = '-b'
        if not os.path.exists(self.htpasswd):
            flags += 'c'
        if call([sys.executable, './contrib/htpasswd.py', flags, self.htpasswd,
             username, password], close_fds=close_fds, cwd=self.command_cwd):
            raise Exception('Unable to setup password for user "%s"' % username)
    
    def _grant_permissions(self, username, permissions):
        "Grant the specified permissions the user (using trac-admin)."
        for perm in permissions:
            self._tracadmin('permission', 'add', username, perm)
    
    def _setup_user(self, username, permissions=None, password=None):
        if password is None:
            password = username
        self._create_user(username, password)
        if permissions is not None:
            self._grant_permissions(username, permissions)
    
    def _setup_users_and_permissions(self):
        """Create all configured users (in the authentication layer) and 
        grant the specified permissions to this account."""
        for item in self.get_users_and_permissions():
            password = None
            permissions = []
            if isinstance(item, basestring):
                username = item
            else:
                if len(item) == 2:
                    username, permissions = item
                else:
                    username, permissions, password = item
            self._setup_user(username, permissions=permissions, password=password)
    
    def _setup_logging(self):
        "Create the log files which capture output from subprocesses."
        self.logfile = open(os.path.join(self.dirname, 'testing.log'), 'a')
        twill_log = os.path.join(self.dirname, 'functional-testing.log')
        twill.set_output(open(twill_log, 'w'))
    
    def _shutdown_environment(self):
        # On Windows we can not remove the environment files if some file handles
        # are still open. Try to close as many of them as possible.
        if self.logfile:
            self.logfile.close()
        self.logfile = None
        if hasattr(tc, 'OUT'):
            tc.OUT.close()
    
    def _get_process_arguments(self):
        "Return a list of strings to use for starting the tracd."
        proc_args = ["./trac/web/standalone.py",
                     "--hostname=%s" % self.hostname, "--port=%s" % self.port]
        if self.use_single_env:
            proc_args.append('--single-env')
        if self.use_basic_auth:
            proc_args.append('--basic-auth=*,%s,' % (self.htpasswd))
        
        proc_args.append(self.envdir)
        return proc_args
    
    def _start_standalone_tracd(self):
        "Start a standalone tracd and return its pid."
        if 'FIGLEAF' in os.environ:
            exe = os.environ['FIGLEAF']
        else:
            exe = sys.executable
        proc_args = self._get_process_arguments()
        #print 'starting server', exe, ' '.join(proc_args)
        server = Popen([exe] + proc_args, stdout=self.logfile, 
                       stderr=self.logfile, close_fds=close_fds, 
                       cwd=self.command_cwd)
        return server.pid
    
    def _upgrade_environment(self):
        # Upgrading the environment is not necessary for trac but for all 
        # plugins which need to do some database modifications.
        # '--no-backup' is important if you don't use sqlite.
        self._tracadmin('upgrade', '--no-backup')
    
    
    # -------------------------------------------------------------------------

# Register this module with the EnvironmentBuilder
from agilo.test.functional.api import EnvironmentBuilder
EnvironmentBuilder.register_environment(TracFunctionalTestEnvironment.get_key(),
                                        TracFunctionalTestEnvironment)

