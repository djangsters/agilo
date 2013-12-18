#!/usr/bin/env python
# -*- encoding: utf-8 -*-
#   Copyright 2008 Agile42 GmbH, Berlin (Germany)
#   Copyright 2007 Andrea Tomasini <andrea.tomasini_at_agile42.com>
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
#   Author: Andrea Tomasini <andrea.tomasini_at_agile42.com>

from time import sleep

import agilo.utils.filterwarnings

from agilo.test import Usernames
from agilo.test.functional import AgiloFunctionalTestCase
from agilo.utils import Type, Key, Status
from agilo.utils.errors import DependenciesError, InvalidAttributeError, \
    NotAssignedError, NotOwnerError
from agilo.test import TestEnvHelper
from agilo.utils.svn_hooks import AgiloSVNPreCommit, AgiloSVNPostCommit


class TestSVNHooks(AgiloFunctionalTestCase):
    """Test case to test the SVN pre and post hook, acting on agilo rules."""
    
    def _testPostCommitClose(self):
        """Tests the post commit hook with close command"""
        # Create a ticket of type task, and set it to assigned
        task = self.teh.create_ticket(Type.TASK, props={Key.REMAINING_TIME: '2'})
        # Create a file in the SVN repository using the helper
        rev = self.teh.create_file('test_not_assigend.txt', "This is a test :-)", 'tester', "Closes #%d" % task.id)
        apostc = AgiloSVNPostCommit(project=self.teh.get_env_path(), rev=rev, env=self.teh.get_env())
        # Execute the commands
        self.assertRaises(NotAssignedError, apostc.execute)
        # Now set the task to assigned, change owner and try again
        task = self.teh.create_ticket(Type.TASK, props={Key.REMAINING_TIME: '2'})
        task[Key.STATUS] = Status.ASSIGNED
        task[Key.OWNER] = 'somebody'
        task.save_changes('somebody', 'Accepted the ticket')
        rev = self.teh.create_file('test_not_owner.txt', "This is a test :-)", 'tester', "Closes #%d" % task.id)
        apostc = AgiloSVNPostCommit(project=self.teh.get_env_path(), rev=rev, env=self.teh.get_env())
        self.assertRaises(NotOwnerError, apostc.execute)
        # Now set the right owner, should succeed
        task = self.teh.create_ticket(Type.TASK, props={Key.OWNER: 'tester',
                                                        Key.REMAINING_TIME: '2'})
        task[Key.STATUS] = Status.ASSIGNED
        task.save_changes('tester', 'It is mine again')
        # The command execute will save again in less than one second...
        sleep(1)
        rev = self.teh.create_file('test_ok.txt', "This is a test :-)", 'tester', "Closes #%d" % task.id)
        apostc = AgiloSVNPostCommit(project=self.teh.get_env_path(), rev=rev, env=self.teh.get_env())
        apostc.execute()
        # Reload the task from Trac
        task = self.teh.load_ticket(task)
        self.assertEqual(task[Key.STATUS], Status.CLOSED)
        self.assertEqual(task[Key.REMAINING_TIME], '0')
        
    def _testPostCommitRemaining(self):
        """Tests the post commit hook with remaining time command"""
        # Create a ticket of type task, and set it to assigned
        task = self.teh.create_ticket(Type.TASK, props={Key.OWNER: 'tester',
                                                        Key.REMAINING_TIME: '8'})
        # Create a file in the SVN reposoitory using the helper
        rev = self.teh.create_file('test_remaining.txt', "This is a test :-)", 
                                   'tester', "Remaining #%d:4h" % task.id)
        apostc = AgiloSVNPostCommit(project=self.teh.get_env_path(), 
                                    rev=rev, env=self.teh.get_env())
        apostc.execute()
        # Should set the task automatically to assigned
        task = self.teh.load_ticket(ticket=task)
        self.assertEqual(task[Key.REMAINING_TIME], '4')
        self.assertEqual(task[Key.STATUS], Status.ACCEPTED)
        # Now test with a wrong owner
        task = self.teh.create_ticket(Type.TASK, props={Key.OWNER: 'somebody', 
                                                        Key.REMAINING_TIME: '8'})
        # Create a file in the SVN reposoitory using the helper
        rev = self.teh.create_file('test_remaining_not_owner.txt', "This is a test :-)", 
                                   'tester', "Remaining #%d:4h" % task.id)
        apostc = AgiloSVNPostCommit(project=self.teh.get_env_path(), 
                                    rev=rev, env=self.teh.get_env())
        self.assertRaises(NotOwnerError, apostc.execute)
        # Now try to set remaining time on a Story
        story = self.teh.create_ticket(Type.USER_STORY)
        rev = self.teh.create_file('test_remaining_story.txt', "This is a test :-)", 
                                   'tester', "Remaining #%d:4h" % story.id)
        apostc = AgiloSVNPostCommit(project=self.teh.get_env_path(), 
                                    rev=rev, env=self.teh.get_env())
        self.assertRaises(InvalidAttributeError, apostc.execute)
        
    def _testPostCommitReference(self):
        """Tests the post commit hook with references command"""
        # Create a ticket of type task, and set it to assigned
        task = self.teh.create_ticket(Type.TASK, props={Key.REMAINING_TIME: '8'})
        # Create a file in the SVN repository using the helper
        rev = self.teh.create_file('test_reference.txt', "This is a test :-)", 
                                   'tester', "See #%d" % task.id)
        apostc = AgiloSVNPostCommit(project=self.teh.get_env_path(), 
                                    rev=rev, env=self.teh.get_env())
        apostc.execute()
        
    def _testPostCommitMultipleCommands(self):
        """Tests the post commit hook with multiple commands combinations"""
        # Create a some tickets
        task1 = self.teh.create_ticket(Type.TASK, props={Key.OWNER: 'tester',
                                                         Key.REMAINING_TIME: '8'})
        task2 = self.teh.create_ticket(Type.TASK, props={Key.OWNER: 'tester',
                                                         Key.REMAINING_TIME: '4'})
        story = self.teh.create_ticket(Type.USER_STORY, props={Key.STORY_POINTS: '13'})
        # Assign the task1, otherwise will not allow to close it
        task1[Key.STATUS] = Status.ASSIGNED
        task1.save_changes('tester', 'Accepted the task...')
        sleep(1)
        # Create a file in the SVN repository using the helper
        rev = self.teh.create_file('test_multiple.txt', "This is a test :-)", 'tester', 
                                   "This closes #%d and remaining #%d:2h, see #%d for more details." % \
                                   (task1.id, task2.id, story.id))
        apostc = AgiloSVNPostCommit(project=self.teh.get_env_path(), 
                                    rev=rev, env=self.teh.get_env())
        apostc.execute()
        # Reload the tickets from Trac
        task1 = self.teh.load_ticket(ticket=task1)
        task2 = self.teh.load_ticket(ticket=task2)
        story = self.teh.load_ticket(ticket=story)
        # Now check the commands have been executed successfully
        self.assertEqual(task1[Key.STATUS], Status.CLOSED)
        self.assertEqual(task1[Key.REMAINING_TIME], '0')
        self.assertEqual(task2[Key.STATUS], Status.ACCEPTED)
        self.assertEqual(task2[Key.REMAINING_TIME], '2')
        
    def _testPostCommitDependencies(self):
        """Tests the post commit hook with some dependencies links"""
        # Create a some tickets
        story = self.teh.create_ticket(Type.USER_STORY, props={Key.STORY_POINTS: '13'})
        task1 = self.teh.create_ticket(Type.TASK, props={Key.OWNER: 'tester',
                                                         Key.REMAINING_TIME: '8'})
        task2 = self.teh.create_ticket(Type.TASK, props={Key.OWNER: 'tester',
                                                         Key.REMAINING_TIME: '4'})
        self.assertTrue(story.link_to(task1))
        self.assertTrue(story.link_to(task2))
        # Assign the task1, otherwise will not allow to close it
        task1[Key.STATUS] = Status.ASSIGNED
        task1.save_changes('tester', 'Accepted the task...')
        sleep(1)
        # Create a file in the SVN reposoitory using the helper
        rev = self.teh.create_file('test_multiple_dependencies.txt', "This is a test :-)", 'tester', 
                                   "This closes #%d and remaining #%d:2h, closes #%d for more details." % \
                                   (task1.id, task2.id, story.id))
        apostc = AgiloSVNPostCommit(project=self.teh.get_env_path(), rev=rev, 
                                    env=self.teh.get_env())
        self.assertRaises(DependenciesError, apostc.execute)
        
    def _testPostCommitMultipleDependencies(self):
        """Tests the post commit hook with multiple commands and dependencies"""
        story = self.teh.create_ticket(Type.USER_STORY, props={Key.STORY_POINTS: '13'})
        task1 = self.teh.create_ticket(Type.TASK, props={Key.OWNER: 'tester',
                                                         Key.REMAINING_TIME: '8'})
        task2 = self.teh.create_ticket(Type.TASK, props={Key.OWNER: 'tester',
                                                         Key.REMAINING_TIME: '4'})
        self.assertTrue(story.link_to(task1))
        self.assertTrue(story.link_to(task2))
        # Assign the task1, otherwise will not allow to close it
        task1[Key.STATUS] = Status.ASSIGNED
        task1.save_changes('tester', 'Accepted the task...')
        # Assign the task2, otherwise will not allow to close it
        task2[Key.STATUS] = Status.ASSIGNED
        task2.save_changes('tester', 'Accepted the task...')
        sleep(1)
        rev = self.teh.create_file('test_multiple_ok.txt', "This is a test :-)", 'tester', 
                                   "This closes #%d and #%d, closes #%d for more details." % \
                                   (task1.id, task2.id, story.id))
        apostc = AgiloSVNPostCommit(project=self.teh.get_env_path(), 
                                    rev=rev, env=self.teh.get_env())
        apostc.execute()                    
        # Reload the tickets from Trac
        task1 = self.teh.load_ticket(ticket=task1)
        task2 = self.teh.load_ticket(ticket=task2)
        story = self.teh.load_ticket(ticket=story)
        # Now check the commands have been executed successfully
        self.assertEqual(task1[Key.STATUS], Status.CLOSED)
        self.assertEqual(task1[Key.REMAINING_TIME], '0')
        self.assertEqual(task2[Key.STATUS], Status.CLOSED)
        self.assertEqual(task2[Key.REMAINING_TIME], '0')
        self.assertEqual(story[Key.STATUS], Status.CLOSED)
        
    def _testPreCommit(self):
        """Tests the pre commit hook validation"""
        wrong_log = "This ticket doesn't exists, close #cacca and #9999, see #9999"
        aprec = AgiloSVNPreCommit(project=self.teh.get_env_path(), 
                                  log=wrong_log, env=self.teh.get_env())
        try:
            aprec.execute()
            self.fail()
        except Exception, e:
            #print "Error <%s>: %s" % (e.__class__.__name__, str(e))
            self.assertTrue(len(str(e)) > 0)
        # Now create a real ticket and should work
        task = self.teh.create_ticket(Type.TASK)
        story = self.teh.create_ticket(Type.USER_STORY)
        right_log = "see #%d and #%d" % (task.id, story.id)
        aprec = AgiloSVNPreCommit(project=self.teh.get_env_path(), 
                                  log=right_log, env=self.teh.get_env())
        self.assertTrue(aprec.execute())
        
    def _testParsingCommands(self):
        """Tests some combinations of valid and invalid commands for both hooks"""
        valid_logs = [
            "I have closed #3123 and #123",
            "See #123 and #1873, remaining #45:5h",
            "Today is not a very good day but still I manage to close #12",
            "This is cacca #342 and #412, see #241",
            "This closes #cacca and #123, see #24",
            "This ticket doesn't exists, close #cacca and #999, see #3123"
        ]
        invalid_logs = [
            "This is a totally messed up #134",
            "This for sure #231 is wrong",
            "what about running #231 and #nothing for #112",
            ""
        ]
        for log in valid_logs:
            try:
                AgiloSVNPreCommit(project=self.teh.get_env_path(), 
                                  log=log, env=self.teh.get_env()).execute()
            except InvalidAttributeError, e:
                #print "Error: <%s>" % str(e)
                pass
            except Exception, e:
                print "Error <%s>: %s" % (e.__class__.__name__, str(e))
                self.fail()
        for log in invalid_logs:
            try:
                AgiloSVNPreCommit(project=self.teh.get_env_path(), 
                                  log=log, env=self.teh.get_env()).execute()
                self.fail()
            except Exception, e:
                #print "Error <%s>: %s" % (e.__class__.__name__, str(e))
                pass

    def runTest(self):
        """Tests SVN Hooks with various commands"""
        self._testParsingCommands()
        self._testPostCommitClose()
        self._testPostCommitDependencies()
        self._testPostCommitMultipleCommands()
        self._testPostCommitMultipleDependencies()
        self._testPostCommitReference()
        self._testPostCommitRemaining()
        self._testPreCommit()


