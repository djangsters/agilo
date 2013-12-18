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

from pkg_resources import resource_filename, resource_string
from agilo.utils.days_time import now

from trac.core import TracError, Component, implements
from trac.timeline.api import ITimelineEventProvider
from trac.perm import IPermissionRequestor
from trac.util import datefmt
from trac.util.datefmt import to_timestamp, localtz
from trac.util.translation import _
from trac.web.chrome import ITemplateProvider, add_link, add_script, \
    add_stylesheet, prevnext_nav
try:
    from trac.web.chrome import Chrome
except:
    pass
from trac.wiki.formatter import format_to

from agilo.api import view
from agilo.utils import Action, Key, log
from agilo.scrum import SPRINT_URL
from agilo.scrum.sprint import SprintController, SprintModelManager
from agilo.scrum.sprint.roadmap import AgiloRoadmapModule
from agilo.scrum.team.model import TeamModelManager

__all__ = ['NoSprintFoundView', 'SprintConfirmView', 'SprintDisplayView',
           'SprintEditView','SprintModule']


class SprintDisplayView(view.HTTPView):
    """
    Represent the Public Display View of a Sprint, showing details of the sprint
    and allowing the user to choose to Edit, Delete or Close this Sprint.
    """
    template = 'agilo_sprint.html'
    controller_class = SprintController
    url = SPRINT_URL
    url_regex = '/(?P<name>[^/]+)/?$'
    
    def prepare_data(self, req, args, data=None):
        """Returns the sprint visualization data"""
        if not args:
            raise TracError("You should provide at least a sprint name: ",
                            args)
        # Assuming there is a sprint name
        name = args.get('name')
        
        if data is None:
            data = {}
        # avoid circular import
        from agilo.scrum.backlog.web_ui import NewBacklogView
        data.update({
            'may_edit_sprint': Action.SPRINT_EDIT in req.perm,
            # show a deletion confirmation if user wanted to delete
            'delete_confirmation': 'delete' in req.args,
            'close_confirmation': 'close' in req.args,
            'edit_form_action': req.href(SprintEditView.url, 
                                         name, 'edit'),
            'confirm_form_action': req.href(SprintConfirmView.url, 
                                            name, 'confirm'),
            'sprint_backlog_link': req.href(NewBacklogView.url,
                                            Key.SPRINT_BACKLOG, name)
        })
        list_sprints = \
            SprintController.ListSprintsCommand(self.env,
                                                criteria={'name': '!=%s' % name})
        data['sprints'] = [s.name for s in \
                           self.controller.process_command(list_sprints)]
        # Generate the date converter function for this timezone
        convert_date = view.generate_converter(req.tz)
        get_sprint = SprintController.GetSprintCommand(self.env,
                                                       sprint=name)
        sprint = self.controller.process_command(get_sprint)
        # update the sprint dates
        sprint.start = convert_date(sprint.start)
        sprint.end = convert_date(sprint.end)
        # update the data with the Sprint info
        data.update({'sprint': sprint})
        # now get the sprint ticket statistics
        cmd_stats = SprintController.GetTicketsStatisticsCommand(self.env,
                                                                 sprint=name,
                                                                 totals=True)
        nr_new, nr_planned, nr_closed = self.controller.process_command(cmd_stats)
        data['planned_tickets'] = nr_new
        data['in_progres_tickets'] = nr_planned
        data['open_tickets'] = nr_new + nr_planned
        data['closed_tickets'] = nr_closed
        
        rm = AgiloRoadmapModule(self.env)
        data['sprint_stats'] = rm.build_sprint_story_statistics(req, name)
        
        sprint_dates = {'start': sprint.start,
                        'end': sprint.end,
                        'duration': sprint.duration}
        
        if sprint.is_closed:
            data['date_info'] = "Ended the %(end)s. Duration %(duration)s days (started the %(start)s)" % \
                                    sprint_dates
        elif sprint.is_currently_running:
            data['date_info'] = "Started the %(start)s, ends on the %(end)s." % \
                                    sprint_dates
        else:
            data['date_info'] = "Starts the %(start)s. Duration %(duration)s days, ends on the %(end)s" % \
                                    sprint_dates
        return data
    
    def _add_links_to_navigation_bar(self, req, sprint):
        milestone = sprint.milestone
        previous_sprint = milestone.get_previous_sprint(sprint)
        next_sprint = milestone.get_next_sprint(sprint)
        if previous_sprint is not None:
            add_link(req, 'prev', previous_sprint.url())
        if next_sprint is not None:
            add_link(req, 'next', next_sprint.url())
        add_link(req, 'up', milestone.url(), 'Milestone')
        prevnext_nav(req, 'Sprint', 'Milestone')
    
    def _prepare_links(self, req, name, milestone):
        """Prepares the links for the navigation bar"""
        list_sprints = SprintController.ListSprintsCommand(self.env,
                                                           criteria={'milestone': name})
        sprints = self.controller.process_command(list_sprints)
        for i, s in enumerate(sprints):
            s = s['sprint']
            if s['name'] == name:
                if i > 0:
                    add_link(req, 'prev', 
                             self.href(sprints[i - 1]['sprint']['name']))
                if i < len(sprints) - 1:
                    add_link(req, 'next', 
                             self.href(sprints[i + 1]['sprint']['name']))
                break
        # add back link to Milestone
        if milestone:
            add_link(req, 'up', req.href.milestone(milestone), 
                     'Milestone')
        prevnext_nav(req, 'Sprint', 'Milestone')
    
    def do_get(self, req):
        """Returns the data processed via GET handler"""
        if Action.SPRINT_VIEW in req.perm:
            name = req.args.get('name')
            milestone = req.args.get('milestone')
            # Prepares the links for the context navigation
            self._prepare_links(req, name, milestone)
            # add styles to the request
            add_stylesheet(req, "common/css/roadmap.css")
            # Return the sprint show if nothing else happened
            return self.prepare_data(req, {'name': name, 
                                           'milestone': milestone})


