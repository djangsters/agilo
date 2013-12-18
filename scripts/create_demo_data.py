#!/usr/bin/env python
# -*- coding: utf8 -*-
#   Copyright 2009 agile42 GmbH All rights reserved
#   Copyright 2011 Agilo Software GmbH All rights reserved
#
#   Authors:
#        - Andrea Tomasini <andrea.tomasini__at__agile42.com>

import sys
import getopt
from random import randint

from trac.env import Environment

from agilo.scrum.burndown.model import BurndownDataChangeModelManager
from agilo.test import TestEnvHelper
from agilo.utils import Key, Type

help_message = '''
Generate demo data into an existing environment.
    -e, --env=<path>  Specify the path to the environment
    -h, --help        Print this message
    -d, --delete      Deletes every pre-existing data
'''


class Usage(Exception):
    def __init__(self, msg):
        self.msg = msg


# ---------------------------------------------------------------------------
# TODO: Move this into Team Member admin - did not want to destabilize release
from trac.perm import PermissionSystem
from agilo.utils import Role

try:
    from acct_mgr.api import AccountManager
except ImportError:
    AccountManager = None

class UserManager(object):
    
    def __init__(self, env):
        self.env = env
    
    def account_manager_is_enabled(self):
        if AccountManager is not None:
            return self.env.is_component_enabled(AccountManager)
        return False
    
    def use_account_manager_integration(self, member_name):
        if self.account_manager_is_enabled():
            account_already_created = AccountManager(self.env).has_user(member_name)
            if not account_already_created:
                return AccountManager(self.env).supports('set_password')
        return False
    
    def create_user_and_grant_permissions(self, team_member):
        if self.use_account_manager_integration(team_member.name):
            password = team_member.name
            AccountManager(self.env).set_password(team_member.name, password)
        permission_system = PermissionSystem(self.env)
        if not permission_system.check_permission(Role.TEAM_MEMBER, team_member.name):
            permission_system.grant_permission(team_member.name, Role.TEAM_MEMBER)
# ---------------------------------------------------------------------------


def delete_burndown_data_change(env):
    for change in BurndownDataChangeModelManager(env).select(order_by=['-id']):
        change.delete()

def _create_demo_data(env, delete):
    """Creates a set of requirements and Stories for the Demo project.
    If the delete option is set to True, it will also delete every
    existing ticket before starting to add the demo ones. If in the
    target environment there is no Team set, it will create some users
    and a demo team."""
    teh = TestEnvHelper(env)
    
    if delete:
        teh.delete_all_milestones()
        teh.delete_all_sprints()
        teh.delete_all_tickets()
        delete_burndown_data_change(env)
    
    # Now check if there is at least one team
    team = _check_or_create_team(teh)
    
    # create milestone and sprints, and assign it to the team
    # Remember that this sprint started 3 days ago
    sprint = _create_sprint(teh, team)
    
    # create a Product Backlog
    stories = _create_product_backlog(teh, sprint)
    _create_sprint_backlog(teh, stories, sprint)

def _create_sprint_backlog(teh, stories, sprint):
    """Move stories to a sprint, and break them down into tasks, than
    creates historical remaining time data for the sprint backlog"""
    us1, us2 = stories
    owners = [m.name for m in sprint.team.members]
    tasks1 = [
        {Key.SUMMARY: 'Update AgiloTicketModule',
         Key.OWNER: owners[randint(0, len(owners) - 1)],
         Key.SPRINT: sprint.name,
         Key.DESCRIPTION: 'update the AgiloTicketModule: modify the ' + \
                          'create_new_ticket() so that it can redirect ' + \
                          'to the originating ticket after creation'},
        {Key.SUMMARY: 'Write Functional Test',
         Key.OWNER: owners[randint(0, len(owners) - 1)],
         Key.SPRINT: sprint.name,
         Key.DESCRIPTION: 'write a twill test to check that with and ' + \
                          'without the parameter the redirection works'},
    ]
    tasks2 = [
        {Key.SUMMARY: 'Get user context information',
         Key.OWNER: owners[randint(0, len(owners) - 1)],
         Key.SPRINT: sprint.name,
         Key.DESCRIPTION: 'create a method to get user context info'},
        {Key.SUMMARY: 'Provide context help link on all pages',
         Key.OWNER: owners[randint(0, len(owners) - 1)],
         Key.SPRINT: sprint.name,
         Key.DESCRIPTION: 'create a link for help in every page that ' + \
                          'will redirect to the appropriate help page'},
        {Key.SUMMARY: 'Implement method to get page by context',
         Key.SPRINT: sprint.name,
         Key.DESCRIPTION: 'create a method in agilo help to get the ' + \
                          'pages by context'},
    ]
    for t in tasks1:
        task = teh.create_ticket(Type.TASK, props=t)
        us1.link_to(task)
    for t in tasks2:
        task = teh.create_ticket(Type.TASK, props=t)
        us2.link_to(task)
    for task in us1.get_outgoing() + us2.get_outgoing():
        teh.generate_remaining_time_data(task, sprint.start)

