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
#       - Andrea Tomasini <andrea.tomasini__at__agile42.com>

from pkg_resources import resource_filename

from genshi.core import Markup

from trac.core import implements, Component
from trac.resource import IResourceManager
from trac.util.datefmt import format_datetime
from trac.util.translation import _
from trac.web.chrome import add_script, add_stylesheet, add_warning, \
    ITemplateProvider

from agilo.api.view import HTTPView
from agilo.charts.chart_generator import ChartGenerator
from agilo.scrum import BACKLOG_URL
from agilo.scrum.backlog.backlog_toggle import BacklogToggleViewInjector
from agilo.scrum.backlog.backlog_toggle_interface import IBacklogToggleViewProvider
from agilo.scrum.backlog.csv_export import add_backlog_conversion_links, send_backlog_as
from agilo.scrum.backlog.model import backlog_resource
from agilo.scrum.backlog.controller import BacklogController
from agilo.scrum.backlog.json_ui import BacklogInfoJSONView, ConfiguredChildTypesView, \
    BacklogJSONView
from agilo.scrum.charts import ChartType
from agilo.scrum.sprint import NoSprintFoundView, SessionScope
from agilo.scrum.sprint.controller import SprintController
from agilo.ticket.model import AgiloMilestone
from agilo.utils import Action, Key, Realm, use_jquery_13
from agilo.utils.compat import json
from agilo.scrum.backlog.backlog_renderer import BacklogRenderer

__all__ = ['BacklogModule', 'BacklogAction', 'NewBacklogView']


class BacklogAction(object):
    """Represent an action for the backlog"""
    CALCULATE = 'calculate'
    CONFIRM = 'confirm'
    DELETE = 'delete'
    EDIT = 'edit'
    REMOVE = 'remove'
    SAVE = 'save'
    SORT = 'sort'
    EDIT_SAVE_SORT = [EDIT, SAVE, SORT]
    EDIT_SAVE_SORT_REMOVE = EDIT_SAVE_SORT + [REMOVE]