class SprintConfirmView(SprintDisplayView):
    """
    Represent a Sprint confirmation view, used when there is the need to ask
    user confirmation, in this case for deleting and retargeting open tickets
    """
    url = SPRINT_URL
    controller_class = SprintController
    template = 'agilo_sprint_confirm.html'
    url_regex = r'/((?P<name>[^/]+)/(?P<action>confirm))/?$'
    
    def _get_name_action(self, req):
        """Return the name and action parameters from the req"""
        name = req.args.get('name')
        action = req.args.get('action')
        log.debug(self, "Processing request: action:%s name:%s" % \
              (action, name))
        return name, action
    
    def do_get(self, req):
        """Process the GET request"""
        if Action.SPRINT_EDIT in req.perm:
            name, action = self._get_name_action(req)
            
            if action == 'confirm' and not name:
                raise TracError(_("Please provide a Sprint Name"))
            
            return self.prepare_data(req, {'name': name})
    
    def do_post(self, req):
        """Process the POST request"""
        if Action.SPRINT_EDIT in req.perm:
            name, action = self._get_name_action(req)
            
            if 'cancel' in req.args:
                # the user changed idea, send him back to the DisplayView
                self.redirect(req, SprintDisplayView, name)
            elif 'sure':
                # the user hit confirm button and is sure to go forward
                really = req.args.get('really')
                if really == 'Delete':
                    self._do_delete(req, name)
                elif really == 'Close':
                    self._do_close(req, name)
    
    def _do_retarget(self, req, name):
        """Perform a retarget if selected in the request"""
        retarget = req.args.get('retarget')
        if retarget:
            cmd_retarget = SprintController.RetargetTicketsCommand(self.env,
                                                                   sprint=name,
                                                                   retarget=retarget,
                                                                   author=req.authname)
            self.controller.process_command(cmd_retarget)
    
    def _do_delete(self, req, name):
        """Deletes and retarget tickets to a new sprint if specified"""
        self._do_retarget(req, name)
        cmd_delete = SprintController.DeleteSprintCommand(self.env,
                                                          sprint=name)
        self.controller.process_command(cmd_delete)
        req.redirect(req.href.roadmap())
    
    def _do_close(self, req, name):
        """Closes a sprint and update metrics"""
        self._do_retarget(req, name)
        from agilo.scrum.team.controller import TeamController
        cmd_store_velocity = TeamController.StoreTeamVelocityCommand(self.env,
                                                                     sprint=name)
        TeamController(self.env).process_command(cmd_store_velocity)
        return req.redirect(req.href.roadmap())


