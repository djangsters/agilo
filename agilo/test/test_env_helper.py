# -*- encoding: utf-8 -*-
#   Copyright 2008 Agile42 GmbH, Berlin (Germany)
#   Copyright 2007 Andrea Tomasini <andrea.tomasini_at_agile42.com>
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
#   Author: Andrea Tomasini <andrea.tomasini_at_agile42.com>

from datetime import datetime, timedelta
import new, os
from random import randint
from time import mktime
from trac.db import DatabaseManager
from trac.db.api import with_transaction
from agilo.scrum.burndown.model import BurndownDataChangeModelManager
from agilo.scrum.sprint.controller import SprintController
from trac.ticket.default_workflow import ConfigurableTicketWorkflow,\
    get_workflow_config

try:
    from svn import fs, repos, core
except ImportError:
    fs = repos = core = None
from trac.env import Environment
from trac.perm import DefaultPermissionPolicy, PermissionCache, PermissionSystem
from trac.resource import ResourceNotFound
from trac.test import EnvironmentStub, Mock
from trac.ticket import Milestone
from trac.util.datefmt import localtz, parse_date, to_timestamp, utc
from trac.versioncontrol.api import RepositoryManager
from trac.web.api import Cookie, Href, RequestDone

from agilo.api import ValueObject
from agilo.scrum import BacklogModelManager, SprintModelManager, \
    TeamModelManager, TeamMemberModelManager,BacklogConfiguration
from agilo.scrum.contingent import ContingentController
from agilo.ticket import AgiloTicketSystem, LinksConfiguration, AgiloTicket, AgiloTicketModelManager
from agilo.test.pythonic_testcase import *
from agilo.utils import Key, Status, BacklogType, Type, AgiloConfig
from agilo.utils.days_time import now, shift_to_utc
from agilo.utils.db import get_db_for_write
from agilo.utils.compat import exception_to_unicode, json
from agilo.utils.sorting import SortOrder


__all__ = ['BetterEnvironmentStub', 'TestEnvHelper']

# the EnvironmentStub needs that the Agilo's Roles are visible to load them
import agilo.utils.permissions

LAST_ENV_KEY = 'agilo'

from trac import test
original_get_dburi = test.get_dburi
def custom_get_dburi():
    from agilo.test.functional.api import EnvironmentBuilder
    if LAST_ENV_KEY not in EnvironmentBuilder._created_environments.keys():
        return original_get_dburi()
    testenv = EnvironmentBuilder.get_testenv(LAST_ENV_KEY)
    return testenv.get_db_url()

test.get_dburi = custom_get_dburi

def custom_get_db_cnx(self, destroying=False):
    dbenv = EnvironmentStub.dbenv
    if not dbenv:
        dbenv = EnvironmentStub.dbenv = EnvironmentStub()
        dbenv.config.set('trac', 'database', self.dburi)
        if not destroying:
            self.reset_db() # make sure we get rid of previous garbage
    return DatabaseManager(dbenv).get_connection()

if not AgiloTicketSystem.is_trac_1_0():
    EnvironmentStub.get_db_cnx = custom_get_db_cnx

def suppressed__del__(self):
    try:
        self.close()
    except:
        # if we got here, it's because the poolable connection was 
        # garbage collected from a thread other than the one where it
        # was opened.  this is not trac's fault, but it should handle
        # the situation better
        pass
    
from trac.db.pool import PooledConnection
PooledConnection.__del__ = suppressed__del__


