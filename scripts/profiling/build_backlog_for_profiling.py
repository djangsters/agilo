#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# This script tries to simulate a normal sprint with several of tickets so that
# we can measure the time to load the backlog page afterwards.. 
# No randomness is used so the results are really reproducible.

# -----------------------------------------------------------------------------
# Configuration

sprint_name = None

number_of_requirements = 3
number_of_stories_per_requirement = 5
number_of_tasks_per_story = 6

number_of_bugs = 5
number_of_tasks_per_bug = 2

number_of_orphan_tasks = 10

# -----------------------------------------------------------------------------

import sys

from trac.env import Environment

from agilo.scrum.backlog import BacklogConfiguration
from agilo.scrum.sprint import SprintModelManager
from agilo.ticket.model import AgiloTicketModelManager
from agilo.utils import Key, Type
from agilo.utils.days_time import now


def create_emtpy_sprint(env):
    assert sprint_name != None, 'Please configure a sprint name.'
    sprint = SprintModelManager(env).create(name=sprint_name,
                                                  start=now(),
                                                  duration=14)
    assert sprint is not None
    t_manager = AgiloTicketModelManager(env)
    for t_id, t_type, t_status in sprint._fetch_tickets():
        ticket = t_manager.create(tkt_id=t_id, t_type=t_type)
        if ticket[Key.SPRINT] == sprint.name:
            ticket[Key.SPRINT] = None
            t_manager.save(ticket, None, 'reset sprint field for performance measurement')

def change_backlog(env):
    backlog_config = BacklogConfiguration(env, name=Key.SPRINT_BACKLOG)
    backlog_config.ticket_types = [Type.REQUIREMENT, Type.USER_STORY, Type.TASK, Type.BUG]
    backlog_config.save()

def _create_requirement_tree(env):
    t_manager = AgiloTicketModelManager(env)
    for req_nr in range(number_of_requirements):
        stories = []
        for story_nr in range(number_of_stories_per_requirement):
            tasks = []
            for task_nr in range(number_of_tasks_per_story):
                task = dict()
                task['t_type'] = Type.TASK
                task[Key.SUMMARY] = 'Task %d.%d.%d' % (req_nr, story_nr, task_nr)
                task[Key.SPRINT] = sprint_name
                t = t_manager.create(**task)
                tasks.append(t)
            story = dict()
            story['t_type'] = Type.USER_STORY
            story[Key.SUMMARY] = 'Story %d.%d' % (req_nr, story_nr)
            story[Key.SPRINT] = sprint_name
            s = t_manager.create(**story)
            for t in tasks:
                s.link_to(t)
            stories.append(s)
        requirement = dict()
        requirement['t_type'] = Type.REQUIREMENT
        requirement[Key.SUMMARY] = 'Requirement %d' % (req_nr)
        r = t_manager.create(**requirement)
        for s in stories:
            r.link_to(s)
    return number_of_requirements * number_of_stories_per_requirement * number_of_tasks_per_story

def _create_orphan_tasks(env):
    t_manager = AgiloTicketModelManager(env)
    for task_nr in range(number_of_tasks_per_bug):
        task = dict()
        task['t_type'] = Type.TASK
        task[Key.SUMMARY] = 'Orphan Task %d' % (task_nr)
        task[Key.SPRINT] = sprint_name
        t_manager.create(**task)
    return number_of_tasks_per_bug

def _create_bug_trees(env):
    t_manager = AgiloTicketModelManager(env)
    for bug_nr in range(number_of_bugs):
        tasks = []
        for task_nr in range(number_of_tasks_per_bug):
            task = dict()
            task['t_type'] = Type.TASK
            task[Key.SUMMARY] = 'Bug Task %d.%d' % (bug_nr, task_nr)
            task[Key.SPRINT] = sprint_name
            t = t_manager.create(**task)
            tasks.append(t)
        bug = dict()
        bug['t_type'] = Type.BUG
        bug[Key.SUMMARY] = 'Bug %d' % (bug_nr)
        bug[Key.SPRINT] = sprint_name
        b = t_manager.create(**bug)
        for t in tasks:
            b.link_to(t)
    return number_of_bugs * number_of_tasks_per_bug

def create_tickets(env):
    nr_tickets = 0
    nr_tickets += _create_orphan_tasks(env)
    nr_tickets += _create_requirement_tree(env)
    nr_tickets += _create_bug_trees(env)
    return nr_tickets


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print 'Usage ', sys.argv[0], ' <environment> [sprint name]'
        print 'Warning: Sprint property will be removed for all tickets in sprint "%s"' % sprint_name
        print 'Furthermore your %s will be reconfigured' % Key.SPRINT_BACKLOG
    else:
        environment_path = sys.argv[1]
        env = Environment(environment_path)
        
        if sprint_name == None and len(sys.argv) > 2:
            sprint_name = sys.argv[2]
        
        create_emtpy_sprint(env)
        change_backlog(env)
        nr_tickets = create_tickets(env)
        print 'Created a sprint with %s tickets' % nr_tickets