class SprintEditView(view.HTTPView):
    """
    Represent a Sprint Edit View, a form where a user can either edit an
    existing Sprint object or create a new one.
    """
    url = SPRINT_URL
    controller_class = SprintController
    template = 'agilo_sprint_edit.html'
    url_regex = '/' + \
        '(?:' + '(?P<name>[^/]+)/' + '(?P<edit>edit))' + \
        '|' + \
        '(?:' + '(?P<add>add)/(?P<url_milestone>[^\?]+)' + ')' + \
        '/?$'
    
    def _extract_params(self, req):
        # This will give priority to a rename in case of change
        name = req.args.get('name')
        if name is None:
            name = req.args.get('sprint_name')
        milestone = req.args.get('milestone') or req.args.get('url_milestone')
        action = req.args.get('edit') or req.args.get('add')
        log.debug(self, "Processing request: action:%s name:%s milestone:%s" % \
              (action, name, milestone))
        if action == 'edit':
            if not name:
                raise TracError(_("Please provide a Sprint Name"))
            elif 'save' in req.args and not milestone:
                raise TracError(_("Please provide a Milestone Name"))
        elif action == 'add' and not milestone:
            raise TracError(_("Please provide a Milestone Name"))
        return name, milestone, action
    
    def _get_sprint(self, req, name):
        cmd_get = SprintController.GetSprintCommand(self.env, sprint=name)
        return self.controller.process_command(cmd_get, date_converter=view.generate_converter(req.tz))
    
    def do_get(self, req):
        req.perm.assert_permission(Action.SPRINT_EDIT)
        name, milestone, action = self._extract_params(req)
        data = {}
        if action == 'edit':
            sprint = self._get_sprint(req, name)
            if sprint:
                data.update({'sprint': sprint})
        elif action == 'add':
            data.update({'milestone': milestone})
        # add styles to the request
        add_stylesheet(req, "common/css/roadmap.css")
        try:
            Chrome(self.env).add_jquery_ui(req)
        except:
            pass
        # if is a get, just show the form
        return self.prepare_data(req, data)
    
    def _prepare_params(self, req, name=None, sprint=None):
        # Convert the date value into datetime in UTC
        start = self._parse_date_value(req, req.args.get('start'))
        end = self._parse_date_value(req, req.args.get('end'))
        params = dict(milestone=req.args.get('milestone') or None,
                      start=start,
                      end=end,
                      duration=req.args.get('duration') or None,
                      description=req.args.get('description') or None,
                      team=req.args.get('team') or None)
        if name:
            params['name'] = req.args.get('sprint_name') or name
        elif sprint:
            params['sprint'] = req.args.get('sprint_name')
            params['old_sprint'] = sprint
        # Store data in session to preserve them in case of failure
        data = params.copy()
        data['start'] = req.args.get('start')
        data['end'] = req.args.get('end')
        data = self.prepare_data(req, {'sprint': data})
        self.store_data_in_session(req, data)
        return params
    
    def do_post(self, req):
        """Process the POST request"""
        name, milestone, action = self._extract_params(req)
        # Make sure the guy has the right to do this
        req.perm.assert_permission(Action.SPRINT_EDIT)
        if action == 'add':
            return self._do_create(req, name)
        elif action == 'edit' and 'save' in req.args:
            return self._do_save(req, name)
        else:
            # most likely cancel
            return self.redirect(req, SprintDisplayView(self.env), name)
    
    def _do_create(self, req, name):
        """Creates a sprint getting data from the post request"""
        params = self._prepare_params(req, name=name)
        cmd_create = SprintController.CreateSprintCommand(self.env, **params)
        self.controller.process_command(cmd_create)
        return self.redirect(req, SprintDisplayView(self.env), name)
    
    def _do_save(self, req, name):
        """Saves the sprint with the given name"""
        params = self._prepare_params(req, sprint=name)
        cmd_save = SprintController.SaveSprintCommand(self.env, **params)
        self.controller.process_command(cmd_save)
        sprint, old_sprint = params['sprint'], params['old_sprint']
        if sprint and old_sprint and sprint != old_sprint:
            name = sprint
        return self.redirect(req, SprintDisplayView(self.env), name)

    def _user_readable_timezone_from_request(self, req):
        if req.tz != localtz:
            return str(req.tz)

        now_in_localtz = now(tz=localtz)
        return "GMT%s (Default timezone)" % now_in_localtz.strftime("%z")

    def prepare_data(self, req, data=None):
        """Prepares the form to edit a sprint"""
        # Get the team list from the team controller
        from agilo.scrum.team.controller import TeamController
        cmd_team_list = TeamController.ListTeamsCommand(self.env)
        if data is None:
            data = {}
        if not data.get('milestone'):
            data['milestone'] = req.args.get('milestone', '')
        data.update({
            'teams': [t.name for t in \
                      TeamController(self.env).process_command(cmd_team_list)],
            'datetime_hint': datefmt.get_datetime_format_hint(),
            'redirect': req.args.get('redirect'),
            'timezone_of_sprint': self._user_readable_timezone_from_request(req)
        })
        add_script(req, 'common/js/wikitoolbar.js')
        return data