class BetterEnvironmentStub(EnvironmentStub):

    # This is a patch similar to http://trac.edgewall.org/ticket/8591
    # even if the patch above would go into trac 0.11.x, we still need to
    # support older trac versions
    def __init__(self, default_data=False, enable=None, env_key='agilo'):
        self.env_key = env_key
        self._destroyedInSetup = None
        from agilo.test.functional.api import EnvironmentBuilder
        testenv = EnvironmentBuilder.get_testenv(self.env_key)
        self.dburi = testenv.get_db_url()
        super(BetterEnvironmentStub, self).__init__(default_data=default_data, enable=enable)
        self.db = None

        if enable is not None:
            self.config.set('components', 'trac.*', 'disabled')
        for name_or_class in enable or ():
            config_key = self.normalize_configuration_key(name_or_class)
            self.config.set('components', config_key, 'enabled')

    def normalize_configuration_key(self, name_or_class):
        name = name_or_class
        if not isinstance(name_or_class, basestring):
            name = name_or_class.__module__ + '.' + name_or_class.__name__
        return name.lower()

    def is_component_enabled(self, cls):
        return Environment.is_component_enabled(self, cls)

    def reset_db(self, default_data=None):
        from agilo.test.functional.api import EnvironmentBuilder
        env = EnvironmentBuilder.get_testenv(self.env_key)
        from trac.db.api import _parse_db_str
        scheme, db_prop = _parse_db_str(env.get_db_url())

        if scheme != 'sqlite' and not default_data:
            return super(BetterEnvironmentStub, self).reset_db(default_data)

        env_for_transaction = env.get_trac_environment()
        if AgiloTicketSystem.is_trac_1_0():
            env_for_transaction = env

        tables = []
        if scheme != 'sqlite':
            db = self.get_db_cnx()
            @with_transaction(env_for_transaction, db)
            def implementation(db):
                cursor = db.cursor()
                cursor.execute("update system set value='9999' WHERE name='database_version'")
                db.commit()

            tables = super(BetterEnvironmentStub, self).reset_db(default_data)
        else:
            from trac import db_default
            from trac.db_default import schema
            from trac.db.sqlite_backend import _to_sql

            # our 'destroy_db'
            db = self.get_db_cnx()
            @with_transaction(env_for_transaction, db)
            def implementation(db):
                cursor = db.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchall()
                for table in tables:
                    cursor.execute("DROP TABLE %s" % table)

                # part of sqlite_backend's init_db
                for table in schema:
                    for stmt in _to_sql(table):
                        cursor.execute(stmt)

                # part of reset_db
                for table, cols, vals in db_default.get_data(db):
                    cursor.executemany("INSERT INTO %s (%s) VALUES (%s)"
                                       % (table, ','.join(cols),
                                          ','.join(['%s' for c in cols])),
                        vals)
                db.commit()

        if env.tester.testcase.testtype != 'unittest':
            try:
                env._upgrade_environment()
                env._setup_users_and_permissions()
            except:
                # it's possible that this has already happened
                print "Warning: Exception on post-reset_db tasks"

        return tables

    # See trac ticket: http://trac.edgewall.org/ticket/7619, it has been fixed
    # in 0.11.2, but we still tests till 0.11.1 because it is still the
    # default for some linux distributions.
    def get_known_users(self, db=None):
        return self.known_users

class TestEnvHelper(object):
    """Helper to create an environment give the path. Used for testing"""
    def __init__(self, env=None, strict=False, enable=(), enable_agilo=True, env_key='agilo'):
        self.env = env
        if env is None:
            self.env = self._create_stub_environment(enable, strict, enable_agilo=enable_agilo, env_key=env_key)
            import time; time.sleep(0.5)
        else:
            # Prevent programmer errors
            assert strict == False
            assert enable == ()
            assert enable_agilo == True
        self.env_path = self.env.path
        self.objects = list()
        self.files = list()
        self._ticket_counter = 0

        try:
            self._upgrade_environment(self.env)
        except:
            # might have already happened
            pass

        self.svn_repos = None
        try:
            repo_path = RepositoryManager(self.env).repository_dir
            self.svn_repos = repos.open(repo_path)
        except:
            #No repo configured
            pass

    def _plugins(self, enabled_plugins, enable_agilo):
        plugins = ['trac.*']
        if enable_agilo:
            plugins.append('agilo.*')
        plugins.extend(list(enabled_plugins))
        return plugins

    def _create_stub_environment(self, enabled_plugins, restrict_owner, enable_agilo, env_key='agilo'):
        plugins = self._plugins(enabled_plugins, enable_agilo)
        env = BetterEnvironmentStub(default_data=True, enable=plugins, env_key=env_key)
        # Set the connection type in the config as memory
        # Sent patch to trac #7208 waiting for commit
