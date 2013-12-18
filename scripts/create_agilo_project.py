# -*- coding: utf-8 -*-
#   Copyright 2008 Agile42 GmbH - Andrea Tomasini
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
# 
# Authors:
#     - Andrea Tomasini <andrea.tomasini__at__agile42.com>
import sys
import getopt

from trac.env import Environment
from trac.admin.console import TracAdmin
from trac.wiki.model import WikiPage

from agilo.utils.config import AgiloConfig
from agilo.utils.compat import exception_to_unicode


help_message = '''
Creates and agilo project.
    -h, --help                Print this message
    -e, --env=<path>          The new project path
    -n, --name=<Project Name> The new project name
    -d, --db_url=<sqlite:db/trac.db> The db url
    -s, --svn=<repos_path>    The SVN repository path
    -i, --init-demo           Initialize the project with demo data
'''

agilo_wiki = """

= Welcome to Agilo =

== Geting Started ==

To find out how Agilo works you should read the [/agilo-help Help/Guide]. 
This contains all the needed information to work with Agilo. In particular
have a look at the [/agilo-help/QuickStart Quick Start] for setting up
all you need to start using Agilo.

The Scrum '''[/dashboard Dashboard]''' in the main Navigation 
could be a good start to ''get a quick access to the Scrum functionalities.

To shorten the time for you to understand how Agilo work, we created a
demo Release, and a demo Sprint, with some ticket inside, so you can start
by looking into the Product Backlog, and the Sprint Backlog for the demo
Sprint.

== Some Information about how Agilo works ==

In the '''Sprint Backlog''' view you will have the chance to see the 
''Tasks'' in progress as well as who is doing what. Once the team members 
will commit themselves to complete a specific activity, you can assign them
(also as multiple resources) to a that ''Task''. If you will not assign an 
''owner'' to that task, Agilo will ''promote'' the first resource in
the list of resources to owner.

The ''Sprint Backlog'' is grouping tasks by ''User Story'' so that it 
will be easier to get the dependencies right and see which user stories 
have been completed, and can be set to complete. Now the backlog allow 
you to easily sort items by multiple keys as well as via Drag & Drop.

From the dashboard you'll find the possibility to create tasks for the 
next ''Sprint'' (Which is now a native object in agilo), as well as the 
possibility to add new '''Product Backlog''' items. 

In the Dashboard you'll also find the access to many ''Backlogs'' created 
specifically for '''Scrum''', one is the ''Sprint Backlog'' for a specific
Sprint and the other is the ''Product Backlog'' (that you will find also 
in the left sidebar for quicker access).

Have fun and let us know ;-)[[BR]]
The Agilo Software Team[[BR]]


== Scrum & Agilo - A Quick Start Guide ==

To start using Agilo you normally need to build a '''Product Backlog''', 
which is one of the most important artefact in Scrum, a Product Backlog in 
Agilo is build using '''Requirements''' and '''User Stories'''. You can also 
use only '''User Stories''' and customize the whole tool to handle your own 
type of tickets. The '''Product Backlog''' is the list of Requirements and 
related User Stories prioritized by '''Business Value''' that have not yet 
been assigned to any Sprint (a Milestone in the [/roadmap Roadmap]). You 
can also configure the Product Backlog not to be strict (that is will still 
show you also the planned items). We suggest for the purpose of a release 
plan to use a ''Release Backlog'' which will contain all the items planned 
for every Sprint in that release, also when closed.

To create Requirements, as a {{{product_owner}}} go to the 
[/scrum-dashboard Scrum Dashboard] and click on 
[/newticket?type=requirement New Requirement] or click on the left side bar, 
do not set the Milestone property, you normally do not need to set the 
Milestone on a Requirement, because the Team will commit to User Stories. 
You can set a Milestone if you want to plan a Requirement for a specific 
product release, normally the Product Owner does that once the teams are 
good enough in self organizing and have reached a constant velocity, so 
that based on estimation the Product Owner can guess what will enter into 
a Release... but this is a very long story...

Once Requirements are in, you can click on the Edit tab of each Requirement
and use the link "Create a Referenced User Story" to associate User Stories 
to each Requirement. User Stories represent a way to describe the interaction 
between a type of user of your system and the system itself, they are a kind 
of functional specification if you wish. User Stories are great for their 
simplicity, in order order to make them effective for the development team 
remember to write Acceptance Criteria too.

Now you can look at your [/agilo/backlog/Product%20Backlog Product Backlog] 
and use this at the '''Sprint Planning Meeting''' to present to the Team each and 
every User Story. Normally we use a projector or a big screen, introduce the team 
to the bigger picture explaining the whole Requirement (the need that have to be 
fulfilled, you can click on it from the Backlog Report) and dig down into each 
User Story, so that the team has an overview of the whole Requirement.

Once the Team has chosen a Baseline, using the ''Planning Poker'' technique they 
estimate one after the next as many User Stories as will fit into the first half 
of the meeting (time-boxed to 4h, first half is 2h normally). 
The {{{product_owner}}} can update estimations on every User Story, switching to 
the Edit pane and entering the Story Points estimations in the appropriate field, 
or directly in the Product Backlog. When the Team completed the initial estimations, 
it will give an initial commitment in term of which Stories they think they would
be able to successfully implement and release in the next Sprint. At this point the 
{{{product_owner}}} may set the Sprint property to the next Sprint for those chosen
 Stories (this can also be done directly in the Product Backlog, keep in mind that 
 once the stories are planned they will disappear from the Backlog).

Before starting the detailed planning make sure the sprint is well defined and the 
capacity for that sprint set and updated.

 1) Go to [/roadmap Roadmap] and chose the Milestone related to the next Release, 
 and than the right Sprint, or create a new one
 
 2) Set Start and End or duration for a new sprint, keep in mind that agilo will 
 normalized the start and end date to fall into a working day (we know you work 
 also at the weekend but it is not a good practice ;-) )
 
 3) Go to the Scrum Dashboard, the Sprint shown in the "Sprint Backlog for Sprint" 
 should be the one you just set, and so the charts that will eventually display on
  the Dashboard will be related to the next due Sprint
 
 4) At this point in the Sprint Backlog you should see all the Stories, with the 
 related Requirements, that have been committed for this Sprint by the team
 
 5) Now the '''Scrum Master''' can help the Team in breaking down every Story 
 into '''Tasks''', from the Sprint Backlog view he can click on a specific Story, 
 go to the Edit pane, and use the "Create Referenced Task" to create all the 
 needed Tasks for that Story. We normally do not estimate at this point, but we 
 do set estimation directly in the Sprint Backlog view, once all the Tasks for 
 a Story have been defined, this helps the team in having an overall view when 
 estimating. The Scrum Master can enter the estimated time in ''Ideal hours'' 
 (you can also do in ideal days, but this demo server is configured with hours) 
 for each of the task, save the Backlog by pushing the button "Save" on top of 
 the Sprint Backlog.
 
 6) There is also a button "Confirm" that normally appears only the first day 
 of the Sprint, which is meant to be used to "Confirm" the team commitment once 
 a bit more of detailed plan as been made. Agilo also offer the possibility to 
 automatically estimate the 'User Story Point/Ideal Time' ratio and calculate the 
 actual team estimated commitment using the remaining story points. This can be 
 achieved selecting one or more stories that the team consider well defined and 
 estimated and pressing the button "Calculate", this will store in the team metrics 
 for the current sprint the 'User Story Points/Ideal Time' ratio, that will be used 
 to calculate the estimated remaining time. Clicking on "Confirm" will store in 
 metrics the Estimated team velocity, in terms of 'Story Points', the team 
 commitment in terms of committed time, and the capacity for the current sprint. 
 All this information are than shown in the team statistics page, accessible from 
 the menu [/agilo/team Team] than dig down to sprints.

On a daily basis at the '''Daily Scrum''' the Scrum Master while asking the three 
questions:

 - What did you do yesterday?
 - What are you going to do today?
 - What are your impediments
 
May ask also how much time each {{{team_member}}} has left to complete its task, 
and update the Sprint Backlog directly. Each {{{team_member}}} can pick out a Task 
or more than one (even if you should focus!) form the Sprint Backlog, by declaring 
it at the '''Daily Scrum''' the Scrum Master can assign the Task to that 
{{{team_member}}} that will have to ''accept'' it by going to the Sprint Backlog, 
as {{{team_member}}} and clicking on the Edit pane of the Task, choose Accept and 
saving the Task.

All the ''Accepted'' Tasks will appear highlighted in orange in the Sprint Backlog 
view, to help the Team and the Scrum Master in focusing on the most important 
things, avoiding the Team Members to start too many parallels tasks at the same 
time. (We will implement a better workflow for agilo types as soon as possible... 
don't worry)

If you need more advanced tips and tricks, do not hesitate to subscribe and 
participate to our online User Group: http://groups.google.com/group/agilo


== What is Trac? ==

Trac is a '''minimalistic''' approach to '''web-based''' management of
'''software projects'''. Its goal is to simplify effective tracking and 
handling of software issues, enhancements and overall progress.

All aspects of Trac have been designed with the single goal to 
'''help developers write great software''' while '''staying out of the way'''
and imposing as little as possible on a team's established process and
culture.

As all Wiki pages, this page is editable, this means that you can
modify the contents of this page simply by using your
web-browser. Simply click on the "Edit this page" link at the bottom
of the page. WikiFormatting will give you a detailed description of
available Wiki formatting commands.

"[wiki:TracAdmin trac-admin] ''yourenvdir'' initenv" created
a new Trac environment, containing a default set of wiki pages and some sample
data. This newly created environment also contains 
[wiki:TracGuide documentation] to help you get started with your project.

You can use [wiki:TracAdmin trac-admin] to configure
[http://trac.edgewall.org/ Trac] to better fit your project, especially in
regard to ''components'', ''versions'' and ''milestones''. 


TracGuide is a good place to start.

Enjoy! [[BR]]
''The Trac Team''

== Starting Points ==

 * TracGuide --  Built-in Documentation
 * [http://trac.edgewall.org/ The Trac project] -- Trac Open Source Project
 * [http://trac.edgewall.org/wiki/TracFaq Trac FAQ] -- Frequently Asked Questions
 * TracSupport --  Trac Support

For a complete list of local wiki pages, see TitleIndex.
"""