def _create_product_backlog(teh, sprint):
    """Creates a set of Requirements and User Stories that will
    represent the Product Backlog. Plans 2 stories for the sprint"""
    requirements = [
        {Key.SUMMARY: 'Need to improve usability',
         Key.DESCRIPTION: 'There is the need to make the product ' + \
                          'usage more intuitive, the number of ' + \
                          'support requests related to usage of ' + \
                          'the tool are too many and often related ' + \
                          'to very "simple" problems',
         Key.BUSINESS_VALUE: '2000'},
        {Key.SUMMARY: 'Need to ease configuration',
         Key.DESCRIPTION: 'There is the need to increase the ease ' + \
                          'of configuration of the product. too ' + \
                          'often admins report to have to look ' + \
                          'into the product code to understand ' + \
                          'how to configure it',
         Key.BUSINESS_VALUE: '1200'}
    ]
    stories = [
        {Key.SUMMARY: 'Reduce clicks to create a ticket',
         Key.DESCRIPTION: 'As a user of the tool I would like to be ' + \
                          'able to create linked ticket with only ' + \
                          'one single click so that I will not have' + \
                          'to browse back and check where the ' + \
                          'originating ticket is gone',
         Key.STORY_POINTS: '3',
         Key.STORY_PRIORITY: 'Linear',
         Key.SPRINT: sprint.name},
        {Key.SUMMARY: 'Improve the integrated help system',
         Key.DESCRIPTION: 'As a user of the tool I would like to ' + \
                          'have an integrated help system that ' + \
                          'allows me to get information ' + \
                          'contextualized to the part of the tool ' + \
                          'in which I am working, so that I will ' + \
                          'spend less time searching for answers',
         Key.STORY_POINTS: '8',
         Key.STORY_PRIORITY: 'Mandatory',
         Key.SPRINT: sprint.name},
        {Key.SUMMARY: 'Searching through the help pages',
         Key.DESCRIPTION: 'As a user of the tool I would like to ' + \
                          'be able to search through the help, ' + \
                          'so that I can find what I am looking ' + \
                          'for without having to navigate through it',
         Key.STORY_POINTS: '13',
         Key.STORY_PRIORITY: 'Linear'},
        {Key.SUMMARY: 'Integrated Tooltips',
         Key.DESCRIPTION: 'As a user of the tool I would like to ' + \
                          'see tooltip while hovering forms fields ' + \
                          'and buttons to understand faster what ' + \
                          'format and kind of information I need ' + \
                          'to provide so that I can accomplish ' + \
                          'tasks faster',
         Key.STORY_POINTS: '5',
         Key.STORY_PRIORITY: 'Exciter'}
    ]
    backlog_stories = []
    # Create the tickets
    req1 = teh.create_ticket(Type.REQUIREMENT, props=requirements[0])
    for story in stories:
        us = teh.create_ticket(Type.USER_STORY, props=story)
        req1.link_to(us)
        if Key.SPRINT in story:
            backlog_stories.append(us)
    teh.create_ticket(Type.REQUIREMENT, props=requirements[1])
    return backlog_stories

def _create_sprint(teh, team):
    """Creates a Sprint, a milestone and assign the given team to the
    newly created sprint, that will be returned"""
    milestone = teh.create_milestone("Demo Release 1.0")
    sprint = teh.create_sprint("Demo Sprint 1", team=team, 
                               milestone=milestone, duration=10)
    return sprint

def _check_or_create_team(teh):
    """Check if there is a team configured, and use that team for the 
    demo, if not existing will create one with three members"""
    team = None
    team_names = teh.list_team_names()
    user_manager = UserManager(teh.get_env())
    
    if len(team_names) == 0:
        members = ['dave', 'mary', 'tom']
        team = teh.create_team('Demo Team')
        # create three team members
        for member_name in members:
            team_member = teh.create_member(member_name, team='Demo Team')
            user_manager.create_user_and_grant_permissions(team_member)
    else:
        # this will just return the team if already existing
        team = teh.create_team(team_names[0])
    return team

def main(argv=None):
    if argv is None:
        argv = sys.argv
    try:
        try:
            opts, args = getopt.getopt(argv[1:], "e:dh", ["env=", "delete", "help"])
        except getopt.error, msg:
            raise Usage(msg)
        
        # global script variables
        env = None
        delete = False
        # option processing
        for option, value in opts:
            if option in ("-h", "--help"):
                raise Usage(help_message)
            if option in ("-e", "--env"):
                env = Environment(value)
            if option in ("-d", "--delete"):
                delete = True
        
        # if no env is set we have to raise the error
        if not env:
            raise Usage("Please specify the environment path")
        
        # Crete the data
        _create_demo_data(env, delete)
        
    except Usage, err:
        print >> sys.stderr, sys.argv[0].split("/")[-1] + ": " + str(err.msg)
        print >> sys.stderr, "\t for help use --help"
        return 2


if __name__ == "__main__":
    sys.exit(main())
