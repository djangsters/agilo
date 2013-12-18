
import Cookie
import os

from trac.util.datefmt import to_timestamp

from agilo.ticket import AgiloTicket
from agilo.utils import Key, Type
from agilo.utils.json_client import ServerProxy

from agilo.test.test_util import get_instance_of_current_testcase

__all__ = ['AgiloJSONTester']


class AgiloJSONTester(object):
    
    def __init__(self, url, env):
        self.server = ServerProxy(url)
        self.server.save_errors_to_file(self.filename_for_exceptions())
        self.env = env
    
    def filename_for_exceptions(self):
        try:
            testcase = get_instance_of_current_testcase()
            classname = testcase.__class__.__name__
            logdir = testcase.testenv.get_log_dir()
        except:
            logdir = os.path.dirname(os.path.abspath(__file__))
            classname = 'no_testcase_found'
        return os.path.join(logdir, '%s.html' % classname)
    
    def _extract_trac_session_id_from_response(self, response):
        cookie_header = response.getheader('set-cookie')
        if cookie_header:
            cookie = Cookie.SimpleCookie()
            cookie.load(cookie_header)
            if 'trac_auth' in cookie:
                return cookie['trac_auth'].value
        return None
    
    def create_task(self, **kwargs):
        kwargs[Key.TYPE] = Type.TASK
        return self.server.json.tickets.put(**kwargs)
    
    def login_as(self, username, password=None):
        if password is None:
            password = username
        # We need to store the cookie for later reuse
        self.server.set_username(username)
        self.server.set_password(password)
        (data, response) = self.server.login.get_json_with_response()
        session_id = self._extract_trac_session_id_from_response(response)
        assert session_id is not None
        self.server.set_session_id(session_id)
    
    # REFACT: no 'get_'
    def get_sprint_backlog(self, sprint_name):
        return self.server.json.sprints[sprint_name].backlog.get()
    
    def burndownvalues(self, sprint_name):
        return self.server.json.sprints[sprint_name].burndownvalues.get()
    
    def edit_ticket(self, ticket_id, **kwargs):
        if 'time_of_last_change' not in kwargs:
            ticket = AgiloTicket(self.env, ticket_id)
            kwargs['time_of_last_change'] = to_timestamp(ticket.time_changed)
        if 'ts' not in kwargs:
            ticket = AgiloTicket(self.env, ticket_id)
            kwargs['ts'] = str(ticket.time_changed)
        from agilo.ticket import AgiloTicketSystem
        if AgiloTicketSystem.is_trac_1_0():
            from trac.util.datefmt import to_utimestamp
            if 'view_time' not in kwargs:
                ticket = AgiloTicket(self.env, ticket_id)
                kwargs['view_time'] = str(to_utimestamp(ticket.time_changed))
            if 'submit' not in kwargs:
                kwargs['submit'] = True
        return self.server.json.tickets[ticket_id].post(**kwargs)
    
    def get_team_for_sprint(self, sprint_name):
        return self.server.json.sprints[sprint_name].team.get()

