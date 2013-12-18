# -*- encoding: utf-8 -*-
#   Copyright 2008-2009 Agile42 GmbH, Berlin (Germany)
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
#   Authors: 
#       - Jonas von Poser <jonas.vonposer__at__agile42.com>
#       - Andrea Tomasini <andrea.tomasini__at__agile42.com>
#       - Felix Schwarz <felix.schwarz__at__agile42.com>

from genshi.builder import tag
from pkg_resources import resource_filename
from trac.core import Component, implements
from trac.util.compat import set
from trac.util.datefmt import format_date, format_datetime
from trac.util.translation import _
from trac.web.chrome import add_stylesheet, INavigationContributor, ITemplateProvider

from agilo.api.view import HTTPView
from agilo.charts.chart_generator import ChartGenerator
from agilo.scrum import TEAM_URL
from agilo.scrum.charts import ChartType
from agilo.scrum.team.controller import TeamController
from agilo.ticket.renderers import TimePropertyRenderer, Renderer
from agilo.utils import Action, Key
from agilo.utils.config import get_label
from agilo.utils.days_time import is_working_day


class ListTeamsView(HTTPView):
    
    template = 'agilo_list_teams.html'
    controller_class = TeamController
    url = TEAM_URL
    url_regex = '/?$'
    
    def do_get(self, req):
        req.perm.assert_permission(Action.TEAM_VIEW)
        teams = self.controller.process_command(TeamController.ListTeamsCommand(self.env))
        visible_teams = list()
        for team in teams:
            if req.perm.has_permission(Action.TEAM_VIEW, team.resource):
                visible_teams.append(team)
        data = dict(teams=visible_teams)
        return data


class ListTeamSprintsView(HTTPView):
    
    template = 'agilo_team_sprints.html'
    controller_class = TeamController
    url = TEAM_URL
    url_regex = r'/(?P<name>[^/]+)/?$'
    
    def do_get(self, req):
        # Metrics is higher in the hierarchy
        from agilo.scrum.metrics import MetricsController
        
        add_stylesheet(req, "common/css/report.css")
        get_team = TeamController.GetTeamCommand(self.env, team=req.args['name'])
        team = self.controller.process_command(get_team)
        req.perm.assert_permission(Action.TEAM_VIEW, team.resource)
        
        cmd = MetricsController.ListMetricsCommand(self.env, team=team.name)
        metrics_by_sprint = MetricsController(self.env).process_command(cmd)
        
        available_metrics = self._get_available_metrics(metrics_by_sprint)
        data = {'team': team}
        data['chart_widgets'] = self._get_charts(req, team, available_metrics)
        data['metric_labels'] = [get_label(m) for m in available_metrics]
        data['metric_names'] = available_metrics
        data['sprints'] = self._format_sprint_and_metrics(req, metrics_by_sprint,
                                                          available_metrics, team)
        return data
    
    def _get_available_metrics(self, metrics_by_sprint):
        "Return a list containing the keys of all available metrics"
        available_metrics = set()
        for sprint, metrics in metrics_by_sprint:
            for metrics_name in metrics:
                available_metrics.add(metrics_name)
        return list(available_metrics)
    
    def _get_metric_groups(self, available_metrics):
        # Some metrics are well known and we show them together in one chart.
        # We have the RT_USP ratio separate because of two reasons:
        #  - it has not much to do with the other charts
        #  - the numbers are much lower so we would need to add a second scale 
        #    which is not yet implemented in the team metrics chart.
        chart_groups = [(Key.ESTIMATED_VELOCITY, Key.VELOCITY), 
                        (Key.CAPACITY, Key.COMMITMENT), 
                        (Key.RT_USP_RATIO, )]
        grouped_metrics = []
        [grouped_metrics.extend(i) for i in chart_groups]
        other_metrics = set(available_metrics).difference(set(grouped_metrics))
        other_metrics = [(i,) for i in other_metrics]
        return chart_groups + other_metrics
    
    def _get_charts(self, req, team, available_metrics):
        chart_widgets = []
        
        grouped_metrics = self._get_metric_groups(available_metrics)
        get_widget = ChartGenerator(self.env).get_chartwidget
        for metric_names in grouped_metrics:
            widget = get_widget(ChartType.TEAM_METRICS, team_name=team.name, 
                                metric_names=metric_names)
            widget.prepare_rendering(req)
            chart_widgets.append(widget)
        return chart_widgets
    
    def _format_sprint_and_metrics(self, req, metrics_by_sprint, available_metrics, team):
        def build_url(sprint):
            return TeamSprintPlanningView(self.env).get_url(req, team.name,
                                                            sprint.name)
        
        sprints = []
        for sprint, metrics in metrics_by_sprint:
            sprint.start = format_datetime(sprint.start, tzinfo=req.tz)
            sprint.end = format_datetime(sprint.end, tzinfo=req.tz)
            sprint.metrics = {}
            for name in available_metrics:
                formatted_value = Renderer(metrics.get(name), name, env=self.env).render()
                sprint.metrics[name] = formatted_value
            sprint.url = build_url(sprint)
            sprints.append(sprint)
        return sprints


