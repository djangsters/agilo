# -*- encoding: utf-8 -*-
#   Copyright 2010 Agile42 GmbH, Berlin (Germany)
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
#       - Robert Buchholz <robert.buchholz__at__agile42.com>

from trac.db.api import DatabaseManager

from agilo.db.upgrades.db5 import do_upgrade
from agilo.test.functional import AgiloFunctionalTestCase
from agilo.test.test_util import Usernames
from agilo.utils import Action


class OldAction(object):
    MODIFY_CONTINGENTS      = 'AGILO_MODIFY_CONTINGENTS'
    ADD_TIME_FOR_CONTINGENT = 'AGILO_ADD_TIME_FOR_CONTINGENT'


class TestDB5Upgrade(AgiloFunctionalTestCase):
    
    def setUp(self):
        self.super()
        self.teh.create_member(Usernames.team_member, self.team_name())
        self.inject_permission(Usernames.team_member, OldAction.MODIFY_CONTINGENTS)
        
        self.teh.create_member(self.other_user(), self.team_name())
        self.inject_permission(self.other_user(), OldAction.ADD_TIME_FOR_CONTINGENT)
        self.assert_original_permissions_are_set()
    
    def tearDown(self):
        self.revoke_permission(Usernames.team_member, OldAction.MODIFY_CONTINGENTS)
        self.revoke_permission(self.other_user(), OldAction.ADD_TIME_FOR_CONTINGENT)
        self.super()
    
    def inject_permission(self, username, permission):
        db = self.env.get_db_cnx()
        sql = r"INSERT INTO permission (username, action) VALUES ('%s', '%s')"
        db.cursor().execute(sql % (username, permission))
        db.commit()
    
    def revoke_permission(self, username, permission):
        db = self.env.get_db_cnx()
        sql = r"DELETE FROM permission WHERE username='%s' AND action='%s';"
        db.cursor().execute(sql % (username, permission))
        db.commit()
    
    def other_user(self):
        return 'AnotherUser'
    
    def _call_db5_upgrade(self):
        dbm = DatabaseManager(self.env)
        db_connector, _ = dbm._get_connector()
        db = self.env.get_db_cnx()
        self.assert_true(do_upgrade(self.env, 5, db.cursor(), db_connector))
        db.commit()
    
    def assert_original_permissions_are_set(self):
        self.assert_true(self.teh.has_permission(Usernames.team_member, OldAction.MODIFY_CONTINGENTS))
        self.assert_true(self.teh.has_permission(self.other_user(), OldAction.ADD_TIME_FOR_CONTINGENT))
    
    def _assert_correct_permissions_were_changed(self):
        self.assert_false(self.teh.has_permission(Usernames.team_member, OldAction.MODIFY_CONTINGENTS))
        self.assert_true(self.teh.has_permission(Usernames.team_member, Action.CONTINGENT_ADMIN))
        
        self.assert_false(self.teh.has_permission(self.other_user(), OldAction.ADD_TIME_FOR_CONTINGENT))
        self.assert_true(self.teh.has_permission(self.other_user(), Action.CONTINGENT_ADD_TIME))
    
    def test_can_upgrade_from_db4_to_db5(self):
        self._call_db5_upgrade()
        self._assert_correct_permissions_were_changed()
    
