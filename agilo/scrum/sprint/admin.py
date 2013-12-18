# -*- coding: utf-8 -*-
#   Copyright 2008 Agile42 GmbH, Berlin (Germany)
#   Copyright 2007 Andrea Tomasini <andrea.tomasini__at__agile42.com>
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
#    Authors: 
#         Andrea Tomasini <andrea.tomasini__at__agile42.com>
#         Jonas von Poser <jonas.vonposer__at__agile42.com>

from trac.core import TracError
from trac.util import datefmt
from trac.util.translation import _
from trac.ticket.model import Milestone
from trac.web.chrome import add_warning, add_script

from agilo.api.admin import AgiloAdminPanel
from agilo.scrum.sprint.model import SprintModelManager
from agilo.scrum.team import TeamModelManager


class SprintAdminPanel(AgiloAdminPanel):
    """
    Administration panel for sprints.
    """
    
    _type = 'sprints'
    _label = ('Sprints', _('Sprints'))

    def __init__(self):
        # Create an instance of Sprint Manager
        self.sm = SprintModelManager(self.env)
        self.tm = TeamModelManager(self.env)

    def _parse_args(self, req):
        start = req.args.get('start')
        if start:
            start = datefmt.parse_date(start, tzinfo=req.tz)
        end = req.args.get('end')
        if end:
            end = datefmt.parse_date(end, tzinfo=req.tz)
        duration = req.args.get('duration')
        if duration:
            try:
                duration = int(duration)
            except ValueError:
                duration = None
                
        return start, end, duration

    def detail_save_view(self, req, cat, page, name):
        sprint = self.sm.get(name=name)
        if not sprint or not sprint.exists:
            return req.redirect(req.href.admin(cat, page))

        new_name = req.args.get('name')
        # if necessary, rename sprint
        if sprint.name != new_name:
            new_sprint = self.sm.get(name=new_name)
            if new_sprint and new_sprint.exists:
                add_warning(req, 'A sprint with this name already exists - cannot rename.')
                return self.detail_view(req, cat, page, name)
            if '/' in new_name:
                add_warning(req, 'Please don\'t use "/" in a sprint name.')
                return self.detail_view(req, cat, page, name)
        
        sprint.name = new_name
        sprint.description = req.args.get('description')
        sprint.milestone = req.args.get('milestone')
        
        team_name = req.args.get('team')
        team = None
        if team_name:
            team = self.tm.get(name=team_name)
            if not team or not team.exists:
                add_warning(req, u"Invalid team name, that team doesn't exist.")
                return self.detail_view(req, cat, page, name)
        sprint.team = team
        
        start, end, duration = self._parse_args(req)
        
        if start and start != sprint.start:
            if (end and duration) or (not end and not duration):
                add_warning(req, 'Please enter an end date OR a duration.')
                return self.detail_view(req, cat, page, name)
            sprint.start = start
            
        if end and end != sprint.end:
            if (start and duration) or (not start and not duration):
                add_warning(req, 'Please enter a start date OR a duration.')
                return self.detail_view(req, cat, page, name)
            sprint.end = end
        
        if duration and duration != sprint.duration:
            if (start and end) or (not start and not end):
                add_warning(req, 'Please enter an start date OR an end date.')
                return self.detail_view(req, cat, page, name)
            sprint.duration = duration
            
        self.sm.save(sprint)
        req.redirect(req.href.admin(cat, page))

    def detail_view(self, req, cat, page, name):
        sprint = self.sm.get(name=name)
        if not sprint or not sprint.exists:
            return req.redirect(req.href.admin(cat, page))

        data = {
            'view': 'detail',
            'sprint': sprint,
            'teams': self.tm.select(),
            'format_datetime': datefmt.format_datetime,
            'date_hint': datefmt.get_date_format_hint(),
            'datetime_hint': datefmt.get_datetime_format_hint(),
            'milestones': [m.name for m in Milestone.select(self.env)],
        }
        data.update(req.args)
        add_script(req, 'common/js/wikitoolbar.js')
        return 'agilo_admin_sprint.html', data
    
    def list_view(self, req, cat, page):
        data = {
            'view': 'list',
            'sprints': self.sm.select(),
            'format_datetime' : datefmt.format_datetime,
            'date_hint' : datefmt.get_date_format_hint(),
            'datetime_hint' : datefmt.get_datetime_format_hint(),
            'milestones' : [m.name for m in Milestone.select(self.env)],
        }
        data.update(req.args)
        return 'agilo_admin_sprint.html', data

    def list_save_view(self, req, cat, page):
        name = req.args.get('name')
        start, end, duration = self._parse_args(req)

        if req.args.get('add'):
            if not name:
                add_warning(req, 'Please enter a sprint name.')
                return self.list_view(req, cat, page)
            if '/' in name:
                add_warning(req, 'Please do not use "/" in a sprint name.')
                return self.list_view(req, cat, page)

            sprint = self.sm.create(name=name, save=False)
            if not sprint:
                # sprint already exists, redirect to it
                req.redirect(req.href.admin(cat, page, name))

            if not start and not end and not duration:
                add_warning(req, 'Not enough data to set a sprint.')
                return self.list_view(req, cat, page)
                
            if start:
                if (end and duration) or (not end and not duration):
                    add_warning(req, 'Please enter an end date OR a duration.')
                    return self.list_view(req, cat, page)
                sprint.start = start
                
            if end:
                if (start and duration) or (not start and not duration):
                    add_warning(req, 'Please enter an start date OR a duration.')
                    return self.list_view(req, cat, page)
                sprint.end = end
            
            if duration:
                if (start and end) or (not start and not end):
                    add_warning(req, 'Please enter an start date OR an end date.')
                    return self.list_view(req, cat, page)
                sprint.duration = duration

            sprint.milestone = req.args.get('milestone')
            self.sm.save(sprint)

        # Remove components
        if req.args.get('remove'):
            sel = req.args.get('sel')
            if not sel:
                raise TracError(_('No sprint selected'))
            if not isinstance(sel, list):
                sel = [sel]
            for name in sel:
                # TODO: relocate not closed ticket to another Sprint
                sprint = self.sm.get(name=name)
                if sprint:
                    self.sm.delete(sprint)

        req.redirect(req.href.admin(cat, page))

