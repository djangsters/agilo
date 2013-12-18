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

from genshi.builder import tag
from trac.core import Component, implements
from trac.util.translation import _
from trac.web.main import IRequestHandler
from trac.web.chrome import add_stylesheet, INavigationContributor

from agilo.charts.chart_generator import ChartGenerator
from agilo.csv_import import IMPORT_URL
from agilo.scrum import DASHBOARD_URL
from agilo.scrum.backlog.controller import BacklogController
from agilo.scrum.backlog.web_ui import BacklogModule
from agilo.scrum.charts import ChartType
from agilo.scrum.sprint import SessionScope
from agilo.utils import Action, Key
from agilo.utils.config import AgiloConfig


# This module is actually not directly tied to the backlog but I found no better
# place for the dashboard and did not want to add another package just for the
# dashboard.

from agilo.utils.widgets import Widget

class FakeWidget(Widget):
    def display(self, **data):
        return ''

class ScrumDashboard(Component):

    implements(IRequestHandler, INavigationContributor)

    def _get_sprint_backlog(self, sprint_name):
        cmd_get = BacklogController.GetBacklogCommand(self.env,
                                                      name=Key.SPRINT_BACKLOG,
                                                      scope=sprint_name)
        cmd_get.native = True
        return BacklogController(self.env).process_command(cmd_get)
        
    #=============================================================================
    # IRequestHandler methods
    #=============================================================================
    def match_request(self, req):
        """Returns the matching url for the dashboard"""
        return req.path_info.startswith(DASHBOARD_URL)
    
    def _add_charts_to_template_data(self, req, current_sprint_name, data):
        if current_sprint_name is None:
            # If we don't have at least one running sprint, we can not display
            # any chart.
            data['burndown'] = FakeWidget(self.env, '')
            data['points'] = FakeWidget(self.env, '')
            data['pie'] = FakeWidget(self.env, '')
            data['ticket_stats'] = FakeWidget(self.env, '')
            return
        cached_data = dict()
        if current_sprint_name not in [None, '']:
            backlog = self._get_sprint_backlog(sprint_name=current_sprint_name)
            cached_data = dict(tickets=backlog)

        # Hour Burndown Chart
        chart_generator = ChartGenerator(self.env)
        get_widget = chart_generator.get_chartwidget
        widget = get_widget(ChartType.BURNDOWN, width=680, height=350,
                            sprint_name=current_sprint_name, cached_data=cached_data)
        widget.prepare_rendering(req)
        data['burndown'] = widget

        # Story Point Burndown Chart
        chart_generator = ChartGenerator(self.env)
        get_widget = chart_generator.get_chartwidget
        widget = get_widget(ChartType.POINT_BURNDOWN, width=680, height=350,
                            sprint_name=current_sprint_name, cached_data=cached_data)
        widget.prepare_rendering(req)
        data['points'] = widget
        
        widget = get_widget(ChartType.SPRINT_RESOURCES_STATS, width=300, height=300,
                            sprint_name=current_sprint_name, cached_data=cached_data)
        widget.prepare_rendering(req)
        data['pie'] = widget
        
        widget = get_widget(ChartType.SPRINT_TICKET_STATS, width=300, height=300,
                            sprint_name=current_sprint_name)
        widget.prepare_rendering(req)
        data['ticket_stats'] = widget
    
    def process_request(self, req):
        """Returns data and template for the Dashboard"""
        req.perm.assert_permission(Action.DASHBOARD_VIEW)
        current_sprint = SessionScope(req, env=self.env).current_sprint()
        current_sprint_name = current_sprint and current_sprint.name or None
        add_stylesheet(req, 'agilo/stylesheet/dashboard.css')
        
        data = {
            'import_url': req.href(IMPORT_URL),
            'current_sprint': current_sprint_name,
            'may_delete_tickets': Action.TICKET_DELETE in req.perm,
            'may_edit_tickets': Action.TICKET_EDIT in req.perm
        }
        self._add_charts_to_template_data(req, current_sprint_name, data)
        
        return 'agilo_dashboard.html', data, None

    #=============================================================================
    # INavigationContributor methods
    #=============================================================================
    def get_navigation_items(self, req):
        if Action.DASHBOARD_VIEW in req.perm:
            dashboard_link = tag.a(_('Dashboard'), href=req.href(DASHBOARD_URL))
            yield ('mainnav', 'dashboard', dashboard_link)
    
    def get_active_navigation_item(self, req):
        return 'dashboard'
