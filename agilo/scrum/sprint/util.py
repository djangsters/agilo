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
#   Authors: 
#       - Felix Schwarz <felix.schwarz__at__agile42.com>

from agilo.utils import BacklogType
from agilo.scrum.sprint.model import SprintModelManager

__all__ = ['SessionScope']


class SessionScope(object):
    
    def __init__(self, req, env=None):
        self.req = req
        self.env = env
    
    # internal
    
    def key(self, backlog_type):
        return 'agilo-%s-scope' % backlog_type
    
    # public
    
    def scope(self, backlog_type):
        return self.req.session.get(self.key(backlog_type))
    
    def set_scope(self, scope, backlog_type):
        if scope is not None:
            old_scope = self.scope(backlog_type)
            if scope != old_scope:
                self.req.session[self.key(backlog_type)] = scope
    
    def reset_scope(self, backlog_type):
        """Resets any Agilo preset session scope, used in case a 
        stored value proves invalid"""
        if self.req.session.has_key(self.key(backlog_type)):
            del self.req.session[self.key(backlog_type)]
    
    def sprint_name(self):
        """Returns the sprint name stored in the session"""
        return self.scope(BacklogType.SPRINT)
    
    def set_sprint_name(self, sprint_name):
        """Stores the sprint name in the session"""
        self.req.session[self.key(BacklogType.SPRINT)] = sprint_name
    
    def reset_sprint_scope(self):
        self.reset_scope(BacklogType.SPRINT)
    
    def milestone_name(self):
        """Returns the milestone name stored in the session"""
        return self.scope(BacklogType.MILESTONE)
    
    def reset_milestone_scope(self):
        self.reset_scope(BacklogType.MILESTONE)
    
    def sprint(self):
        """Return a sprint object from the session, if that fails, reset the
        sprint scope in the session and return None."""
        assert self.env is not None
        # AT: It is not stated that the current name of sprint set in
        # the session is still there or valid, we need to check it
        sprint = SprintModelManager(self.env).get(name=self.sprint_name())
        if sprint is None:
            self.reset_sprint_scope()
        return sprint
    
    def _currently_running_sprint(self):
        running_sprints = []
        for sprint in SprintModelManager(self.env).select():
            if not sprint.is_currently_running:
                continue
            running_sprints.append(sprint)
        if len(running_sprints) == 0:
            return None
        return running_sprints[-1]
    
    def current_sprint(self):
        """Get the last visited sprint from the session or the currently running
        sprint. Return None if no sprint could be found."""
        sprint = self.sprint()
        if sprint is None:
            return self._currently_running_sprint()
        return sprint