class BacklogModule(Component):
    """Represent a Trac Component to manage Backlogs"""

    implements(IResourceManager, ITemplateProvider)

    #=============================================================================
    # ITemplateProvider methods
    #=============================================================================
    def get_htdocs_dirs(self):
        return [('agilo', resource_filename('agilo.scrum.backlog', 'htdocs'))]

    def get_templates_dirs(self):
        return [resource_filename('agilo.scrum.backlog', 'templates')]

    def send_backlog_list_data(self, req, data):
        """add to the data array the backlog data necessary to show
        the backlog list"""
        def milestone_options(milestones, selected):
            """
            Return three lists of tuple (milestone_name, selected) for
            the milestones which are:
                - Open with a due date
                - Open without a due date
                - Closed
            """
            open_with_due_date = list()
            open_without_due_date = list()
            closed = list()
            for m in milestones:
                m_list = None
                if m.is_completed:
                    m_list = closed
                elif m.due:
                    m_list = open_with_due_date
                else:
                    m_list = open_without_due_date
                # append the milestone to the list
                m_list.append((m.name, m.name==selected))

            return open_with_due_date, open_without_due_date, closed

        # Maximum items in the pulldown, ordered by status and by time
        # The number is the maximum per status, so 5 closed, 5 running
        # and 5 to start
        MAX_ITEMS = 5

        milestone_list = None
        if data is not None and Action.BACKLOG_VIEW in req.perm:
            data['sprint_list'] = self.running_to_start_closed_sprints(req)
            cmd_list = BacklogController.ListBacklogsCommand(self.env)
            data['backlog_list'] = \
                BacklogController(self.env).process_command(cmd_list)
            s_milestone = SessionScope(req).milestone_name()
            open_due, open, closed = \
                milestone_options(AgiloMilestone.select(self.env), s_milestone)
            milestone_list = [
                {Key.LABEL: _('Open (by Due Date)'),
                 Key.OPTIONS: open_due},
                {Key.LABEL: _('Open (no Due Date)'),
                 Key.OPTIONS: open},
                {Key.LABEL: _('Closed'),
                 Key.OPTIONS: closed[-MAX_ITEMS:]}]
            data['milestone_list'] = milestone_list

    def running_to_start_closed_sprints(self, req):
        MAX_ITEMS = 5

        def mark_last_viewed_sprint(sprint_names):
            return [(name, name==last_viewed_sprint_name) for \
                               name in sprint_names]

        last_viewed_sprint_name = SessionScope(req).sprint_name()
        # get sprint data
        get_options = SprintController.GetSprintOptionListCommand(self.env)
        closed, running, to_start = \
            SprintController(self.env).process_command(get_options)
        running_sprints = mark_last_viewed_sprint(running)
        ready_to_start_sprints = mark_last_viewed_sprint(to_start[:MAX_ITEMS])
        closed_sprints = mark_last_viewed_sprint(closed[-MAX_ITEMS:])
        # Show last closed sprints at the top
        closed_sprints.reverse()
        sprint_list = [
            {Key.LABEL: _('Running (by Start Date)'),
             Key.OPTIONS: running_sprints},
            {Key.LABEL: _('To Start (by Start Date)'),
             Key.OPTIONS: ready_to_start_sprints},
            {Key.LABEL: _('Closed (by End Date)'),
             Key.OPTIONS: closed_sprints},
        ]
        return sprint_list

    #=============================================================================
    # IResourceManager methods
    #=============================================================================
    def get_resource_realms(self):
        """Return resource realms managed by the component.
        :rtype: `basestring` generator"""
        yield Realm.BACKLOG

    def get_resource_url(self, resource, href, **kwargs):
        """Return the canonical URL for displaying the given resource.

        :param resource: a `Resource`
        :param href: an `Href` used for creating the URL

        Note that if there's no special rule associated to this realm
        for creating URLs (i.e. the standard convention of using
        realm/id applies), then it's OK to not define this method."""
        pass

    def _render_link(self, context, name, label, scope=None):
        """Renders the backlog Link"""
        backlog = self._get_backlog(context, name=name, scope=scope)
        href = context.href(BACKLOG_URL, name, scope)
        if backlog.exists and \
                Action.BACKLOG_VIEW in context.perm(backlog.resource):
            return tag.a(label, class_='backlog', href=href, rel="nofollow")

    def get_resource_description(self, resource, format='default', context=None,
                                 **kwargs):
        """Return a string representation of the resource, according to the
        `format`."""
        desc = resource.id
        if format != 'compact':
            desc =  _('Backlog (%(name)s)', name=resource.id)
        if context:
            return self._render_link(context, resource.id, desc)
        else:
            return desc

    def _get_sprint(self, req, sprint_name):
        """Retrieve the Sprint for the given name"""
        get_sprint = SprintController.GetSprintCommand(self.env,
                                                       sprint=sprint_name)
        sprint = SprintController(self.env).process_command(get_sprint)
        # we need to convert sprint dates into local timezone
        sprint.start = format_datetime(sprint.start, tzinfo=req.tz)
        sprint.end = format_datetime(sprint.end, tzinfo=req.tz)
        if sprint.team is None:
            msg = _("No Team has been assigned to this Sprint...")
            if not msg in req.chrome['warnings']:
                add_warning(req, msg)
        return sprint

    def _get_backlog(self, req, name, scope=None, reload=True, filter_by=None):
        """Retrieve the Backlog with the given name and scope, and sets it as
        default in the session of the user"""
        cmd_get_backlog = \
            BacklogController.GetBacklogCommand(self.env, name=name,
                                scope=scope, reload=reload, filter_by=filter_by)
        backlog = BacklogController(self.env).process_command(cmd_get_backlog)
        SessionScope(req).set_scope(scope, backlog.config.type)
        return backlog


