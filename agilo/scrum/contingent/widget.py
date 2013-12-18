# -*- coding: utf-8 -*-
#   Copyright 2007-2009 Agile42 GmbH - Andrea Tomasini
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
#     - Felix Schwarz <felix.schwarz__at__agile42.com>

from trac.ticket.roadmap import TicketGroupStats
from trac.web.chrome import add_stylesheet

from agilo.scrum.contingent.controller import ContingentController, CONTINGENTS_URL
from agilo.utils import Action
from agilo.utils.widgets import Widget


__all__ = ['ContingentWidget']


class ContingentWidget(Widget):
    
    def __init__(self, env, sprint, backlog=False, *args, **kwargs):
        template_filename = 'scrum/contingent/templates/agilo_contingent_widget.html'
        super(ContingentWidget, self).__init__(env, template_filename, *args, **kwargs)
        self.sprint = sprint
        self.backlog = backlog
    
    def get_contingents_for_sprint(self):
        cmd = ContingentController.ListSprintContingentCommand(self.env, sprint=self.sprint)
        return ContingentController(self.env).process_command(cmd)
    
    def calculate_contingent_totals(self):
        cmd = ContingentController.GetSprintContingentTotalsCommand(self.env, sprint=self.sprint)
        return ContingentController(self.env).process_command(cmd)
    
    def build_stats_object_for_roadmap_macro(self, contingent, unit=None):
        """Return a TicketGroupStats instance loaded with the parameters for
        time used vs. time left."""
        stats = TicketGroupStats('used contingent', unit)
        time_left = contingent.amount - contingent.actual
        stats.add_interval('used', contingent.actual, None, 'closed', overall_completion=True)
        stats.add_interval('left', time_left, None, None)
        stats.refresh_calcs()
        used_interval = stats.intervals[0]
        if stats.done_percent > 90:
            used_interval['css_class'] = 'critical'
        elif stats.done_percent > 70:
            used_interval['css_class'] = 'warning'
        return stats
    
    def get_sprint_name(self):
        sprint_name = self.sprint
        if hasattr(self.sprint, 'name'):
            sprint_name = self.sprint.name
        return sprint_name
    
    def prepare_rendering(self, req):
        super(ContingentWidget, self).prepare_rendering(req)
        stats = []
        for contingent in self.get_contingents_for_sprint():
            item = (contingent, self.build_stats_object_for_roadmap_macro(contingent))
            stats.append(item)
        
        add_stylesheet(req, "common/css/roadmap.css")
        self.data['contingents_with_stats'] = stats
        self.data['sprint'] = self.get_sprint_name()
        self.data['backlog'] = self.backlog
        self.data['contingent_totals'] = self.calculate_contingent_totals()
        self.data['CONTINGENTS_URL'] = req.href(CONTINGENTS_URL)
        
        self.data['may_add_actual_time'] = (Action.CONTINGENT_ADD_TIME in req.perm)
        self.data['may_modify_contingents'] = (Action.CONTINGENT_ADMIN in req.perm)

