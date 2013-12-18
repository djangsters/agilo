#!/usr/bin/env python
# -*- coding: utf8 -*-
#   Copyright 2010 agile42 GmbH All rights reserved
#   Copyright 2011 Agilo Software GmbH All rights reserved
#
#   Authors:
#        - Martin Häcker <martin.haecker__at__agile42.com>

import sys
import getopt

from trac.env import Environment

from agilo.utils import Key, Type
from agilo.test import TestEnvHelper
from agilo.scrum.backlog import Backlog

help_message = '''
Generate large backlogs into an existing environment. Usually for performance tests.
    -e, --env=<path>            Specify the path to the environment
    -n, --name=<sprint-name>    Specify the name of th sprint to create the backlog for
    -s, --size=<number>         Specify the number of items to create
    -h, --help                  Print this message
'''

def main(argv=None):
    if argv is None:
        argv = sys.argv
    try:
        try:
            opts, args = getopt.getopt(argv[1:], "e:n:s:h", ["env=", "name=", "size=", "help"])
        except getopt.error, msg:
            raise Usage(msg)
        
        # global script variables
        env = None
        sprint_name = "Big Backlog"
        number_of_tickets = 1000
        # option processing
        for option, value in opts:
            if option in ("-h", "--help"):
                raise Usage(help_message)
            if option in ("-e", "--env"):
                env = Environment(value)
            if option in ("-n", "--name"):
                sprint_name = value
            if option in ("-s", "--size"):
                number_of_tickets = int(value)
        
        # if no env is set we have to raise the error
        if not env:
            raise Usage("Please specify the environment path")
        
        print "Creating sprint <%s> with <%d> tickets." % (sprint_name, number_of_tickets)
        _create_sprint_with_backlog(env, sprint_name, number_of_tickets)
        
    except Usage, err:
        print >> sys.stderr, sys.argv[0].split("/")[-1] + ": " + str(err.msg)
        print >> sys.stderr, "\t for help use --help"
        return 2

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


def _create_sprint_with_backlog(env, sprint_name, number_of_tickets):
    """Creates a set of requirements and Stories for the Demo project.
    If the delete option is set to True, it will also delete every
    existing ticket before starting to add the demo ones. If in the
    target environment there is no Team set, it will create some users
    and a demo team."""
    teh = TestEnvHelper(env)
    sprint = _create_sprint_with_team(teh, sprint_name)
    _create_sprint_backlog(teh, sprint, number_of_tickets)

def _create_sprint_with_team(teh, sprint_name):
    """Creates a Sprint, a milestone and assign the given team to the
    newly created sprint, that will be returned"""
    milestone = teh.create_milestone("Performance Tests")
    team = _check_or_create_team(teh, "Performance Team")
    return teh.create_sprint(sprint_name, team=team, milestone=milestone, duration=100)

def _check_or_create_team(teh, team_name):
    """Check if there is a team configured, and use that team for the 
    demo, if not existing will create one with three members"""
    team = None
    team_names = teh.list_team_names()
    user_manager = UserManager(teh.get_env())
    
    if len(team_names) == 0:
        members = ['dave', 'mary', 'tom']
        team = teh.create_team(team_name)
        # create three team members
        for member_name in members:
            team_member = teh.create_member(member_name, team=team_name)
            user_manager.create_user_and_grant_permissions(team_member)
    else:
        # this will just return the team if already existing
        team = teh.create_team(team_names[0])
    return team

def _create_sprint_backlog(teh, sprint, number_of_tickets):
    """Move stories to a sprint, and break them down into tasks, than
    creates historical remaining time data for the sprint backlog"""
    
    for start_index in range(0, number_of_tickets, 10):
        _create_requirement_with_stories_and_tasks(teh, sprint, start_index)
    
    sprint_backlog = Backlog(teh.get_env(), Key.SPRINT_BACKLOG, scope=sprint.name)
    sprint_backlog.save()


def _create_requirement_with_stories_and_tasks(teh, sprint, start_index):
    "Creates and returns 9 tickets"
    requirement = _create_requirement(teh, "Requirement %d" % start_index)
    for i in (1,2):
        story = _create_story(teh, sprint, "Story %d" % (start_index + 1 * i), requirement)
        _create_task(teh, sprint, "Task %d" % (start_index + 2 * i), story)
        _create_task(teh, sprint, "Task %d" % (start_index + 3 * i), story)
        _create_task(teh, sprint, "Task %d" % (start_index + 4 * i), story)

def _create_requirement(teh, summary):
    return teh.create_ticket(Type.REQUIREMENT, props={
        Key.SUMMARY: summary,
        Key.DESCRIPTION: "Description for %s" % summary,
        Key.BUSINESS_VALUE: '2000'
    })

def _create_story(teh, sprint, summary, requirement=None):
    story = teh.create_ticket(Type.USER_STORY, props={
        Key.SUMMARY: summary,
        Key.DESCRIPTION: "Description for Story %s" % summary,
        Key.STORY_POINTS: "3",
        Key.STORY_PRIORITY: 'Linear',
        Key.SPRINT: sprint.name
    })
    if requirement is not None:
        requirement.link_to(story)
    return story

def _create_task(teh, sprint, summary, story=None):
    task = teh.create_ticket(Type.TASK, props={
        Key.SUMMARY: summary,
        Key.DESCRIPTION: "Description for Story %s" % summary,
        Key.SPRINT: sprint.name
    })
    if story is not None:
        story.link_to(task)
    return task


if __name__ == "__main__":
    sys.exit(main())