class Usage(Exception):
    def __init__(self, msg):
        self.msg = msg


class AgiloAdmin(TracAdmin):
    """Wraps the TracAdmin console command to create an Agilo project.
    It creates a trac environment and enable on it Agilo."""
    def initialize_agilo(self, project_name, db_url, svn_repo, demo=False):
        try:
            self.do_initenv('%s %s %s %s' % (project_name,
                                             db_url, 'svn', 
                                             svn_repo or 'somewhere'))
            # Now add agilo and the template path
            env = Environment(self.envname)
            ac = AgiloConfig(env)
            if not svn_repo:
                # remove the fake from the config
                ac.change_option('repository_dir', '', 'trac')
            # sets the restric_owner option
            ac.change_option('restrict_owner',
                             'true',
                             'ticket')
            # this is also saving the config
            ac.enable_agilo()
            # update wiki
            wiki = WikiPage(env, name='WikiStart')
            wiki.text = agilo_wiki
            wiki.save('admin', 'Updated to Agilo', '127.0.0.1')
            # reset the env
            self.env_set(envname=self.envname, env=env)
            # Now initialize Agilo
            self.do_upgrade('upgrade --no-backup')
            # Now create the demo if needed
            if demo:
                try:
                    from create_demo_data import _create_demo_data
                    _create_demo_data(env)
                except ImportError, e:
                    env.log.error(exception_to_unicode(e))
        except:
            pass