#        self.env.config.set('trac', 'database', 'sqlite:db/test.db')
        env.config.set('trac', 'permission_policies', 'AgiloPolicy, DefaultPermissionPolicy, LegacyAttachmentPolicy')
        if restrict_owner:
            env.config.set('ticket', 'restrict_owner', 'true')
        return env

    def _upgrade_environment(self, env):
        # Avoid recursive imports - TestEnvHelper must not trigger anything
        from agilo.init import AgiloInit
        if not self.env.is_component_enabled(AgiloInit):
            return
        ai = AgiloInit(env)
        db = env.get_db_cnx()
        if ai.environment_needs_upgrade(db):
            ai.upgrade_environment(db)
        db.commit()
        AgiloConfig(env).clear_trac_component_cache()

    def get_env(self):
        """Returns the created environment"""
        return self.env

    def get_env_path(self):
        """Returns the trac environment path"""
        return self.env_path

    def _set_sprint_date_normalization(self, enabled):
        config = AgiloConfig(self.env)
        config.change_option('sprints_can_start_or_end_on_weekends', not enabled,
                             section=AgiloConfig.AGILO_GENERAL)
        config.save()

    def enable_sprint_date_normalization(self):
        self._set_sprint_date_normalization(True)
        assert AgiloConfig(self.env).sprints_can_start_or_end_on_weekends == False

    def disable_sprint_date_normalization(self):
        self._set_sprint_date_normalization(False)
        assert AgiloConfig(self.env).sprints_can_start_or_end_on_weekends == True

    def create_milestone(self, name, due=None, duration=20, db=None):
        """
        Creates a milestone with the given name and due
        date, the latter should be a datetime object
        """
        db, handle_ta = get_db_for_write(self.env, db)
        # Try to load the milestone first
        try:
            m = Milestone(self.env, name=name, db=db)
        except ResourceNotFound:
            # than we create it
            m = Milestone(self.env, db=db)
            m.name = name
            if due is not None and isinstance(due, datetime):
                dueo = due.toordinal() + duration
                m.due = mktime(datetime.fromordinal(dueo).timetuple())
            m.insert()
            if handle_ta:
                try:
                    db.commit()
                    # workaround for the fact that trac in 0.11.1 doesn't set exists correctly...
                    m._old_name = m.name
                except Exception, e:
                    self.env.log.warning(exception_to_unicode(e))
                    db.rollback()
        return m

    def delete_milestone(self, name):
        """Deletes the given milestone"""
        conn = self.env.get_db_cnx()
        m = Milestone(self.env, name=name, db=conn)
        m.delete(db=conn)

    def list_milestone_names(self):
        """Returns a list of all the milestone names in the env"""
        conn = self.env.get_db_cnx()
        names = []
        sql_query = "SELECT name FROM milestone"
        cursor = conn.cursor()
        try:
            cursor.execute(sql_query)
            rows = cursor.fetchall()
            for name, in rows:
                names.append(name)
        except:
            conn.rollback()
        return names

    def delete_all_milestones(self):
        """Delete all the milestones in the environment"""
        names = self.list_milestone_names()
        for name in names:
            self.delete_milestone(name)

    def generate_remaining_time_data(self, task, start_date, end_date=None):
        def create_burndown_data_change(remaining_time, when):
            task[Key.REMAINING_TIME] = str(remaining_time)
            task.save_changes(author=task[Key.OWNER], comment='Updated time...', when=when)

            # Reset time of the last burndown data change
            changes = BurndownDataChangeModelManager(self.env).select(limit=1, order_by=['-id'])
            last_burndown_change = changes[0]
            last_burndown_change.update_values(when=when).save()

        if task.get_type() != Type.TASK:
            return
        if not end_date:
            end_date = parse_date('now')

        remaining_time = randint(4,12)
        create_burndown_data_change(remaining_time, start_date)

        if not task.has_owner:
            return
        when = start_date + timedelta(hours=randint(4,16))
        while when < end_date:
            remaining_time += randint(-3,0)
            # if the remaining time is set to 0, the task will be closed!
            if remaining_time <= 0:
                remaining_time = 1

            create_burndown_data_change(remaining_time, when)
            when += timedelta(hours=randint(4,16))

    def create_sprint(self, name, start=None, end=None, duration=20,
                      milestone=None, team=None):
        """Creates a Sprint for the given milestone, if doesn't exists, first
        it creates a Milestone"""
        # If the start day is set to today, the sprint will
        # normalize it to 9:00am of the start day and all the tests
        # will fail, till 9:00am in the morning...
        if start is None:
            # we set hours to 0 so will be normalized to 9am at any
            # time of the day, when running tests.
            start = (now(tz=utc) - timedelta(days=3)).replace(hour=0)
        if milestone is None:
            milestone = self.create_milestone('Milestone for %s' % name)
        # It should automatically load the existing Sprint if already there
        if isinstance(milestone, Milestone):
            milestone = milestone.name
        sprint_controller = SprintController(self.env)
        if start is not None:
            start = shift_to_utc(start)
        if end is not None:
            end = shift_to_utc(end)
        create_sprint_command = SprintController.CreateSprintCommand(self.env, name=name, start=start,
                                                                     end=end, duration=duration, milestone=milestone)
        create_sprint_command.native = True
        sprint = sprint_controller.process_command(create_sprint_command)

        assert sprint is not None
        if team is not None:
            if isinstance(team, basestring):
                team = self.create_team(name=team)
            sprint.team = team
            sprint.save()
        return sprint

    def delete_sprint(self, name):
        """Deletes the given Sprint from the environment"""
        smm = SprintModelManager(self.env)
        s = smm.get(name=name)
        smm.delete(s)

    def list_sprint_names(self):
        """Returns a list of all the sprint names"""
        smm = SprintModelManager(self.env)
        return [s.name for s in smm.select()]

    def add_contingent_to_sprint(self, name, amount, sprint):
        # REFACT: why can't I say sprint.add_contingent('Foo', 12). That would seem so much nicer?
        # Maybe sprint.contingents.add('foo', 12) to have an easier time to separate stuff out.
        # That could also support stuff like {{{for contingent in sprint.contingents: ...}}}
        add_contingent_command = ContingentController.AddContingentCommand(self.env, sprint=sprint, name=name, amount=str(amount))
        ContingentController(self.env).process_command(add_contingent_command)

    def used_up_time_in_contingent(self, name, sprint):
        get_contingent_command = ContingentController.GetContingentCommand(self.env, sprint=sprint, name=name)
        return ContingentController(self.env).process_command(get_contingent_command).actual

    def delete_all_sprints(self):
        """Deletes all the sprints in the environment"""
        names = self.list_sprint_names()
        for name in names:
            self.delete_sprint(name)

    def create_team(self, name='Team'):
        """Creates and return a team object, if already existing just returns it"""
        tmm = TeamModelManager(self.env)
        team = tmm.get(name=name)
        if not team:
            team = tmm.create(name=name)
        return team

    def list_team_names(self):
        """Returns a list of existing team names"""
        tmm = TeamModelManager(self.env)
        return [t.name for t in tmm.select()]

    def create_member(self, name, team=None):
        """Creates a team member for the given team with the given name"""
        if team is not None:
            if isinstance(team, basestring):
                team = self.create_team(team)
            team.invalidate_team_member_cache()

        tmmm = TeamMemberModelManager(self.env)
        member = tmmm.get(name=name, team=team)
        if not member:
            member = tmmm.create(name=name, team=team)
        return member

    def create_backlog(self, name='Performance Backlog',
                       num_of_items=10, b_type=BacklogType.GLOBAL,
                       ticket_types=[Type.REQUIREMENT, Type.USER_STORY],
                       scope=None):
        """Creates a Backlog with the given parameters and returns it"""
        # Characteristic properties
        ticket_custom = AgiloConfig(self.env).get_section(AgiloConfig.TICKET_CUSTOM)
        char_props = {Type.REQUIREMENT: [(Key.BUSINESS_VALUE,
                                          ticket_custom.get("%s.options" % Key.BUSINESS_VALUE).split('|'))],
                      Type.USER_STORY: [(Key.STORY_PRIORITY,
                                         ticket_custom.get("%s.options" % Key.STORY_PRIORITY).split('|')),
                                        (Key.STORY_POINTS,
                                         ticket_custom.get("%s.options" % Key.STORY_POINTS).split('|'))],
                      Type.TASK: [(Key.REMAINING_TIME, ['12', '8', '4', '6', '2', '0'])],
                      Type.BUG: [(Key.PRIORITY, ['minor', 'major', 'critical'])]}
        # creates the specified number of tickets
        last = None
        for i in range(num_of_items):
            t_type = ticket_types[randint(0, len(ticket_types) - 1)]
            t_props = dict([(prop_name, values[randint(0, len(values) - 1)]) for \
                            prop_name, values in char_props[t_type]])
            if scope and BacklogType.LABELS.get(b_type) in \
                    AgiloConfig(self.env).TYPES.get(t_type):
                # Set the scope to the ticket
                t_props[BacklogType.LABELS.get(b_type)] = scope
            t_props[Key.SUMMARY] = 'Agilo Ticket #%d' % i

            actual = self.create_ticket(t_type, props=t_props)
