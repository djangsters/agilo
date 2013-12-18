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

from agilo.utils import Key
from agilo.utils.command import CommandParser
from agilo.test import AgiloTestCase
from agilo.utils.config import AgiloConfig


class TestUtilsCommand(AgiloTestCase):
    """Testcase for command parser, used by Request Filter module at the momemt"""
    
    def setUp(self):
        """Creates the needed environment"""
        self.super()
        alias_mapping = AgiloConfig(self.env).ALIASES
        type_mapping = dict(zip(alias_mapping.values(), alias_mapping.keys()))
        self.cp = CommandParser(self.env, type_mapping, alias_mapping)
    
    def testCommandParser(self):
        """Tests the command parser with some command samples"""
        commands = {
            "'ticket':Key.TYPE": [
                (self.cp._by_key, 'ticket', ':Key.TYPE'), 
                (self.cp._by_key, Key.TYPE, '')],
            "'fields'@'options'(item[Key.NAME]==Key.TYPE)": [
                (self.cp._by_key, 'fields', "@'options'(item[Key.NAME]==Key.TYPE)"),
                (self.cp._iterate, ('options', '(item[Key.NAME]==Key.TYPE)'), '')],
            "'allowed_links':Key.TYPE": [
                (self.cp._by_key, 'allowed_links', ':Key.TYPE'),
                (self.cp._by_key, Key.TYPE, '')],
            "'available_types'": [(self.cp._by_key, 'available_types', '')],
            "'source'": [(self.cp._by_key, 'source', '')],
            "'target'": [(self.cp._by_key, 'target', '')],
            "'changes'@'fields'(item.has_key(Key.FIELDS)):Key.TYPE:'new'|'old'": [
                (self.cp._by_key, 'changes', "@'fields'(item.has_key(Key.FIELDS)):Key.TYPE:'new'|'old'"),
                (self.cp._iterate, ('fields', '(item.has_key(Key.FIELDS))'), ":Key.TYPE:'new'|'old'"),
                (self.cp._by_key, Key.TYPE, ":'new'|'old'"),
                (self.cp._by_key, ('new', 'old'), '')], #Note that string key are cleaned up here!
            "'ticket'@'types'": [
                (self.cp._by_key, 'ticket', "@'types'"),
                (self.cp._iterate, 'types', '')
            ],
            "'row_groups',0,1@'cell_groups',0@'value'(item['header']['title']=='Type')": [
                (self.cp._by_key, 'row_groups', ",0,1@'cell_groups',0@'value'(item['header']['title']=='Type')"),
                (self.cp._by_pos, 0, ",1@'cell_groups',0@'value'(item['header']['title']=='Type')"),
                (self.cp._by_pos, 1, "@'cell_groups',0@'value'(item['header']['title']=='Type')"),
                (self.cp._iterate, 'cell_groups', ",0@'value'(item['header']['title']=='Type')"),
                (self.cp._by_pos, 0, "@'value'(item['header']['title']=='Type')"),
                (self.cp._iterate, ('value', "(item['header']['title']=='Type')"), '')
            ],
            "'allowed_links':'*'" : [
                (self.cp._by_key, 'allowed_links', ":'*'"),
                (self.cp._by_key, '*', '')
            ],
        }
        # Iterate through commands and consume them
        for command in commands.keys():
            #print "Command: %s" % command
            acc, key, command = self.cp._parse_command(command)
            while command:
                #print "\nAcc: %s\nKey: %s\nCommand: %s\n" % (acc, key, command)
                acc, key, command = self.cp._parse_command(command)
                
        # Test against the expected results
        for command, results in commands.items():
            for res in results:
                self.assert_equals(self.cp._parse_command(command), res)
                command = res[2] # Substitute with remaining command
    

if __name__ == '__main__':
    from agilo.test.testfinder import run_unit_tests
    run_unit_tests(__file__)