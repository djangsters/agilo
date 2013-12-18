# -*- encoding: utf-8 -*-
#   Copyright 2010 Agile42 GmbH, Berlin (Germany)
#   Copyright 2011 Agilo Software GmbH All rights reserved
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

from agilo.scrum.backlog.json_ui import BacklogAbstractJSONView
from agilo.utils import Action, Key
from agilo.scrum.backlog.model import MissingOrInvalidScopeError
from agilo.charts import ChartGenerator
from agilo.scrum.charts import ChartType
from agilo.utils.config import AgiloConfig

__all__ = ['BurndownValuesView', ]


class BurndownValuesView(BacklogAbstractJSONView):
    url = '/json/sprints'
    url_regex = '/(?P<sprint>.+?)/burndownvalues/?$'
    
    def _get_sprint_backlog(self, req, sprint_name):
        if Action.BACKLOG_VIEW not in req.perm:
            self.error_response(req, '', ['No permission to get burndown for sprint with name: ' + sprint_name])
        try:
            backlog = self._get_backlog(name=Key.SPRINT_BACKLOG, scope=sprint_name)
        except MissingOrInvalidScopeError:
            self.error_response(req, '', ['No Sprint found with name: ' + sprint_name])
        return backlog
    
    def _burndown_widget(self, sprint, backlog, filter_by):
        return ChartGenerator(self.env).get_chartwidget(ChartType.BURNDOWN, 
                    sprint_name=sprint.name, filter_by=filter_by,
                    cached_data=dict(tickets=backlog))
    
    def _filter_by(self, data):
        filter_by = None
        if AgiloConfig(self.env).should_reload_burndown_on_filter_change_when_filtering_by_component:
            filter_by = data.get('filter_by')
        return filter_by
    
    def do_get(self, req, data):
        sprint_name = data['sprint']
        backlog = self._get_sprint_backlog(req, sprint_name)
        sprint = backlog.sprint()
        widget = self._burndown_widget(sprint, backlog, self._filter_by(data))
        widget.prepare_rendering(req)
        return widget.data_as_json()