class TeamSprintPlanningView(HTTPView):
    
    template = 'agilo_team_sprint_planning.html'
    controller_class = TeamController
    url = TEAM_URL
    url_regex = r'/?(?P<team>[^/]+)/(?P<sprint>[^/]+)/?'
    
    def _format_developer_data(self, req, developer):
        render_time = lambda x: TimePropertyRenderer(self.env, x).render()
        if developer.load is not None:
            for load in developer.load:
                load.is_working_day = is_working_day(load.day)
                load.day = format_date(load.day, tzinfo=req.tz)
                load.remaining_time = render_time(load.remaining_time)
        total_capacity = getattr(developer, 'total_capacity', None)
        developer.total_capacity = render_time(total_capacity)
    
    def do_get(self, req):
        from agilo.scrum import SprintController
        
        get_team = TeamController.GetTeamCommand(self.env, team=req.args['team'])
        team = self.controller.process_command(get_team)
        sprint_controller = SprintController(self.env)
        get_sprint = SprintController.GetSprintCommand(self.env, sprint=req.args['sprint'])
        sprint = sprint_controller.process_command(get_sprint)
        
        req.perm.assert_permission(Action.TEAM_VIEW, team.resource)
        # Why don't we have some kind of SPRINT_VIEW permission?
        
        cmd = SprintController.GetResourceLoadForDevelopersInSprintCommand(self.env, sprint=sprint.name)
        data = sprint_controller.process_command(cmd)
        load_totals = data.load_totals
        developers = data.developers
        for developer in developers:
            self._format_developer_data(req, developer)
        
        net_capacity_cmd = SprintController.GetSprintNetCapacityCommand(self.env, sprint=sprint.name)
        net_capacity = sprint_controller.process_command(net_capacity_cmd)
        team.net_capacity = TimePropertyRenderer(self.env, net_capacity).render()
        
        add_stylesheet(req, "common/css/report.css")
        
        from agilo.scrum.contingent import ContingentWidget
        contingent_widget = ContingentWidget(self.env, sprint=sprint)
        contingent_widget.prepare_rendering(req)
        
        data = dict(team=team, sprint=sprint,
                    edit_all   = req.perm.has_permission(Action.TEAM_CAPACITY_EDIT, team.resource),
                    developers = developers,
                    load_totals = load_totals,
                    contingent_widget = contingent_widget,
                   )
        return data
    
    def _extract_member_and_day(self, value):
        # We need to support member names with underscores.
        member, day = value.rsplit('_', 1)
        return member, day
    
    def do_post(self, req):
        req.perm.assert_permission(Action.TEAM_CAPACITY_EDIT)
        
        capacity_member = {}
        for key, value in req.args.items():
            if (not key.startswith('ts_')) or (not value) or ('_' not in key[3:]):
                continue
            member, day = self._extract_member_and_day(key[3:])
            if member not in capacity_member:
                capacity_member[member] = {}
            try:
                capacity_member[member][day] = float(value)
            except ValueError:
                capacity_member[member][day] = 0.0
        
        for m in capacity_member:
            # here is already filtered the m name should exist no need to check?
            tmc = self.controller.tmm_manager.get(name=m).calendar
            for day, value in capacity_member[m].items():
                tmc.set_hours_for_day(value, d_ordinal=day)
            tmc.save()
        
        self.redirect(req, self, req.args['team'], req.args['sprint'])


class TeamModule(Component):
    
    implements(INavigationContributor, ITemplateProvider)
    
    # ITemplateProvider methods
    def get_htdocs_dirs(self):
        return []
    
    def get_templates_dirs(self):
        return [resource_filename('agilo.scrum.team', 'templates')]
    
    # INavigationContributor methods
    def get_navigation_items(self, req):
        if Action.TEAM_VIEW in req.perm:
            team_link = tag.a(_('Teams'), href=req.href(TEAM_URL))
            yield ('mainnav', 'teams', team_link)
        
    def get_active_navigation_item(self, req):
        return 'teams'



