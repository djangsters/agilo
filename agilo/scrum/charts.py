# -*- encoding: utf-8 -*-
#   Copyright 2008 Agile42 GmbH, Berlin (Germany)
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

# I made yet another class (besides Widget and FlotChartWidget) because this
# widget class needs to import some scrum model objects. 
# In order to keep at least some layering I don't think some module from 
# agilo.utils should depend directly on some scrum related objects. 

from pkg_resources import resource_filename

from agilo.charts import FlotChartWidget

__all__ = ['ChartType', 'ScrumFlotChartWidget']


# Please note that this object is just there for convenience so that other 
# modules can use a constant instead of a string. However charts are found using
# Trac's ExtensionPoint mechanism so adding a new item here will not do anything.
class ChartType(object):
    BURNDOWN = 'burndown'
    POINT_BURNDOWN = "points"
    RELEASE_BURNDOWN = 'release'
    SPRINT_TICKET_STATS = 'sprint_tickets'
    SPRINT_RESOURCES_STATS = 'sprint_resources'
    TEAM_METRICS = 'team_metrics'


class ScrumFlotChartWidget(FlotChartWidget):
    
    def _get_prefetched_backlog(self):
        backlog = None
        if 'cached_data' in self.data and 'tickets' in self.data['cached_data']:
            backlog = self.data['cached_data']['tickets']
            backlog.filter_by = self.data.get('filter_by', None)
        return backlog
    
    def _load_sprint(self, sprint_name, native=False):
        sprint = None
        error_message = None
        if sprint_name == None:
            error_message = 'No sprint specified'
        else:
            try:
                # Charts are a layer below the Sprint so they must not import this
                # module globally to avoid recursive imports
                from agilo.scrum.sprint import SprintController
                cmd = SprintController.GetSprintCommand
                cmd_get_sprint = cmd(self.env, sprint=sprint_name)
                cmd_get_sprint.native = native
                sprint = SprintController(self.env).process_command(cmd_get_sprint)
            except Exception, e:
                error_message = 'Sprint %s does not exist' % unicode(e)
                sprint = None
        if error_message != None:
            self.data['error_message'] = error_message
        return sprint
    
    def _get_all_widget_template_directories(self):
        directories = self.super()
        directories.append(resource_filename('agilo.charts', 'templates'))
        return directories
    