def main(argv=None):
    if argv is None:
        argv = sys.argv
    try:
        try:
            opts, args = getopt.getopt(argv[1:], "e:n:d:s:hi", ["env=", 
                                                               "name=",
                                                               "db_url=",
                                                               "svn=",
                                                               "help",
                                                               "init-demo"])
        except getopt.error, msg:
            raise Usage(msg)
        
        if len(opts) == 0:
            raise Usage(help_message)
        
        path = svn_repo = None
        demo = False
        project_name = '"My Agilo Project"'
        db_url = 'sqlite:db/trac.db'
        # option processing
        for option, value in opts:
            if option in ("-h", "--help"):
                raise Usage(help_message)
            elif option in ("-e", "--env"):
                path = value
            elif option in ("-n", "--name"):
                project_name = value
            elif option in ("-d", "--db-url"):
                db_url = value
            elif option in ("-s", "--svn"):
                svn_repo = value
            elif option in ("-i", "--init-demo"):
                demo = True
        # Now lets create the env
        if not path:
            raise Usage(help_message)
        
        admin = AgiloAdmin(path)
        admin.initialize_agilo(project_name, db_url, svn_repo, demo)
        
    except Usage, err:
        print >> sys.stderr, sys.argv[0].split("/")[-1] + ": " + str(err.msg)
        print >> sys.stderr, "\t for help use --help"
        return 2


if __name__ == "__main__":
    sys.exit(main())