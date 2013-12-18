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

from agilo.utils.log import warning

__all__ = ["operators", "AgiloConfigSyntaxError"]


class AgiloConfigSyntaxError(Exception): pass


class BaseOperator(object):
    def __init__(self, property_string, condition_string=None, component=None):
        self.properties = self._parse_property_names(property_string)
        self.conditions = self._parse_conditions(condition_string)
        self.component = component
    
    def _parse_property_names(self, property_string):
        raw_property_names = property_string.split(";")
        property_names = []
        for item in raw_property_names:
            if item != '':
                if item.startswith('.') or item.endswith('.') or '..' in item:
                    raise AgiloConfigSyntaxError('Invalid namespace')
                property_names.append(item)
        if len(property_names) == 0:
            raise AgiloConfigSyntaxError('No values given')
        return property_names
    
    def _parse_conditions(self, condition_string):
        conditions = []
        if condition_string != None:
            if not '=' in condition_string:
                raise AgiloConfigSyntaxError('No condition found')
            for single_conditions_string in condition_string.split('|'):
                condition_property_name, possible_values = single_conditions_string.split('=', 1)
                if ':' in possible_values:
                    possible_values = possible_values.split(':')
                else:
                    possible_values = [possible_values]
                conditions.append((condition_property_name, possible_values))
        return conditions
    
    def _is_iterable(self, value):
        """This method returns True if value is an instance of list.
        
        We check for lists (instead of iterables by using "iter(value)") 
        because:
          - strings must not be treated as iterable in this method
          - every object with __getitem__ returns an iterator, too so 
            AgiloTicket would be treated as iterable
          - TeamMetrics have an __iter__ method though we want to access only
            the specified metrics value (not iterate over all stored 
            TeamMetrics values)
        """
        return isinstance(value, list)
    
    def _satisfies_condition(self, ticket):
        if self.conditions != None:
            for (condition_property_name, possible_values) in self.conditions:
                value = ticket[condition_property_name]
                condition_satisfied = value in possible_values
                if not condition_satisfied:
                    return False
        return True
    
    def _get_values_for_property_name(self, ticket, property_name):
        values = []
        found_attribute = False
        
        property_names = property_name.split('.', 1)
        name = property_names[0]
        property_value = None
        
        try:
            property_value = getattr(ticket, name)
            found_attribute = True
        except AttributeError:
            found_attribute = False
        
        if not found_attribute:
# We can't rely on the ticket's knowlegde of its fields because the
# alias module will replace the type which will cause all fields to
# be resetted to []
#            if hasattr(ticket, 'is_readable_field'):
#                if ticket.is_readable_field(name):
#                    property_value = ticket[name]
#                    found_attribute = True
#            else:
                try:
                    property_value = ticket[name]
                    found_attribute = (property_value != None)
                except TypeError:
                    pass
        if not found_attribute and self.component:
            msg = u"No attribute '%s' found in '%s'" % (ticket, name)
            warning(self.component, msg)
        
        if found_attribute and callable(property_value):
            # for performance reasons, tickets of types which are not included in the backlog are not loaded
            # so here we need to force loading them for the calculation to be correct
            if str(property_value.__name__) == 'get_outgoing' or str(property_value.__name__) == 'get_incoming':
                property_value = property_value(force_reload=True)
            else:
                property_value = property_value()
            found_attribute = (property_value != None)
        
        if found_attribute:
            if self._is_iterable(property_value):
                for item in property_value:
                    values.append((ticket, item))
            else:
                values.append((ticket, property_value))
            if len(property_names) > 1:
                if len(values) == 0:
                    # A empty list was retrieved from the ticket 
                    values = None
                else:
                    real_values = []
                    attribute_name = property_names[1]
                    for old_base_object, item in values:
                        real_value = self._get_values_for_property_name(item, attribute_name)
                        if real_value != None:
                            real_values.extend(real_value)
                    if len(values) == 1 and len(real_values) == 0:
                        real_values = None
                    values = real_values
        else:
            values = None
        return values
    
    def __call__(self, ticket):
        do_calculation = True
        
        values = []
        for property_name in self.properties:
            property_values = self._get_values_for_property_name(ticket, property_name)
            if property_values == None:
                do_calculation = False
                break
            for base_object, property_value in property_values:
                if self._satisfies_condition(base_object):
                    values.append(property_value)
        if do_calculation:
            return self.calculate(values)
        return None
    
    def calculate(self, properties):
        raise NotImplementedError


class SummingOperator(BaseOperator):
    def calculate(self, values):
        result = None
        for item in values:
            try:
                value = float(item)
                if result == None:
                    result = 0
                result += value
            except:
                # The value may be None or an arbitrary string, we don't care.
                # Just ignore the exception. We should not log them because else
                # users will see errors in their logs which are mostly harmless
                pass
        return result


class DivOperator(BaseOperator):
    def calculate(self, values):
        result = None
        if len(values) != 2:
            msg = u"Number of values given for division operator is " + \
                  u"invalid - expected 2, got %d" % len(values)
            #print msg
        else:
            try:
                dividend = float(values[0])
                divisor = float(values[1])
            except:
                # The value may be None or an arbitrary string, we don't care.
                # Just ignore the exception. We should not log them because else
                # users will see errors in their logs which are mostly harmless
                pass
            else:
                try:
                    result = dividend / divisor
                except ZeroDivisionError:
                    pass
        return result


class MultiplicationOperator(BaseOperator):
    def calculate(self, values):
        result = None
        for item in values:
            try:
                value = float(str(item))
                if result == None:
                    # If no multiplication took place, None should be returned
                    result = 1
                result *= value
            except (ValueError, TypeError), e:
                # The value may be None or an arbitrary string, we don't care.
                # Just ignore the exception. We should not log them because else
                # users will see errors in their logs which are mostly harmless
                pass
        return result


operators = {"div": DivOperator, "mul": MultiplicationOperator, "sum": SummingOperator}
