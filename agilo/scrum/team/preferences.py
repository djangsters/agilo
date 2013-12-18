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

from datetime import datetime

from trac.core import Component, implements
from trac.util.translation import _
from trac.prefs.api import IPreferencePanelProvider

from agilo.charts.chart_generator import ChartGenerator
from agilo.utils.days_time import AgiloCalendar
from agilo.utils.permissions import Role
from agilo.scrum.team import TeamModelManager, TeamMemberModelManager


class AgiloPreferences(Component):
    
    implements(IPreferencePanelProvider)
    
    def __init__(self, *args, **kwargs):
        super(AgiloPreferences, self).__init__(*args, **kwargs)
        self.tmm = TeamModelManager(self.env)
        self.tmmm = TeamMemberModelManager(self.env)
    
    #=============================================================================
    # IPreferencePanelProvider methods
    #=============================================================================
    def get_preference_panels(self, req):
        """Return a list of available preference panels.
        
        The items returned by this function must be tuple of the form
        `(panel, label)`.
        """
        if req.authname is not None and req.authname != 'anonymous' and \
                Role.TEAM_MEMBER in req.perm:
            yield ('team', _('Team'))

    def render_preference_panel(self, req, panel):
        """Process a request for a preference panel. This builds the
        Panel for the team preferences
        """
        if req.method == 'POST':
            self._do_save(req)
            req.redirect(req.href.prefs(panel or None))
       
        # Build the team_member object
        team_member = None
        if req.authname not in [None, 'anonymous'] and \
                Role.TEAM_MEMBER in req.perm:
            name = req.authname
            team_member = self.tmmm.get(name=name)
            if team_member == None:
                team_member = self.tmmm.create(name=name)
        
        # Build the calendar for the current month
        calendars = list()
        ac = AgiloCalendar(day=datetime.today())
        for cal in range(2):
            calendars.append(team_member.calendar.get_hours_for_interval(ac.get_first_day(), 
                                                                         ac.get_last_day()))
            ac = ac.next_month()
            
        return 'agilo_prefs_%s.html' % (panel or 'general'), {
            'settings': {'session': req.session, 'session_id': req.session.sid},
            'teams': self.tmm.select(),
            'team_member': team_member,
            'calendars': calendars,
        }
    
    def _do_save(self, req):
        """Saves the parameters into the object"""
        # Get the Team Member
        team_member = self.tmmm.get(name=req.authname)
        cal = team_member.calendar
        save_calendar = False
        for fieldname in sorted(req.args):
            value = req.args.get(fieldname)
            if (value is not None) and (team_member is not None):
                if fieldname == 'team':
                    team = self.tmm.get(name=value)
                    team_member.team = team
                elif fieldname.startswith('ts_'):
                    if fieldname.startswith('ts_%s_' % team_member.name):
                        ts_member, day = fieldname.rsplit('_', 1)
                        try:
                            cal.set_hours_for_day(float(value), d_ordinal=day)
                        except ValueError:
                            cal.set_hours_for_day(0.0, d_ordinal=day)
                        if not save_calendar:
                            save_calendar = True
                    elif hasattr(team_member, fieldname):
                        try:
                            if float(value) != getattr(team_member, fieldname):
                                setattr(team_member, fieldname, float(value))
                        except ValueError:
                            setattr(team_member, fieldname, 0.0)
        team_member.save()
        # The member's capacity may have changed so we have to invalidate the
        # burndown
        ChartGenerator(self.env).invalidate_cache()
        if save_calendar:
            cal.save()
