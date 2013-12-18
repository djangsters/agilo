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
#       - Martin Häcker <martin.haecker__at__agile42.com>

import agilo.utils.filterwarnings

from agilo.test import AgiloTestCase

from agilo.utils.config import AgiloConfig
from agilo.utils.errors import *
from agilo.utils.svn_hooks import AgiloSVNPreCommit

class SVNHookCommandParsingTest(AgiloTestCase):
    
    def parse(self, commit_message):
        return AgiloSVNPreCommit(project=self.teh.get_env_path(), log=commit_message, env=self.env).execute()
    
    # Pre Hook (parser) tests
    
    def test_raises_on_empty_log_message(self):
        exception = self.assert_raises(Exception, self.parse, '')
        self.assert_true("Please provide a comment" in exception.args[0])
        self.assert_true("Supported commands include" in exception.args[0])
    
    def test_can_have_as_many_whitespace_between_command_and_ticket_as_wanted(self):
        story = self.teh.create_story()
        parsed = [('closes', '%s' % story.id, '')]
        self.assert_equals(parsed, self.parse('closes  #%s' % story.id))
        self.assert_equals(parsed, self.parse('closes         \t\t   \t #%s' % story.id))
        self.assert_equals(parsed, self.parse('closes \t\n\r#%s' % story.id))
    
    def test_can_contain_special_characters_in_commit_message(self):
        # only a stray # somewhere doesn't block the commit
        self.assert_equals([], self.parse('#'))
        self.assert_equals([], self.parse('fooo # bar'))
        self.assert_equals([], self.parse('foo #bar foo'))
    
    def test_adding_multiple_tickets_to_a_command(self):
        # Add some testcases for the allowed syntaxes to group tickets
        # '#1 & #2' or '#1, #2' or '#1 and #2'
        first_id = self.teh.create_story().id
        second_id = self.teh.create_story().id
        parsed = [('closes', '%s' % first_id, ''), ('closes', '%s' % second_id, '')]
        
        self.assert_equals(parsed, self.parse('closes #%s, #%s' % (first_id, second_id)))
        self.assert_equals(parsed, self.parse('closes #%s & #%s' % (first_id, second_id)))
        self.assert_equals(parsed, self.parse('closes #%s and #%s' % (first_id, second_id)))
        
        self.assert_equals(parsed, self.parse('closes #%s, #%s' % (first_id, second_id)))
        self.assert_equals(parsed, self.parse('closes #%s   \t\r\n,   \t\r\n#%s' % (first_id, second_id)))
    
    def test_can_extract_remaining_time_with_unit(self):
        task_id = self.teh.create_task().id
        parsed = [('rem', "%s" % task_id, '3h')]
        self.assert_equals(parsed, self.parse('rem #%s:3h' % task_id))
        
        AgiloConfig(self.env).use_days = True
        parsed = [('TIME', "%s" % task_id, '3d')]
        self.assert_equals(parsed, self.parse('TIME #%s:3d' % task_id))
    
    def test_raises_if_ticket_id_not_found(self):
        exception = self.assert_raises(InvalidAttributeError, self.parse, 'closes #1')
        self.assert_true('Unable to verify ticket' in exception.args[0])
    
    def test_raises_if_want_to_change_remaining_time_and_ticket_has_no_remaining_time_attribute(self):
        story = self.teh.create_story()
        exception = self.assert_raises(InvalidAttributeError, self.parse, 'still #%s:1h' % story.id)
        self.assert_true('Remaining time is not an allowed property for this ticket' in exception.args[0])
    
    # We decided to do this as test numbers are continuus
    # def test_raises_if_non_existing_ticket_is_referenced(self):
    #     # - only a reference to a ticket without a command should be valid if that ticket exists
    #     exception = self.assert_raises(InvalidAttributeError, self.parse, '#1')
    #     self.assert_true('Unable to verify ticket' in exception.args[0])
    #     
    #     exception = self.assert_raises(InvalidAttributeError, self.parse, 'foo #1')
    #     self.assert_true('Unable to verify ticket' in exception.args[0])
    #     
    #     exception = self.assert_raises(InvalidAttributeError, self.parse, '#1 bar')
    #     self.assert_true('Unable to verify ticket' in exception.args[0])
    #     
    #     exception = self.assert_raises(InvalidAttributeError, self.parse, 'foo #1 bar')
    #     self.assert_true('Unable to verify ticket' in exception.args[0])
    
    def test_raises_if_non_existing_ticket_is_referenced_in_command(self):
        # - a command without a valid ticket reference should not be valid
        exception = self.assert_raises(InvalidAttributeError, self.parse, 'closes #1')
        self.assert_true('Unable to verify ticket' in exception.args[0])
        
        exception = self.assert_raises(InvalidAttributeError, self.parse, 'foo fixes #1')
        self.assert_true('Unable to verify ticket' in exception.args[0])
        
        exception = self.assert_raises(InvalidAttributeError, self.parse, 're #1 bar')
        self.assert_true('Unable to verify ticket' in exception.args[0])
        
        exception = self.assert_raises(InvalidAttributeError, self.parse, 'foo rem #1 bar')
        self.assert_true('Unable to verify ticket' in exception.args[0])
    
    def test_raises_if_non_remaining_time_changing_command_gets_ticket_with_time_reference(self):
        # - a ticket with time reference without a matching command should be invalid
        task_id = self.teh.create_task().id
        exception = self.assert_raises(InvalidAttributeError, self.parse, 'closes #%s:3h' % task_id)
        self.assert_true('Cannot set remaining time with command' in exception.args[0], exception)
        
        exception = self.assert_raises(InvalidAttributeError, self.parse, 'fixes #%s:1.3d' % task_id)
        self.assert_true('Cannot set remaining time with command' in exception.args[0], exception)
        
        # Dont mix up with rem - which could change the remaining time
        exception = self.assert_raises(InvalidAttributeError, self.parse, 're #%s:3h' % task_id)
        self.assert_true('Cannot set remaining time with command' in exception.args[0], exception)
    
    def test_command_words_without_ticket_references_are_valid(self):
        # so you can use them in normal sentences
        self.assert_equals([], self.parse('I see what you mean'))
        self.assert_equals([], self.parse('you remain calm'))
        self.assert_equals([], self.parse('still there is lots to do'))
        self.assert_equals([], self.parse('that about closes it'))
    
    def test_remaining_time_commands_raise_if_they_are_called_without_a_remaining_time(self):
        task_id = self.teh.create_task().id
        exception = self.assert_raises(InvalidAttributeError, self.parse, 'STILL #%s' % task_id)
        self.assert_true('Missing remaining time for command' in exception.args[0], exception)
    
    def test_ticket_validation_error_doesnt_make_rest_of_code_throw(self):
        exception = self.assert_raises(InvalidAttributeError, self.parse, 'rem #1:3h')
        self.assert_true('Unable to verify ticket' in exception.args[0])
    
    def test_time_references_raises_if_h_or_d_suffix_is_missing(self):
        # especially on non time remaining changing commands so you know you made a mistake
        task_id = self.teh.create_task().id
        exception = self.assert_raises(InvalidAttributeError, self.parse, 'rem #%s:3' % task_id)
        self.assert_true('Need h(our) or d(ay) unit for remaining time' in exception.args[0])
    
    def test_raises_if_wrong_unit_is_used(self):
        task_id = self.teh.create_task().id
        config = AgiloConfig(self.env)
        
        config.use_days = True
        parsed = [('rem', "%s" % task_id, '3d')]
        self.assert_equals(parsed, self.parse('rem #%s:3d' % task_id))
        exception = self.assert_raises(InvalidAttributeError, self.parse, 'rem #%s:3h' % task_id)
        self.assert_true('Wrong unit used in remaining time' in exception.args[0])
        
        config.use_days = False
        parsed = [('rem', "%s" % task_id, '3h')]
        self.assert_equals(parsed, self.parse('rem #%s:3h' % task_id))
        exception = self.assert_raises(InvalidAttributeError, self.parse, 'rem #%s:3d' % task_id)
        self.assert_true('Wrong unit used in remaining time' in exception.args[0])
    
    # consider to enforce a word break after a remaining time unit
    # check that the right unit is used for time remaining
    # Post Hook tests
    # Do these later - if I can retain all the parsing being done via a regex, I don't need to change the post-hook at all
    
    
    # I would like to get as a result of the parsing a datasructure like this
    # (command, (ticket-id[, remaining_time]))*