#            print "Ticket(%s): %s => %s (Backlog: %s)" % \
#                   (actual[Key.STATUS], actual, t_props,
#                    BacklogType.LABELS.get(b_type))
            if last:
                if ticket_types.index(last.get_type()) > ticket_types.index(actual.get_type()):
                    assert actual.link_to(last)
                else:
                    assert last.link_to(actual)
                last = actual
        backlog = self.create_backlog_without_tickets(name, type=b_type,
                                                      ticket_types=ticket_types,
                                                      scope=scope)
        return backlog

    def create_backlog_without_tickets(self, name, type, ticket_types=(), scope=None):
        backlog_config = BacklogConfiguration(self.env, name=name, type=type)
        backlog_config.ticket_types=ticket_types
        backlog_config.save()
        return BacklogModelManager(self.env).get(name=name, scope=scope)

    def allow_link_from_to(self, from_type, to_type, save=None):
        # All tickets instantiated before this call will have a copy
        # of their allowed links, so for this call to have an effect,
        # the objects have to be dropped and recreated.
        config = AgiloConfig(self.env)
        assert from_type in config.get_available_types()
        assert to_type in config.get_available_types()
        section = config.get_section(AgiloConfig.AGILO_LINKS)
        allowed_links = section.get_list('allow')
        allowed_links.append('%s-%s' % (from_type, to_type))
        section.change_option('allow', ', '.join(allowed_links), save=save)

        # Recreate all the worst caches
        links_configuration = LinksConfiguration(self.env)
        links_configuration._initialized = False
        links_configuration.initialize()
        AgiloTicketSystem(self.env).clear_cached_information()

    def last_changelog_author(self, ticket):
        changelog = ticket.get_changelog()
        assert len(changelog) >= 1
        return changelog[-1][1]

    def create_file(self, file_name, content, author, comment):
        """
        Creates a file in the SVN repository with the given
        name and content (text). Returns the committed revision
        """
        assert self.svn_repos is not None, "SVN repository not set..."
        # Get an SVN file system pointer
        fs_ptr = repos.fs(self.svn_repos)
        rev = fs.youngest_rev(fs_ptr)
        # Create and SVN transaction
        txn = fs.begin_txn(fs_ptr, rev)
        txn_root = fs.txn_root(txn)
        # Create a file in the root transaction
        fs.make_file(txn_root, file_name)
        stream = fs.apply_text(txn_root, file_name, None)
        core.svn_stream_write(stream, "%s\n" % content)
        core.svn_stream_close(stream)
        # Now set the properties svn:log and svn:author to
        # the newly created node (file)
        fs.change_txn_prop(txn, 'svn:author', author)
        fs.change_txn_prop(txn, 'svn:log', comment)
        # Commit the transaction
        fs.commit_txn(txn)
        # Add teh file to the list of created files
        self.files.append(file_name)
        # Returns therevision number
        return rev + 1

    def delete_file(self, file_name):
        """Deletes the given file from the repository"""
        assert self.svn_repos is not None, "SVN repository not set..."
        # Get an SVN file system pointer
        fs_ptr = repos.fs(self.svn_repos)
        rev = fs.youngest_rev(fs_ptr)
        # Create and SVN transaction
        txn = fs.begin_txn(fs_ptr, rev)
        txn_root = fs.txn_root(txn)
        # Create a file in the root transaction
        fs.delete(txn_root, file_name)
        # Commit the transaction
        fs.commit_txn(txn)

    def retrieve_file(self, file_name, rev=None):
        """
        Retrieves the given file name, at the specified revision or
        the latest available from the SVN repository
        """
        assert self.svn_repos is not None, "SVN repository not set..."
        # Get an SVN file system pointer
        fs_ptr = repos.fs(self.svn_repos)
        if rev is None:
            rev = fs.youngest_rev(fs_ptr)
        root = fs.revision_root(fs_ptr, rev)
        stream = fs.file_contents(root, file_name)
        svn_file = core.Stream(stream)
        core.svn_stream_close(stream)
        return svn_file

    def _replace_object_by_name(self, field_name, value):
        if field_name in [Key.SPRINT, Key.OWNER, Key.MILESTONE, Key.TEAM]:
            if not isinstance(value, basestring) and hasattr(value, 'name'):
                return value.name
        return value

    def create_ticket(self, t_type, props=None):
        """Utility to create a ticket of the given type"""
        if props is None:
            props = {}
        self._ticket_counter += 1
        ticket = AgiloTicketModelManager(self.env).create(t_type=t_type, save=False)
        ticket[Key.SUMMARY] = u'%s n.%s' % (t_type.title(), self._ticket_counter)
        ticket[Key.DESCRIPTION] = u'Description for ' + t_type
        ticket[Key.STATUS] = Status.NEW
        for field_name, value in props.items():
            assert ticket.is_writeable_field(field_name), field_name
            value = self._replace_object_by_name(field_name, value)
            ticket[field_name] = value
        AgiloTicketModelManager(self.env).save(ticket)

        self.objects.append(ticket)
        return ticket

    def delete_ticket(self, t_id):
        """Deletes the ticket with the given ticket id"""
        atm = AgiloTicketModelManager(self.env)
        ticket = atm.get(tkt_id=t_id)
        try:
            atm.delete(ticket)
        except Exception, e:
            print exception_to_unicode(e)

    def delete_all_tickets(self):
        """Delete all the tickets in the environment"""
        atm = AgiloTicketModelManager(self.env)
        tickets = atm.select()
        for t in tickets:
            try:
                atm.delete(t)
            except Exception, e:
                print exception_to_unicode(e)

    def load_ticket(self, ticket=None, t_id=None):
        """
        Utility method to load a ticket from trac. Used to check
        committed changes
        """
        assert ticket or t_id, "Supply either a ticket or and id"
        if ticket:
            t_id = ticket.id
        tm = AgiloTicketModelManager(self.env)
        tm.get_cache().invalidate(key_instance=((t_id,), None))
        t = tm.get(tkt_id=t_id)
        return t

    def delete_created_tickets(self):
        """Deletes all the tickets created by the helper"""
        for obj in self.objects:
            obj.delete()
            self._ticket_counter -= 1

    def delete_files(self):
        """Deletes all the files created by the helper"""
        if self.svn_repos is not None:
            # Get an SVN file system pointer
            fs_ptr = repos.fs(self.svn_repos)
            rev = fs.youngest_rev(fs_ptr)
            # Create and SVN transaction
            txn = fs.begin_txn(fs_ptr, rev)
            txn_root = fs.txn_root(txn)
            # Create a file in the root transaction
            for svn_file in self.files:
                fs.delete(txn_root, svn_file)
            # Commit the transaction
            fs.commit_txn(txn)

    def cleanup(self):
        """Delete all the tickets and all the file created"""
        self.delete_files()
        self.delete_created_tickets()
        self.enable_sprint_date_normalization()


    # modifying ticket history.................................................

    def purge_ticket_history(self, ticket):
        db = self.env.get_db_cnx()
        cursor = db.cursor()
        ticket_id = getattr(ticket, 'id', None)
        if ticket_id == None:
            ticket_id = int(ticket)
        sql = 'DELETE FROM ticket_change WHERE ticket=%d'
        cursor.execute(sql % ticket_id)

    def move_changetime_to_the_past(self, tickets):
        """Trac has some tables which use the time as primary key but only with
        a 'second' precision so you can't save a ticket twice in a second. This
        is very annoying for unit tests so this method can just reset the times
        for a the given tickets to the past."""
        # Please note that while this works great for the same connection pool
        # (e.g. for unit tests) the method did not work for me in a functional
        # test (svn_hooks_test). I found that trac always read the old data
        # no matter what I did to put them into the database...
        db = self.env.get_db_cnx()
        cursor = db.cursor()
        for ticket in tickets:
            # This should work for ticket ids too so that it is easier to use
            # this method from functional tests, too.
            ticket_id = getattr(ticket, 'id', None)
            if ticket_id == None:
                ticket_id = int(ticket)
            sql = 'UPDATE ticket_change SET time=time - 2 WHERE ticket=%d'
            cursor.execute(sql % ticket_id)

    # enabling unit tests for high-level features..............................

    def add_user_to_known_users(self, username, name="", email=""):
        assert not self.env.known_users is None
        known_user_names = (tuple[0] for tuple in self.env.known_users)
        if username in known_user_names:
            return
        self.env.known_users.append((username, name, email))

    def emulate_login(self, username, when=None):
        """Emulates a login for the given username, by setting an entry in the
        session table, if when is specified will be also set the datetime of
        the login to when, otherwise to now"""
        if when is None:
            when = now()
        db = self.env.get_db_cnx()
        try:
            cursor = db.cursor()
            cursor.execute("SELECT sid FROM session WHERE sid='%s'" % username)
            last_visit = to_timestamp(when)
            if cursor.fetchone():
                cursor.execute("UPDATE session SET last_visit=%s WHERE sid='%s'" % \
                               (last_visit, username))
            else:
                cursor.execute("INSERT INTO session (sid, authenticated, last_visit) " \
                               "VALUES ('%s', 1, %s)" % (username, last_visit))
            db.commit()
            self.add_user_to_known_users(username)
        except Exception, e:
            db.rollback()
            assert False, "Unable to complete login for user: %s (%)" % \
                (username, exception_to_unicode(e))

    def mock_request(self, username='anonymous', path_info='/', request_body='', **kwargs):
        response = ValueObject(headers=dict(), body='', code=None)
        as_json = lambda self: json.loads(self.body)
        response.body_as_json = new.instancemethod(as_json, response, response.__class__)

        perm = PermissionCache(self.env, username)
        attributes = dict(args=dict(), tz=localtz, perm=perm, method='GET',
                          path_info=path_info, environ={}, session={},
                          form_token=None, )
        attributes.update(kwargs)

        def read():
            return request_body

        def write(string):
            response['body'] += string

        def redirect(url, permanent=False):
            raise RequestDone

        def get_header(header_name):
            header_name = header_name.lower()
            if header_name == 'content-length':
                return str(len(request_body))
            return None

        req = Mock(authname=username, base_path=None, href=Href(path_info),
                   chrome=dict(warnings=[], notices=[], scripts=[]),
                   incookie=Cookie(), outcookie=Cookie(),
                   response=response,

                   end_headers=lambda: None,
                   get_header=get_header,
                   read=read,
                   redirect=redirect,
                   send_response=lambda code: response.update({'code': code}),
                   send_header=lambda name, value: response['headers'].update({name: value}),
                   write=write,

                   **attributes)

        # our jquery injects wines if it does not find trac's jquery
        req.chrome['scripts'].append(dict(href='/foo/jquery.js'))
        return req

    def redirect_for_call(self, req, call, assert_expected_target=None):
        actual_target = {'url': None}
        def redirect(url, permanent=False):
            actual_target['url'] = url
            raise RequestDone

        req.redirect = redirect
        assert_raises(RequestDone, call)
        if assert_expected_target is None:
            return
        assert_equals(assert_expected_target, actual_target['url'])

    # working with permissions..................................................

    def grant_permission(self, username, action):
        # DefaultPermissionPolicy will cache permissions for 5 seconds so we
        # need to reset the cache
        DefaultPermissionPolicy(self.env).permission_cache = {}
        PermissionSystem(self.env).grant_permission(username, action)
        assert action in PermissionSystem(self.env).get_user_permissions(username)

    def revoke_permission(self, username, action):
        # DefaultPermissionPolicy will cache permissions for 5 seconds so we
        # need to reset the cache
        DefaultPermissionPolicy(self.env).permission_cache = {}
        PermissionSystem(self.env).revoke_permission(username, action)
        assert action not in PermissionSystem(self.env).get_user_permissions(username)

    def has_permission(self, username, action):
        # DefaultPermissionPolicy will cache permissions for 5 seconds so we
        # need to reset the cache
        DefaultPermissionPolicy(self.env).permission_cache = {}

        if AgiloTicketSystem.is_trac_1_0():
            del PermissionSystem(self.env).store._all_permissions

        return PermissionSystem(self.env).check_permission(action, username)

    # creating tickets..........................................................

    def create_story(self, **kwargs):
        return self.create_ticket(Type.USER_STORY, kwargs)

    def create_task(self, **kwargs):
        return self.create_ticket(Type.TASK, kwargs)

    # modifying ticket definitions .............................................

    def create_field(self, field_name, field_type, **field_options):
        config = AgiloConfig(self.env)
        ticket_custom = config.get_section('ticket-custom')
        ticket_custom.change_option(field_name, field_type)
        for (option_name, option_value) in field_options.items():
            key = '%s.%s' % (field_name, option_name)
            ticket_custom.change_option(key, option_value)
        config.save()

        ticket_system = AgiloTicketSystem(self.env)
        all_known_fields = ticket_system.fieldnames(ticket_system.get_ticket_fields())
        assert_contains(field_name, all_known_fields)

    def add_field_for_type(self, field_name, ticket_type):
        assert not AgiloTicket(self.env, t_type=ticket_type).is_writeable_field(field_name)
        config = AgiloConfig(self.env)
        current_fields = config.get_list(ticket_type, section=AgiloConfig.AGILO_TYPES)
        config.change_option(ticket_type, ', '.join(current_fields + [field_name]), section=AgiloConfig.AGILO_TYPES)
        config.save()
        assert AgiloTicket(self.env, t_type=ticket_type).is_writeable_field(field_name)

    def enable_backlog_filter(self, attribute_name):
        self.env.config.set(AgiloConfig.AGILO_GENERAL, 'backlog_filter_attribute', attribute_name)
        assert_equals(attribute_name, AgiloConfig(self.env).backlog_filter_attribute)

    def enable_burndown_filter(self):
        self.env.config.set(AgiloConfig.AGILO_GENERAL, 'should_reload_burndown_on_filter_change_when_filtering_by_component', True)
        self.enable_backlog_filter(Key.COMPONENT)
        assert_true(AgiloConfig(self.env).is_filtered_burndown_enabled())

    def clear_ticket_system_field_cache(self):
        # In Trac 0.12, fields will be cached by new functionality and this
        # cache will be initialized before our custom field configuration was
        # read so we need to force a reload
        ticket_system = AgiloTicketSystem(self.env)
        if not ticket_system.is_trac_012():
            return
        del ticket_system.fields
        del ticket_system.custom_fields

    def change_workflow_config(self, lines):
        for (option, value) in lines:
            self.env.config.set('ticket-workflow', option, value)
        self.env.config.save()
        self.clear_ticket_system_field_cache()
        ticket_workflow = ConfigurableTicketWorkflow(self.env)
        ticket_workflow.actions = get_workflow_config(self.env.config)