# REFACT: it seems wasteful to have to create a new view with template for each explanation that needs showing
# See: agilo_common.licensing.NoValidLicenseView
# I'd imagine a MessageView that I just parametrize with the right message
# (or something on HTTPView that makes it easy to show a nice error message)
class NoSprintFoundView(view.HTTPView):
    url = '/sprints/no-sprint-found'
    url_regex = ''
    
    template = 'agilo_no_sprint_found.html'
    
    def do_get(self, req):
        utf8_string = resource_string('agilo.scrum.sprint', 'no_sprint_found_explanation.txt')
        explanation = utf8_string.decode('UTF-8')
        return {'explanation': explanation}


class SprintModule(Component):
    """Module to handle Sprint objects"""
    
    implements(ITemplateProvider, ITimelineEventProvider, IPermissionRequestor)

    def __init__(self, *args, **kwargs):
        """Sets a SprintModelManager"""
        super(SprintModule, self).__init__(*args, **kwargs)
        self.sp_manager = SprintModelManager(self.env)
        self.tm_manager = TeamModelManager(self.env)
        
    #=============================================================================
    # IPermissionRequestor methods
    #=============================================================================
    def get_permission_actions(self):
        actions = [Action.SPRINT_VIEW, Action.SPRINT_EDIT]
        return actions + [(Action.SPRINT_ADMIN, actions)]
    
    #=============================================================================
    # ITemplateProvider methods
    #=============================================================================
    def get_htdocs_dirs(self):
        return []
    
    def get_templates_dirs(self):
        return [resource_filename('agilo.scrum.sprint', 'templates')]
    
    #==========================================================================
    # ITimelineEventProvider methods
    #==========================================================================
    def get_timeline_filters(self, req):
        if Action.SPRINT_VIEW in req.perm:
            yield (Key.SPRINT, 'Sprints')

    def get_timeline_events(self, req, start, stop, filters):
        if Key.SPRINT not in filters:
            return
        # prepare select criteria
        criteria = {'start': '>=%d' % to_timestamp(start),
                    'start': '<=%d' % to_timestamp(stop)}
        for sprint in self.sp_manager.select(criteria=criteria):
            # the first value of the data tuple tells if we're showing
            # a start or an end date (True=start, False=end), see next function
            if sprint.is_currently_running:
                yield(Key.SPRINT, sprint.start, '', (True, sprint))
            if sprint.is_closed:
                yield(Key.SPRINT, sprint.end, '', (False, sprint))

    def render_timeline_event(self, context, field, event):
        (start, sprint) = event[3]
        if field == 'url':
            return context.href.sprint(sprint.name)
        elif field == 'title':
            if start:
                return tag('Sprint ', tag.em(sprint.name), ' started')
            return tag('Sprint ', tag.em(sprint.name), ' finished')
        elif field == 'description':
            return format_to(self.env, None, context(resource=sprint),
                             sprint.description)
    

