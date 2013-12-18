#!/usr/bin/env python
# -*- coding: utf-8 -*-
#   Copyright 2008 Agile42 GmbH - Andrea Tomasini
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
# Authors:
#     - Andrea Tomasini <andrea.tomasini__at__agile42.com>

from trac.ticket import Milestone

from agilo.test import AgiloTestCase, TestEnvHelper
from agilo.ticket import AgiloTicketSystem
from agilo.ticket.model import AgiloMilestone
from agilo.scrum.sprint.model import SprintModelManager
from agilo.utils import Key, Type
from agilo.utils.days_time import now

class MilestoneTest(AgiloTestCase):
    """Tests AgiloMilestone behavior, in particular the renaming, with the
    update of the related tickets"""
    
    def testMilestoneIsPatched(self):
        """Tests that the Milestone is patched with AgiloMilestone"""
        m = Milestone(self.env)
        self.assert_true(isinstance(m, AgiloMilestone), \
                        "The milestone is: %s" % type(m))
        
    def testMilestoneRenamePropagatesToTickets(self):
        """Tests that the Milestone renaming is propagated to the tickets, this
        should work out of the box, as it is a Trac feature"""
        m = Milestone(self.env)
        m.name = 'test_me'
        m.insert()
        t = self.teh.create_ticket(Type.REQUIREMENT, {Key.MILESTONE: m.name})
        self.assert_equals(m.name, t[Key.MILESTONE])
        # AT: we need to reload the milestone as there is a problem in trac,
        # that the insert is not updating the _old_name, making the update
        # silently fail. I sent a patch for this
        m = Milestone(self.env, m.name)
        m.name = 'test_me_not'
        m.update()
        # test the changes happened in the DB
        db = self.env.get_db_cnx()
        cursor = db.cursor()
        cursor.execute("SELECT id, milestone FROM ticket WHERE milestone='test_me'")
        for row in cursor:
            self.fail("Found one old milestone in ticket: #%s (%s)" % \
                      (row[0], row[1]))
        t = self.teh.load_ticket(t)
        self.assert_equals(m.name, t[Key.MILESTONE])
    
    def testMilestoneRenamePropagatesToSprints(self):
        """Tests that the rename of a Milestone, propagates to the Sprints, this
        is an AgiloMilestone feature"""
        m = Milestone(self.env)
        m.name = 'test_me'
        m.insert()
        s = self.teh.create_sprint('my sprint', milestone=m.name)
        self.assert_equals(m.name, s.milestone)
        # AT: we need to reload the milestone as there is a problem in trac,
        # that the insert is not updating the _old_name, making the update
        # silently fail. I sent a patch for this
        m = Milestone(self.env, m.name)
        m.name = 'test_me_not'
        m.update()
        smm = SprintModelManager(self.env)
        smm.get_cache().invalidate()
        s = smm.get(name=s.name)
        self.assert_equals(m.name, s.milestone)

    def test_do_not_raise_exception_on_edit_in_multienv_with_plain_trac(self):
        plain_trac_env = TestEnvHelper(enable_agilo=False, env_key=self.env_key).env
        # This situation happens due to monkey-patching: The plain trac 
        # environment needs to work with Agilo classes.
        milestone = AgiloMilestone(plain_trac_env)
        milestone.name = 'fnord'
        milestone.insert()
        
        # Must not raise an exception
        milestone.update()
    
    def test_can_save_due_date(self):
        # Added when Trac 0.12 was released as the format of the timestamp has changed in 0.12
        milestone = Milestone(self.env)
        milestone.name = 'fnord'
        milestone.insert()
        # in trac 0.11.1, milestone._old_name is not set to "fnord" at
        # insert() time, only on init() or update()
        # so we need to reload the object to be able to run update() on it
        milestone = Milestone(self.env, name='fnord')
        
        expected_time = now().replace(microsecond=0)
        milestone.due = expected_time
        milestone.completed = expected_time
        milestone.update()
        
        loaded_milestone = Milestone(self.env, name='fnord')
        self.assert_equals(expected_time, loaded_milestone.due)
        self.assert_equals(expected_time, loaded_milestone.completed)
    


