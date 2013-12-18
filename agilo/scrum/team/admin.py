# -*- coding: utf-8 -*-
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
#       - Jonas von Poser (jonas.vonposer__at__agile42.com)
#       - Sebastian Schulze <sebastian.schulze_at_agile42.com>

try:
    from acct_mgr.api import AccountManager
except ImportError:
    AccountManager = None

from trac.perm import PermissionSystem
from trac.util.translation import _
from trac.web.chrome import add_warning, add_script

from agilo.api.admin import AgiloAdminPanel
from agilo.charts.chart_generator import ChartGenerator
from agilo.scrum.team.model import TeamModelManager, TeamMemberModelManager
from agilo.utils import Role


__all__ = ['TeamAdminPanel']

class TeamAdminPanel(AgiloAdminPanel):
    """
    Administration panel for teams.
    """
    
    _type = 'teams'
    _label = ('Teams', _('Teams'))

    def __init__(self):
        self.tm = TeamModelManager(self.env)
        self.tmm = TeamMemberModelManager(self.env)

    def detail_save_view(self, req, cat, page, name):
        team_member = req.args.get('team_member') or req.args.get('new_team_member')
        if team_member:
            # save from team member view
            return self.member_save(req, cat, page, name)

        if name=='unassigned':
            team = None
        else:
            team = self.tm.get(name=name)
            if not team:
                return req.redirect(req.href.admin(cat, page))

        if req.args.get('delete'):
            for member_name in req.args.getlist('delete'):
                member = self.tmm.get(name=member_name)
                if team:
                    member.team = None
                    self.tmm.save(member)
                else:
                    self.tmm.delete(member)
            
            # removing members will reduce the capacity, hence the ideal 
            # burndown must be recalculated
            ChartGenerator(self.env).invalidate_cache()
            return req.redirect(req.href.admin(cat, page, name))


        team.description = req.args.get('description')
        self.tm.save(team)
        return req.redirect(req.href.admin(cat, page))

    def detail_view(self, req, cat, page, name):
        if req.args.get('team_member'):
            # show detail page for a specific member
            team_member = self.tmm.get(name=req.args['team_member'])
            if team_member:
                return self.member_view(req, cat, page, name, team_member)

        if name=='unassigned':
            # team members without a team
            members = self.tmm.select(criteria={'team': None})
            if not members:
                # no unassigned team members, redirect to team page
                return req.redirect(req.href.admin(cat, page))
            
            data = {
                'view': 'unassigned',
                'members': members,
            }
            return 'agilo_admin_team.html', data
        
        team = self.tm.get(name=name)
        if not team:
            return req.redirect(req.href.admin(cat, page))
        
        # show the list of team members
        data = {
            'view': 'detail',
            'team': team,
        }
        add_script(req, 'common/js/wikitoolbar.js')
        return 'agilo_admin_team.html', data
    
    def list_view(self, req, cat, page):
        unassigned_members = self.tmm.select(criteria={'team': None})

        data = {
            'view': 'list',
            'teams': self.tm.select(),
            'unassigned' : unassigned_members,
        }
        return 'agilo_admin_team.html', data
    
    def list_save_view(self, req, cat, page):
        # TODO: better sanity checks for input, show error in form
        name = req.args.get('name')
        description = req.args.get('description')
        if req.args.get('add') and name:
            team = self.tm.get(name=name)
            if team:
                return req.redirect(req.href.admin(cat, page, name))
        
            # create the team if it doesn't exist yet
            team = self.tm.create(name=name, description=description)
            return req.redirect(req.href.admin(cat, page, name))

        for team_name in req.args.getlist('delete'):
            # remove all team members first
            team = self.tm.get(name=team_name)
            for m in self.tmm.select(criteria={'team':team}):
                m.team = None
                self.tmm.save(m)
            self.tm.delete(team)
        
        return req.redirect(req.href.admin(cat, page))
    
    def member_view(self, req, cat, page, name, team_member):
        data = {
            'view': 'member',
            'team_member': team_member,
            'teams': self.tm.select(),
        }
        return 'agilo_admin_team.html', data
    
    def _get_or_create_team_member_without_saving(self, req, name, team):
        team_member = self.tmm.get(name=name)
        if not team_member:
            team_member = self.tmm.create(name=name, team=team, save=False)
            team_member.team = team
        else:
            team_member.full_name = req.args.get('member_full_name', '')
            team_member.email = req.args.get('member_email', '')
            new_team = self.tm.get(name=req.args.get('team'))
            team_member.team = new_team
        team_member.description = req.args.get('member_description')
        return team_member
    
    def redirect_to_team_view_page(self, req, cat, page, name, **kw):
        req.redirect(req.href.admin(cat, page, name, **kw))
    
    def account_manager_is_enabled(self):
        if AccountManager is not None:
            return self.env.is_component_enabled(AccountManager)
        return False
    
    def use_account_manager_integration(self, member_name):
        if self.account_manager_is_enabled():
            account_already_created = AccountManager(self.env).has_user(member_name)
            if not account_already_created:
                return AccountManager(self.env).supports('set_password')
        return False
    
    def show_confirmation_user_creation(self, req, member_name):
        return req.args.get('add') and self.use_account_manager_integration(member_name)
    
    def perform_user_creation(self, req):
        add_user_action = req.args.get('add')
        create_user_action = req.args.get('createUser_ok')
        return add_user_action or create_user_action
    
    def create_user_and_grant_permissions(self, req, team_member):
        if self.use_account_manager_integration(team_member.name):
            password = team_member.name
            AccountManager(self.env).set_password(team_member.name, password)
        permission_system = PermissionSystem(self.env)
        if not permission_system.check_permission(Role.TEAM_MEMBER, team_member.name):
            permission_system.grant_permission(team_member.name, Role.TEAM_MEMBER)
    
    def member_save(self, req, cat, page, name):
        if req.args.get('createUser_cancel'):
            self.redirect_to_team_view_page(req, cat, page, name)
        team = self.tm.get(name=name)
        
        member_name = req.args.get('team_member') or req.args.get('new_team_member')
        team_member = self._get_or_create_team_member_without_saving(req, member_name, team)
        
        if self.show_confirmation_user_creation(req, team_member.name):
            data = {'view': 'create_user_confirm', 
                    'user_name': team_member.name, 'team_name': team.name,
                    'member_description' : team_member.description}
            return 'agilo_admin_team.html', data
        
        query_params = {}
        if self.perform_user_creation(req):
            self.create_user_and_grant_permissions(req, team_member)
            query_params = dict(team_member=team_member.name)
        else:
            try:
                team_member.capacity = [float(req.args.get('ts_%d' % i) or '0') for i in range(7)]
            except ValueError:
                # TODO: Enhance error handling
                add_warning(req, 'Could not parse time value')
                self.redirect_to_team_view_page(req, cat, page, name)
        
        self.tmm.save(team_member)
        # capacity may have changed - hence the ideal burndown is different
        ChartGenerator(self.env).invalidate_cache()
        self.redirect_to_team_view_page(req, cat, page, name, **query_params)