class NewBacklogView(HTTPView):
    """Represent the Backlog view, now most of the UI will be generated using JSON data
    so the template is pretty simple"""
    
    template = 'agilo_backlog.html'
    
    url = BACKLOG_URL
    url_regex = '/(?P<name>[^/]+)(/(?P<scope>[^/]+))?/?$'
    
    implements(IBacklogToggleViewProvider)
    
    # IBacklogToggleViewProvider implementation
    def register_backlog_for_toggling(self, configuration_view):
        configuration_view.register_new_backlog()
    
    # Private methods 
    
    def _get_backlog(self, req):
        scope = req.args.get('scope') or req.args.get('bscope')
        name = req.args['name']
        return BacklogJSONView(self.env)._get_backlog(name=name, scope=scope)
    
    def _configured_child_types(self, req):
        view = ConfiguredChildTypesView(self.env)
        return view.do_get(req, req.args)
    
    def _backlog_configuration(self, backlog):
        return backlog.config.ticket_types
    
    def _configured_columns(self, backlog):
        return dict(
            columns=backlog.config.backlog_column_names(),
            human_readable_names=backlog.config.backlog_human_readable_column_labels(),
        )
    
    def _backlog_information(self, req, backlog):
        backlog_info_view = BacklogInfoJSONView(self.env)
        backlog_info = backlog_info_view.backlog_info_for_backlog(req, backlog)
        # Returning as genshi.Markup so that special chars in json values are not html escaped
        return Markup(json.dumps(backlog_info))
    
    def _assert_can_view_backlog(self, req):
        scope = req.args.get('scope') or req.args.get('bscope')
        name = req.args['name']
        
        resource = backlog_resource(Key.SPRINT_BACKLOG, scope, name)
        req.perm.assert_permission(Action.BACKLOG_VIEW, resource)
    
    def _add_js_and_css_files(self, req):
        use_jquery_13(req)
        scripts = [
            'lib/jquery-ui-1.7.2.custom.min.js',
            'lib/jquery.editinplace.js',
            'lib/jquery.metadata.js',
            'lib/json2.js',
            'lib/tools.expose.js',
            'lib/underscore-min.js',
            'ticket.js',
            'backlog.js',
            'backlogServerCommunicator.js',
            'backlogController.js',
            'backlogView.js',
            'burndown.js',
            'backlogFilter.js',
            'toolbarGenerator.js',
            'contingents.js',
            'messageView.js',
        ]
        for script in scripts:
            add_script(req, 'agilo/js/' + script)
        
        add_stylesheet(req, 'agilo/stylesheet/toolbar.css')
        add_stylesheet(req, 'agilo/stylesheet/newbacklog.css')
        add_stylesheet(req, 'agilo/stylesheet/panel.css')
        add_stylesheet(req, 'agilo/stylesheet/messaging.css')
        BacklogToggleViewInjector(self.env).inject_toggle_view(req)
    
    # REFACT: consider to move this into some shared place?
    # we probably have three repetitions of this already
    # Also this should be configurable via the admin interface
    def _get_and_prepare_burndown_chart_if_neccessary(self, req, backlog):
        if not backlog.is_sprint_backlog():
            return {}
        
        sprint = backlog.sprint()
        get_widget = ChartGenerator(self.env).get_chartwidget
        widget = get_widget(ChartType.BURNDOWN, sprint_name=sprint.name)
        widget.prepare_rendering(req)
        return dict(chart=widget)
    
    def _show_no_sprint_if_necessary(self, req, backlog):
        if (backlog is None) or (backlog.is_sprint_backlog() and not backlog.sprint()):
            req.redirect(NoSprintFoundView.get_url(req))
    
    # Public methods 
    
    def do_get(self, req):
        self._assert_can_view_backlog(req)
        backlog = self._get_backlog(req)
        renderer = BacklogRenderer(self.env, backlog)
        self._show_no_sprint_if_necessary(req, backlog)
        SessionScope(req).set_scope(backlog.scope, backlog.config.type)
        
        if req.args.get('format'):
            send_backlog_as(self.env, req, backlog, req.args['format'])
        self._add_js_and_css_files(req)
        add_backlog_conversion_links(self.env, req, backlog, BACKLOG_URL)
        backlog_info = self._backlog_information(req, backlog)
        chart = self._get_and_prepare_burndown_chart_if_neccessary(req, backlog)
        backlog_table = renderer.get_backlog_table_html(req.href())
        return dict(backlog=backlog,
                    backlog_info=backlog_info,
                    column_names=backlog.config.backlog_column_names(),
                    backlog_table=backlog_table,
                    **chart)
    

