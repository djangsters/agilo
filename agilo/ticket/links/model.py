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

from trac.core import Component

from agilo.ticket.links import LinkOption
from agilo.ticket.links.configuration_parser import parse_calculated_fields_definition
from agilo.ticket.links.operators import operators
from agilo.utils.log import debug


__all__ = ['LinksConfiguration']

# RegExp to get operand for the calculation
CALCULATE = re.compile(r'^(?P<l_val>\w+)=(?P<oper>[a-z]+):(?P<r_val>[\w\/]+)(\|(?P<opts>.+))*$')



# Models used from the linking infrastructure
class AllowedLink(object):
    """Represent a pair src_type->dest_type of allowed link"""
    def __init__(self, src_type, dest_type):
        self._src_type = src_type
        self._dest_type = dest_type
        self._options = None
        
    def add_option(self, name, value):
        """Adds an Option=Value pair to this allowed link"""
        if not self._options:
            self._options = dict()
        self._options[name] = value
        
    def get_option(self, name):
        """Returns the given option value if exsting"""
        if self._options and name in self._options:
            return self._options[name]
        else:
            return []
                    
    def __unicode__(self):
        return u"%s-%s (options: %s)" % (self._src_type, self._dest_type, 
                                         str(self._options))

    def __str__(self):
        return '%s-%s (options: %s)' % (repr(self._src_type), 
                                        repr(self._dest_type), 
                                        repr(self._options))
        
    def get_src_type(self):
        return self._src_type
        
    def get_dest_type(self):
        return self._dest_type
        
    src_type = property(fget=get_src_type, doc='src_type')
    dest_type = property(fget=get_dest_type, doc='dest_type')


def _get_option(config_option, option):
    """
    Utility to add link options to the given link allow, the config option
    is a valid multilevel option in the agilo-links configuration. For example
    src.dest.copy, or src.dest.calculate or src.dest.show
    """
    fields = None
    if isinstance(config_option, basestring):
        fields = [item.strip() for item in config_option.split(',')]
    else:
        fields = list(config_option)
    return fields


class LinksConfiguration(Component):
    """All the link related configuration parameters"""
    def __init__(self):
        self._configs = dict()
        self._initialized = False
        self._currently_initializing = False
        
        # List of calculated properties found
        self._calculated_propertynames = list()
        self._calculated_properties_by_type = dict()
        # Now initialize it
        self.initialize()
        
    def get_calculated(self):
        """Returns the list of calculated properties read from the config"""
        self.initialize_if_necessary()
        return self._calculated_propertynames
        
    def is_initialized(self):
        """Returns true if at least one allowed link couple has been configured"""
        return self._initialized
    
    def initialize(self):
        """Initialize the links configuration from the give config key"""
        self._currently_initializing = True
        
        # Prevent recursive imports (AgiloConfig needs to import the ticket
        # module)
        from agilo.utils.config import AgiloConfig
        if self._initialized and AgiloConfig(self.env).is_agilo_enabled:
            return
        
        links = AgiloConfig(self.env).get_section(AgiloConfig.AGILO_LINKS)
        for pair in links.get_list(LinkOption.ALLOW):
            if pair.find('-') == -1:
                continue
            self._parse_option(pair, links)
        # Set to initialized
        self._initialized = True
        self._currently_initializing = False


    def extract_types(self, pair):
        src = dest = None
        from agilo.utils.config import AgiloConfig
        available_types = AgiloConfig(self.env).get_available_types()

        for ticket_type in available_types:
            if len(pair.split(ticket_type)) == 1 or pair.split(ticket_type)[0] != '':
                continue
            src = ticket_type
            dest = "".join(pair.split(src))[1:]

        return src, dest

    def _parse_option(self, pair, link_config):
        src, dest = self.extract_types(pair)
        alink = self.add_allowed(src, dest)
        for prop in (LinkOption.COPY, LinkOption.SHOW):
            fields_s = link_config.get('%s.%s.%s' % (src, dest, prop))
            if fields_s is not None:
                alink.add_option(prop, _get_option(fields_s, prop))
        # Special case for calculate: we have to parse the CALCULATE
        # Option to check if matches the regexp, and we can already
        # store a pointer to the operation instead of the simple 
        # string
        fields_s = link_config.get('%s.%s' % (src, LinkOption.CALCULATE))
        attribute_data = \
            parse_calculated_fields_definition(fields_s, component=self)
        if attribute_data is not None:
            for property_name in attribute_data:
                if property_name not in self.get_calculated():
                    self._calculated_propertynames.append(property_name)
            if src not in self._calculated_properties_by_type:
                self._calculated_properties_by_type[src] = {}
            self._calculated_properties_by_type[src].update(attribute_data)
        
        # Get the sorting options and reverse them to keep logical
        # order with stable sorting
        fields_s = link_config.get('%s.%s.%s' % (src, dest, LinkOption.SORT))
        if fields_s is not None:
            alink.add_option(LinkOption.SORT, 
                             reversed(_get_option(fields_s, LinkOption.SORT)))
    
    def reinitialize(self):
        self._configs = dict()
        self._calculated_propertynames = list()
        self._calculated_properties_by_type = dict()
        self._initialized = False
        self.initialize_if_necessary()
    
    def initialize_if_necessary(self):
        if self.is_initialized() or self._currently_initializing:
            return
        self.initialize()
    
    def add_allowed(self, src_type, dest_type):
        """Add the dest_type as an allowed link end point for src_type"""
        self.initialize_if_necessary()
        if src_type not in self._configs:
            self._configs[src_type] = dict()
        if dest_type not in self._configs[src_type]:
            self._configs[src_type][dest_type] = dict()
        al = AllowedLink(src_type, dest_type)
        self._configs[src_type][dest_type] = al
        if not self._initialized:
            self._initialized = True
        return al
        
    def get_alloweds(self, src_type):
        """Returns the list of the AllowedLink objects with source = src_type"""
        self.initialize_if_necessary()
        if src_type in self._configs:
            return self._configs[src_type].values()
        else:
            return []
        
    def get_allowed_destination_types(self, src_type):
        """Returns the list of dest_type links for the src_type"""
        self.initialize_if_necessary()
        if src_type in self._configs:
            return self._configs[src_type].keys()
        else:
            return []
            
    def is_allowed_source_type(self, src_type):
        """Returns true if the given type is allowed to be a link originator"""
        self.initialize_if_necessary()
        return src_type in self._configs
        
    def add_option(self, src_type, dest_type, option_name, option_value):
        """Adds the given option_name=option_value to the link src_type->dest_type"""
        self.initialize_if_necessary()
        if src_type in self._configs and dest_type in self._configs[src_type]:
            self._configs[src_type][dest_type].add_option(option_name, option_value)
    
    def get_option(self, src_type, dest_type, option_name):
        """Returns the option with the given name from the link relation src_type->dest_type"""
        self.initialize_if_necessary()
        if src_type in self._configs and \
            dest_type in self._configs[src_type] and \
                option_name in self._configs[src_type][dest_type]:
                    return self._configs[src_type][dest_type].get_option(option_name)

    def __unicode__(self):
        """Returns a Unicode representation of the LinksConfiguration."""
        return unicode(self._configs)
        
    def __repr__(self):
        return repr(self._configs)

