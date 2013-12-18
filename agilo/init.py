# -*- coding: utf8 -*-
#   Copyright 2007 Andrea Tomasini <andrea.tomasini_at_agile42.com>
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
#   Authors:
#            - Andrea Tomasini <andrea.tomasini__at__agile42.com>

from trac.core import Component, ExtensionPoint, implements, Interface, TracError
from trac.util.translation import _

from agilo.api.web_ui import HttpRequestCacheManager
from agilo.config import __CONFIG_PROPERTIES__
from agilo.core import PersistentObject, PersistentObjectManager
from agilo.utils.db import create_table
from agilo.utils.log import info
from agilo.utils.config import initialize_config, AgiloConfig

from agilo.db import db_default, PluginEnvironmentSetup

__all__ = ['AgiloInit', 'IAgiloEnvironmentSetupListener']


class IAgiloEnvironmentSetupListener(Interface):
    def agilo_was_installed(self):
        """Called when Agilo was installed."""
        pass


class EmailVerificationDisabler(Component):
    """Disable EmailVerificationModule from AccountManager when Agilo is 
    installed (unless it was explicitely enabled). 
    
    The verification module has a very confusing behavior (if you add an email 
    address in your preferences, you loose all your privileges until you 
    verified your email address). We got a number of user requests and 
    hopefully this will save us some hassle."""
    implements(IAgiloEnvironmentSetupListener)
    
    def name_emailverificationmodule(self):
        return 'acct_mgr.web_ui.emailverificationmodule'
    
    def was_email_verification_enabled_explicitely(self, components):
        return components.get_bool(self.name_emailverificationmodule(), default=False)
    
    def agilo_was_installed(self):
        try:
            from acct_mgr.web_ui import EmailVerificationModule
        except ImportError:
            return
        if not self.env.is_component_enabled(EmailVerificationModule):
            return
        
        components = AgiloConfig(self.env).get_section('components')
        if self.was_email_verification_enabled_explicitely(components):
            return
        components.change_option(self.name_emailverificationmodule(), 'disabled')
        components.save()


class AgiloInit(PluginEnvironmentSetup):
    """ Initialize database and environment for link component """
    
    setup_listeners = ExtensionPoint(IAgiloEnvironmentSetupListener)
    
    # PluginEnvironmentSetup template methods
    
    def get_db_version(self, db):
        """Returns the normalized db version (integer). This method can convert 
        the decimal numbers from Agilo 0.6 to integer."""
        fetch_version = super(AgiloInit, self)._fetch_db_version
        db_version = fetch_version(db, self.name)
        if db_version == 0:
            # Agilo versions before 0.7 had different database versions with
            # floating point
            old_version = fetch_version(db, name='agilo-types')
            if old_version == '1.2':
                db_version = 1
            elif old_version != 0:
                msg = _('Unknown version for agilo-types: %s') % old_version
                raise TracError(msg)
        elif db_version == '0.7':
            db_version = 2
        # 'Modern' Agilo versions like 0.7 just return something like '3'.
        db_version = int(db_version)
        return db_version
    
    def get_package_name(self):
        return 'agilo.db.upgrades'
    
    def get_expected_db_version(self):
        return db_default.db_version
    
    def name(self):
        # Do not modify this because it is used in the DB!
        return 'agilo'
    name = property(name)
    
    def set_db_version(self, db):
        cursor = db.cursor()
        latest_version = self.get_expected_db_version()
        # If there is an update from 0.6 -> 0.7 we have a version number 1 but
        # 'agilo' does not exist in the DB.
        was_upgrade = (self.get_db_version(db) > 1)
        if was_upgrade:
            self._update_version_number(cursor, latest_version)
        else:
            self._insert_version_number(cursor, latest_version)
    
    #==========================================================================
    # IEnvironmentSetupParticipant
    #==========================================================================
    def environment_created(self):
        for table in db_default.schema:
            create_table(self.env, table)
        
        cache_manager = HttpRequestCacheManager(self.env)
        po_manager = PersistentObjectManager(self.env)
        for manager in cache_manager.managers:
            model_class = manager.for_model()
            if issubclass(model_class, PersistentObject):
                module_name = model_class.__module__
                # We don't want to create tables for dummy classes automatically
                # but the test finder may load some of these managers so we
                # need to exclude them here.
                if ('tests.' not in module_name):
                    po_manager.create_table(model_class)
        
        # Need to create Agilo types in the database before writing to the 
        # configuration - otherwise we get a warning during config setup (you'll
        # see it in every test case during setUp)
        db_default.create_default_types(self.env)
        initialize_config(self.env, __CONFIG_PROPERTIES__)
        db_default.create_default_backlogs(self.env)
        super(AgiloInit, self).environment_created()
        for listener in self.setup_listeners:
            listener.agilo_was_installed()
        # Reload the AgiloConfig to make sure all the changes have been updated
        AgiloConfig(self.env).reload()
        info(self, 'Agilo environment initialized')

