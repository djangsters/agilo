#   Copyright 2008 Agile42 GmbH, Berlin (Germany)
#   Copyright 2007 Andrea Tomasini <andrea.tomasini__at__agile42.com>
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
#   Author: 
#            - Andrea Tomasini <andrea.tomasini__at__agile42.com>


class NotOwnerError(Exception):
    """
    Error to be used when an Agilo user tries to modify a ticket
    without being the owner
    """
    

class NotAssignedError(Exception):
    """
    Error to be used when some operation is attempted on a ticket
    which has not yet been assigned, and it is otherwise not authorized.
    For example to close a Task which has not been assigned.
    """

    
class DependenciesError(Exception):
    """
    Error to be used in case some operation on a ticket is not allowed
    given the fact that some of its dependencies are in a particular
    state. For example: if someone tries to close a Story that still has
    open tasks.
    """

class ParsingError(Exception):
    """
    Error to be used in case there are some error during the paring of
    some text using regular expressions.
    """
    
class InvalidAttributeError(Exception):
    """
    Error to be used when there is an attempt to access an attribute of
    a type, which is not defined or supported for that type.
    """