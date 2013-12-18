# -*- coding: utf-8 -*-
#   Copyright 2007-2008 Agile42 GmbH - Andrea Tomasini
#   Copyright 2011 Agilo Software GmbH All rights reserved 
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
# 
# Authors:
#     - Andrea Tomasini <andrea.tomasini__at__agile42.com>

from trac.core import implements
from trac.web.main import IRequestHandler
from trac.ticket.roadmap import DefaultTicketGroupStatsProvider, RoadmapModule,\
    TicketGroupStats
from trac.util import datefmt
from trac.util.text import to_unicode
from trac.util.translation import _

from agilo.scrum import SPRINT_URL
from agilo.scrum.sprint import SprintController
from agilo.utils import Action, Key, Status
from agilo.utils.config import AgiloConfig
from agilo.utils.log import error


# Add links to add sprints to Trac roadmap
class AgiloRoadmapModule(RoadmapModule):
    implements(IRequestHandler)
    
    def __init__(self):
        """Initialize a Sprint Controller"""
        self.controller = SprintController(self.env)
    
    # --------------------------------------------------------------------------
    # Felix Schwarz, 11.10.2008: Copied from trac.ticket.roadmap (0.11), we
    # initially needed our own copy of that because we want to filter the ticket 
    # by sprint name and not by milestone name. Now we want to filter by type, too.
    def _build_sprint_stats_data(self, req, stat, sprint_name, grouped_by='component', 
                                 group=None, type_names=None):
        all_type_names = AgiloConfig(self.env).get_available_types()
        
        def query_href(extra_args):
            args = {'sprint': sprint_name, grouped_by: group, 
                    'group': 'status'}
            # custom addition to show only certain types
            if type_names != None:
                if len(type_names) == 1:
                    args[Key.TYPE] = type_names[0]
                elif len(type_names) > 1:
                    uninteresting_types = set(all_type_names).difference(set(type_names))
                    args[Key.TYPE] = ['!' + name for name in uninteresting_types]
            # end of custom addition
            args.update(extra_args)
            return req.href.query(args)
        
        return {'stats': stat,
                'stats_href': query_href(stat.qry_args),
                'interval_hrefs': [query_href(interval['qry_args'])
                                   for interval in stat.intervals]}
    # --------------------------------------------------------------------------

    def _build_story_statistics(self, req, stats_provider, sprint_name):
        """
        Assemble statistics for all stories in the given sprint_name so 
        that the progress bar can be displayed.
        """
        sprint_stats = dict()
        
        if not sprint_name:
            return sprint_stats
        
        cmd_get_stories = SprintController.ListTicketsHavingPropertiesCommand(self.env,
                                                                              sprint=sprint_name,
                                                                              properties=[Key.STORY_POINTS])
        stories = self.controller.process_command(cmd_get_stories)
        type_dict = dict()
        closed_stories = list()
        inprogress_stories = list()
        for story in stories:
            if story[Key.STATUS] == Status.CLOSED:
                closed_stories.append(story)
            elif story[Key.STATUS] != Status.NEW:
                inprogress_stories.append(story)
            type_dict[story[Key.TYPE]] = True
        type_names = type_dict.keys()
        number_open_stories = len(stories) - (len(closed_stories) + \
                                              len(inprogress_stories))
        
        try:
            stat = TicketGroupStats('User Stories status', 'stories')
            stat.add_interval(_('Completed'), len(closed_stories), 
                              qry_args={Key.STATUS: Status.CLOSED},
                              css_class='closed', overall_completion=True)
            stat.add_interval(_('In Progress'), len(inprogress_stories), 
                              qry_args={Key.STATUS: Status.ACCEPTED},
                              css_class='inprogress')
            stat.add_interval(_('Open'), number_open_stories, 
                              qry_args={Key.STATUS: [Status.NEW, 
                                                     Status.REOPENED]},
                              css_class='open')
            stat.refresh_calcs()
            sprint_stats = self._build_sprint_stats_data(req, stat, sprint_name, 
                                                         type_names=type_names)
        except Exception, e:
            # The DB is closed? And we don't break for statistics
            error(stats_provider, "ERROR: %s" % to_unicode(e))
        return sprint_stats 
    
    # Some kind of public API. On the one hand this very similar to a Command 
    # but on the other hand a command/controller should know nothing about the 
    # output media (e.g. requests/links) which we need to build the progress 
    # bar.
    def build_sprint_story_statistics(self, req, sprint_name, provider=None):
        if provider is None:
            provider = DefaultTicketGroupStatsProvider(self.env)
        return self._build_story_statistics(req, provider, sprint_name)
    
    def _group_sprints_by_milestone(self, req, milestones_to_show):
        """
        Returns a dict which holds the sprints grouped by milestone 
        (key: milestone, value: list of tuples (sprint, progress bar data)).
        The dict contains only sprints for milestones in milestones_to_show.
        """
        # save sprints in dictionary, key is the associated milestone
        provider = DefaultTicketGroupStatsProvider(self.env)
        
        milestone_names = [milestone.name for milestone in milestones_to_show]
        
        sprints = {}
        sp_controller = SprintController(self.env)
        list_sprints = SprintController.ListSprintsCommand(self.env,
                                                           criteria={'milestone': 'in %s' % \
                                                                     milestone_names})
        for s in sp_controller.process_command(list_sprints):
#            milestone_name = sprint.milestone
#            if (not milestone_name) or (milestone_name not in milestone_names):
#                continue
            milestone_name = s.milestone
            if milestone_name not in sprints:
                sprints[milestone_name] = []
            sprint_stats = self.build_sprint_story_statistics(req, s.name,
                                                              provider=provider)
            sprint_data = (s, sprint_stats)
            sprints[milestone_name].append(sprint_data)
        return sprints
    
    # IRequestHandler methods
    def process_request(self, req):
        template, data, content_type = super(AgiloRoadmapModule, self).process_request(req)
        # user has permission to add and edit sprints
        data.update( {'may_edit_sprint' : Action.SPRINT_EDIT in req.perm})
        
        # Trac already filtered the milestones to show - we don't need to 
        # build the sprint statistics for all milestones
        milestones = data['milestones']
        
        sprints = self._group_sprints_by_milestone(req, milestones)
        
        data.update({
            'sprints' : sprints,
            'sprint_url' : req.href(SPRINT_URL),
            'format_datetime' : datefmt.format_datetime,
        })
        return 'agilo_roadmap.html', data, content_type

