# -*- encoding: utf-8 -*-
#   Copyright 2008-2009 Agile42 GmbH, Berlin (Germany)
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
#   
#   Author: 
#       - Felix Schwarz <felix.schwarz_at_agile42.com>

from trac.util.compat import set

from agilo.charts.chart_generator import ChartGenerator
from agilo.scrum.charts import ChartType
from agilo.scrum.sprint.charts import SprintTicketStatsChartGenerator
from agilo.test import AgiloTestCase
from agilo.utils import Key, Type
from agilo.utils.config import AgiloConfig



class TestCharts(AgiloTestCase):
    def setUp(self):
        self.super()
        sprint_name = 'Test sprint'
        self.sprint = self.teh.create_sprint(name=sprint_name, duration=14)
        default = {
            Key.OWNER : '',
            Key.SUMMARY : "This is an AgiloTicket",
            Key.DESCRIPTION : "This is the description of the ticket...",
            Key.SPRINT : sprint_name,
        }
        # create some Agilo tickets on this sprint
        self.t1 = self.teh.create_ticket(Type.TASK, props=dict(default, **{
            Key.REMAINING_TIME : "10",
            Key.STATUS : 'accepted',
        }))
        self.t2 = self.teh.create_ticket(Type.TASK, props=dict(default, **{
            Key.REMAINING_TIME : "30",
            Key.STATUS : 'new',
        }))
        self.t3 = self.teh.create_ticket(Type.TASK, props=dict(default, **{
            Key.REMAINING_TIME : "20",
            Key.STATUS : 'accepted',
        }))
        self.t4 = self.teh.create_ticket(Type.TASK, props=dict(default, **{
            Key.REMAINING_TIME : "0",
            Key.STATUS : 'closed',
        }))
    
    def testSprintTicketStatsChartUsesAliases(self):
        self.env.compmgr.enabled[SprintTicketStatsChartGenerator] = True
        self.teh.create_ticket(Type.USER_STORY, {Key.SPRINT: self.sprint.name})
        
        get_widget = ChartGenerator(self.env).get_chartwidget
        widget = get_widget(ChartType.SPRINT_TICKET_STATS, sprint_name=self.sprint.name)
        
        chart_labels = set([item[1] for item in widget.data['labels']])
        self.assert_equals(set(['User Story', 'Task']), chart_labels)
    
    def testSprintTicketStatsChartShowsCorrectTotal(self):
        self.env.compmgr.enabled[SprintTicketStatsChartGenerator] = True
        self.teh.create_ticket(Type.USER_STORY, {Key.SPRINT: self.sprint.name})
        
        get_widget = ChartGenerator(self.env).get_chartwidget
        widget = get_widget(ChartType.SPRINT_TICKET_STATS, sprint_name=self.sprint.name)
        
        self.assert_equals(2, len(widget.data['closed']))
        
        task_alias = AgiloConfig(self.env).ALIASES.get(Type.TASK)
        self.assert_equals((1, task_alias), widget.data['labels'][1])
        task_data = zip(widget.data['closed'], widget.data['planned'], widget.data['total'])[1]
        closed, planned, total = [value for (t, value) in task_data]
        # previously we assumed that closed+planned == total which is wrong, so
        # detect this situation here...
        self.assert_not_equals(closed+planned, total)
        self.assert_equals(closed+planned+2, total)

