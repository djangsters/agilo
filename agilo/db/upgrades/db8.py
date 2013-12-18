# -*- encoding: utf-8 -*-
#   Copyright 2010 Agile42 GmbH, Berlin (Germany)
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

# For the next migration we need to build a db0 that creates the environment as of Agilo 0.6
# Then we need to modify all migration scripts so that they:
# - drop all tables from agilo, remove config (or use separate plain trac env)
# - disable Agilo in TestEnvHelper
# - replay old migrations

# TODO: Figure out how this works with a shared database in functional tests
#    fs: However it might not be a problem because the migration should create an acceptable state

# REFACT: Consider renaming them to environment upgrades
