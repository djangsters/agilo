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

import re

from agilo.ticket.links import LinkOption
from agilo.utils.log import debug, error

__all__ = ["parse_calculated_field", "parse_calculated_fields_definition"]


# RegExp to get operand for the calculation
CALCULATE = re.compile(r'^(?P<name>\w+?)\s*=\s*(?P<operator>\w+)\s*:\s*(?P<values>(?:\w|\.|;\s*)+)\s*(\|(?P<conditions>.+))*$')

from agilo.ticket.links.operators import AgiloConfigSyntaxError, operators

def parse_calculated_field(configstring, component=None):
    result = None
    if configstring != None and configstring.strip() != "":
        match = CALCULATE.match(configstring)
        if match:
            field_name = match.group('name')
            operator_name = match.group('operator')
            values = match.group('values')
            conditions = match.group('conditions')
            if operator_name in operators:
                operator = operators[operator_name]
                try:
                    result = (field_name, operator(values, condition_string=conditions))
                    if component:
                        base_msg = u"Setting calculated property: %s => %s:%s|%s"
                        msg = base_msg % (field_name, operator_name, values, conditions)
                        debug(component, msg)
                except AgiloConfigSyntaxError, e:
                    if component:
                        msg = u"Error while parsing calculated property '%s': %s"
                        error(component, msg % (field_name, unicode(e)))
            else:
                if component:
                    error(component, u"Unkown operator name '%s'" % field_name)
    return result



def _get_option(config_option, option):
    fields = None
    if isinstance(config_option, basestring):
        fields = [item.strip() for item in config_option.split(',')]
    else:
        fields = list(config_option)
    return fields


def parse_calculated_fields_definition(configstring, component=None):
    calculated_properties = {}
    if configstring != None:
        property_definitions = _get_option(configstring, LinkOption.CALCULATE)
        for definitionstring in property_definitions:
            property_definition = parse_calculated_field(definitionstring, component)
            if property_definition != None:
                name, operator_def = property_definition
                calculated_properties[name] = operator_def
    return calculated_properties


