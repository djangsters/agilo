#   Copyright 2007 Andrea Tomasini <andrea.tomasini_at_agile42.com>
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
#   Authors:
#       - Andrea Tomasini <andrea.tomasini__at__agile42.com>

from trac.core import Component, ExtensionPoint, Interface

from agilo.utils.log import debug


class RuleValidationException(Exception):
    """Thrown when a validation fails"""
    pass


class IRule(Interface):
    """
    Represent a Business Rule, that registers for a specific domain to the
    RuleEngine.
    """
    def validate(self, ticket):
        """
        Called when a Rule need to be validated, it should take care of checking
        the ticket type, if the validation fails raise a RuleValidationException
        """


class RuleEngine(Component):
    """
    Used to check that all the business rules are met before completing an
    operation. The RuleEngine has different domains where the rules applies
    and can be called from the specific object when is saved
    """
    rules = ExtensionPoint(IRule)
    
    def __init__(self):
        """Make sure that all the rules are instantiated and registered"""
        from agilo.scrum.workflow import rules
        for member in dir(rules):
            if type(member) == type and issubclass(member, Component):
                member(self.env)
        
    def validate_rules(self, ticket):
        """
        Validates the give ticket against the registered rules. Every rule
        will be validated and has to take care of all the checks, return True
        or False
        """
        debug(self, "Called validate_rules(%s)" % ticket)
        for r in self.rules:
            r.validate(ticket)
        