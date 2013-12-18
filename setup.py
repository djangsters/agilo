# -*- coding: utf8 -*-
#   Copyright 2007,2008 Andrea Tomasini <andrea.tomasini_at_agile42.com>,
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
import sys

try:
    from ez_setup import use_setuptools
    use_setuptools()
except ImportError:
    pass #Is installing from a source package is not copied locally
from setuptools import setup, find_packages
from agilo import __package__, __version__
from sys import version_info as python_version

install_requires=['trac >= 0.12',
                  'genshi >= 0.5.1',
                  ]

if python_version < (2, 5):
    sys.stderr.write("This version of Agilo requires Python 2.5 up to 2.7")
    sys.exit(-1)

elif python_version < (2, 6):
    install_requires.append('simplejson')


setup(
    name=__package__,
    version=__version__,
    author='Andrea Tomasini, Felix Schwarz, Garbrand van der Molen, Jonas von Poser, Martin Häcker, Robert Buchholz, Sebastian Schulze, Thom Bradford, Stefano Rago',
    author_email='support@agilosoftware.com',
    # this specific url is needed for trac's semi-automatic faulty plugin detection
    # see http://www.edgewall.org/docs/branches-0.12-stable/epydoc/trac.web.main-pysrc.html#send_internal_error
    url='http://trac-hacks.org/wiki/AgiloForTracPlugin',
    description='Agilo for trac is a simple and straightforward tool to support the Scrum process.',
    license='Apache License 2.0',
    packages=find_packages(exclude=['tests', 'functional_tests']),
    scripts=['scripts/agilo_svn_hook_commit.py',
             'scripts/agilo_sqlite2pg.py',
             'scripts/create_agilo_project.py'],
    include_package_data = True,
    entry_points = {'trac.plugins': [
                                     'agilo.admin = agilo.admin',
                                     'agilo.api.web_ui = agilo.api.web_ui',
                                     'agilo.charts = agilo.charts',
                                     'agilo.csv_import.web_ui = agilo.csv_import.web_ui',
                                     'agilo.help = agilo.help',
                                     'agilo.help.search = agilo.help.search',
                                     'agilo.init = agilo.init',
                                     
                                     'agilo.scrum = agilo.scrum',
                                     'agilo.scrum.workflow.rules = agilo.scrum.workflow.rules',
                                     
                                     'agilo.ticket = agilo.ticket',
                                     'agilo.ticket.web_ui = agilo.ticket.web_ui',
                                     'agilo.ticket.json_ui = agilo.ticket.json_ui',
                                     'agilo.ticket.links = agilo.ticket.links',
                                     
                                     'agilo.utils.compatibility_warner = agilo.utils.compatibility_warner',
                                     'agilo.utils.permissions = agilo.utils.permissions',
                                     'agilo.utils.web_ui = agilo.utils.web_ui',
                                    ],
                    
                    # we need separate declarations - otherwise nose will choke
                    # because we implement two plugins in the same module...
                    # even though the entrypoint name is 'nose.plugins.0.10', 
                    # this valid also for nose 0.11.
                    'nose.plugins.0.10': [
                                          'nose_testselector = agilo.test.nose_testselector:NoseClassAttributeSelector',
                                          'exclude_unittest_runners = agilo.test.nose_testselector:NoseExcludeUnittestRunnerFunctions',
                                          'environment_manager = agilo.test.functional.nose_environment_manager:NoseEnvironmentManager',
                                         ],
    },
    package_data = {'': ['templates/*']},
    install_requires=install_requires,
    test_suite='agilo.test.build_functional_test_suite',
)