class TestCanSetDecimalRemainingTimeWithSVNHook(AgiloFunctionalTestCase):
    
    def create_task(self, teh):
        task_id = self.tester.create_new_agilo_task('Foo', **{Key.REMAINING_TIME: 4})
        self.tester.accept_ticket(task_id)
        # This did not work for me (see explanation in the method)
        # teh.move_changetime_to_the_past([task_id])
        sleep(1)
        return task_id
    
    def work_on_task(self, task_id, teh):
        svn_filename = 'test_set_decimals_with_svn_hook.txt'
        # I assume that we just ignore the unit as we did before with 'h'.
        commit_comment = 'still #%s:1.5h left' % task_id
        rev = teh.create_file(svn_filename, 'Test', Usernames.team_member, 
                              commit_comment)
        return rev
    
    def runTest(self):
        self._tester.login_as(Usernames.team_member)
        trac_env = self.testenv.get_trac_environment()
        teh = TestEnvHelper(trac_env, env_key=self.env_key)
        project_dir = self.testenv.dirname
        
        task_id = self.create_task(teh)
        rev = self.work_on_task(task_id, teh)
        AgiloSVNPostCommit(project=project_dir, rev=rev, env=trac_env).execute()
        
        ticket_page = self.tester.navigate_to_ticket_page(task_id)
        self.assertEqual('1.5h', ticket_page.remaining_time())


if __name__ == '__main__':
    from agilo.test.testfinder import run_all_tests
    run_all_tests(__file__)

