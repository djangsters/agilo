# -*- coding: utf8 -*-
#   Copyright 2009 agile42 GmbH All rights reserved
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
#        - Felix Schwarz <felix.schwarz__at__agile42.com>

from trac.core import Component, implements, TracError
from trac.db import DatabaseManager
from trac.env import IEnvironmentSetupParticipant
from trac.util.text import to_unicode
from trac.util.translation import _

__all__ = ['PluginEnvironmentSetup']


class PluginEnvironmentSetup(Component):
    
    abstract = True
    
    implements(IEnvironmentSetupParticipant)
    
    # --------------------------------------------------------------------------
    # Template methods
    
    def get_expected_db_version(self):
        "Return the DB version (as integer) which is need by the plugin "
        raise NotImplementedError()
    
    def get_package_name(self):
        "Return the package name where the upgrade scripts can be found."
        pkg_name = self.__module__.rsplit('.', 1)[0]
        return pkg_name + '.db.upgrades'
    
    def name(self):
        "Return the name of this plugin - like 'Trac' for the core Trac."
        raise NotImplementedError()
    name = property(name)
    
    # --------------------------------------------------------------------------
    # IEnvironmentSetupParticipant methods
    def environment_created(self):
        """Fill in default data when a new environment was created (this 
        implementation just sets the db version identifier)."""
        db, handle_ta = self.get_db_for_write()
        self.set_db_version(db)
        if handle_ta:
            db.commit()
    
    def environment_needs_upgrade(self, db=None):
        db = self.get_db_for_read(db)
        db_ver = self.get_db_version(db)
        expected_db_version = self.get_expected_db_version()
        if db_ver == expected_db_version:
            return False
        elif db_ver > expected_db_version:
            msg = _('Database newer than %s version (has version %s, is version %s)')
            raise TracError(msg % (self.name, db_ver, expected_db_version))
        return True
    
    def upgrade_environment(self, db=None):
        db, handle_ta = self.get_db_for_write(db)
        db_ver = self.get_db_version(db)
        if db_ver == 0:
            return self.environment_created()
        cursor = db.cursor()
        
        catched_exception = None
        try:
            successful_upgrade = self.run_upgrade_scripts(cursor, db_ver)
        except Exception, e:
            error_msg = _('Exception while upgrading %s database: %s')
            self.env.log.error(error_msg % (self.name, to_unicode(e)))
            successful_upgrade = False
            catched_exception = e
        
        if not successful_upgrade:
            # Trac never issues a rollback implicitely during the upgrade which
            # seems to be wrong.
            db.rollback()
            error_msg = _('Upgrading %s tables failed!') % self.name
            self.env.log.error(error_msg)
            if catched_exception:
                raise
        else:
            self.set_db_version(db)
            if handle_ta:
                db.commit()
            msg = _('Upgraded %s database version from %d to %d')
            expected_db_version = self.get_expected_db_version()
            self.env.log.info(msg % (self.name, db_ver, expected_db_version))
    
    # --------------------------------------------------------------------------
    # Custom utility methods
    
    def get_db_for_read(self, db=None):
        # The idea is that maybe in the future there is a different connection 
        # pool for read connections.
        if db == None:
            db = self.env.get_db_cnx()
        return db
    
    def get_db_for_write(self, db=None):
        handle_ta = False
        if db == None:
            db = self.env.get_db_cnx()
            handle_ta = True
        return (db, handle_ta)
    
    def _fetch_db_version(self, db, name):
        db_version = 0
        cursor = db.cursor()
        sql = "SELECT value FROM system WHERE name='%s' LIMIT 1" % name
        cursor.execute(sql)
        row = cursor.fetchone()
        if (row is not None) and (len(row) > 0):
            db_version = row[0]
        return db_version
    
    def get_db_version(self, db, name=None):
        """Return the DB version (0 if no version information was read). 
        If name was given, use this identifier instead of the value in 
        self.name.
        
        Specifying another name is useful if your plugin changed its name but 
        you need to check if an old version of your plugin is present."""
        name = name or self.name
        db_version = int(self._fetch_db_version(db, name))
        return db_version
    
    def run_upgrade_scripts(self, cursor, current_db_version):
        dbm = DatabaseManager(self.env)
        connector, args = dbm._get_connector()
        upgrade_was_successful = True
        expected_db_version = self.get_expected_db_version()
        for i in xrange(current_db_version + 1, expected_db_version + 1):
            name  = 'db%i' % i
            filename = '%s.py' % name
            try:
                pkg_name = self.get_package_name()
                upgrades = __import__(pkg_name, globals(), locals(), [name])
                script = getattr(upgrades, name)
            except AttributeError:
                msg = _('No upgrade module for version %(num)i (%(filename)s)')
                raise TracError(msg, num=i, filename=filename)
            upgrade_was_successful = script.do_upgrade(self.env, i, cursor, connector)
            if not upgrade_was_successful:
                msg = _('Upgrade script %s did not complete successfully')
                self.env.log.error(msg % filename)
                break
        return upgrade_was_successful
    
    def _insert_version_number(self, cursor, version):
        cursor.execute('INSERT INTO system (name, value) VALUES (%s, %s)', 
                       (self.name, version))
    
    def _update_version_number(self, cursor, version):
        cursor.execute('UPDATE system SET value=%s WHERE name=%s', 
                       (version, self.name))
    
    def set_db_version(self, db):
        """Write the DB version of this plugin to the db (or update an existing
        row if one already exist)."""
        cursor = db.cursor()
        latest_version = self.get_expected_db_version()
        was_upgrade = (self.get_db_version(db) > 0)
        if was_upgrade:
            self._update_version_number(cursor, latest_version)
        else:
            self._insert_version_number(cursor, latest_version)

