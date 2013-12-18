# -*- coding: utf-8 -*-
#   Copyright 2007-2009 Agile42 GmbH - Andrea Tomasini 
#   Copyright 2011 Agilo Software GmbH All rights reserved
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
# 
# Authors:
#     - Felix Schwarz <felix.schwarz__at__agile42.com>
#     - Andrea Tomasini <andrea.tomasini__at__agile42.com>

from genshi.builder import tag
from trac.core import Component, implements, TracError
from trac.resource import IResourceManager
from trac.util.translation import _

from agilo.api import validator
from agilo.api import Controller, ICommand, ValueObject
from agilo.charts import ChartGenerator
from agilo.scrum.contingent import ContingentModelManager, Contingent
from agilo.scrum.sprint import SprintModelManager
from agilo.utils import Realm


__all__ = ['ContingentController']

CONTINGENTS_URL = '/contingents'


class ContingentController(Controller):
    
    def __init__(self):
        self.sp_manager = SprintModelManager(self.env)
        self.c_manager = ContingentModelManager(self.env)
    
    def list(self, sprint):
        cmd_list = ContingentController.ListSprintContingentCommand(self.env, sprint=sprint)
        return self.process_command(cmd_list)
    
    class ListSprintContingentCommand(ICommand):
        """Returns a list of contingents for the given sprint"""
        parameters = {'sprint': validator.MandatorySprintValidator}
        
        def _execute(self, cont_controller, date_converter=None, as_key=None):
            contingents = cont_controller.c_manager.select(criteria={'sprint': self.sprint.name})
            return self.return_as_value_object(contingents)
    
    def summed_contingents(self, sprint):
        cmd_list = ContingentController.GetSprintContingentTotalsCommand(self.env, sprint=sprint)
        return self.process_command(cmd_list)
    
    class GetSprintContingentTotalsCommand(ICommand):
        """Returns a list of contingents total hours for the given 
        sprint name"""
        parameters = {'sprint': validator.MandatorySprintValidator}
        
        def _execute(self, cont_controller, date_converter=None, as_key=None):
            contingents = cont_controller.c_manager.select(criteria={'sprint': self.sprint.name})
            contingent_amount = sum([i.amount for i in contingents])
            contingent_actual = sum([i.actual for i in contingents])
            return ValueObject(amount=contingent_amount,
                               actual=contingent_actual)
    
    
    def get(self, name, sprint):
        cmd_get = ContingentController.GetContingentCommand(self.env, name=name, sprint=sprint)
        return self.process_command(cmd_get)
    
    
    class GetContingentCommand(ICommand):
        
        parameters = {'sprint': validator.MandatorySprintValidator,
                      'name': validator.MandatoryStringValidator}
        
        def _execute(self, controller, date_converter=None, as_key=None):
            return controller.c_manager.get(sprint=self.sprint, name=self.name)
    
    
    class AddTimeToContingentCommand(ICommand):
        
        parameters = {'sprint': validator.MandatorySprintValidator,
                      'delta': validator.IntOrFloatValidator,
                      'name': validator.MandatoryStringValidator}
        
        def _execute(self, controller, date_converter=None, as_key=None):
            contingent = controller.get(sprint=self.sprint, name=self.name)
            if contingent:
                assert contingent.name == self.name
                assert contingent.sprint.name == self.sprint.name
                try:
                    contingent.add_time(self.delta)
                except Contingent.ExceededException, e:
                    exceeded_time = round(e.amount, 2)
                    base_text = _('Amount for contingent %s exceeded by %s')
                    error_msg = base_text % (self.name, exceeded_time)
                    raise self.CommandError(error_msg)
                except Contingent.UnderflowException:
                    raise self.CommandError(_('Amount for contingent must not be negative'))
                controller.c_manager.save(contingent)
    
    
    class AddContingentCommand(ICommand):
        
        parameters = {'sprint': validator.MandatorySprintValidator,
                      'amount': validator.MandatoryStringValidator,
                      'name': validator.MandatoryStringValidator}

        def consistency_validation(self, env):
            # REFACT: this should really be the existing instance
            controller = ContingentController(env)
            
            existing_contingent = controller.get(self.name, self.sprint)
            if existing_contingent is not None:
                self.not_valid('already exists', 'contingent', self.name)
        
        def _execute(self, controller, date_converter=None, as_key=None):
            params = {'name': self.name, 'sprint': self.sprint}
            if self.amount.strip().endswith('%'):
                try:
                    params['percent'] = float(self.amount[:-1])
                except ValueError:
                    raise TracError(_('Invalid percentage provided...'))
            else:
                try:
                    params['amount'] = float(self.amount)
                except ValueError:
                    raise TracError(_('Invalid number for amount: %s') % repr(self.amount))
            # Create the contingent
            controller.c_manager.create(**params)
            ChartGenerator(controller.env).invalidate_cache(sprint_name=self.sprint.name)
    
    
    class DeleteContingentCommand(ICommand):
        
        parameters = {'sprint': validator.MandatorySprintValidator,
                      'name': validator.MandatoryStringValidator}
        
        def _execute(self, controller, date_converter=None, as_key=None):
            contingent = controller.get(sprint=self.sprint, name=self.name)
            assert contingent.name == self.name
            assert self.sprint.name == contingent.sprint.name, '%s != %s ' % (repr(self.sprint.name), repr(contingent.sprint.name))
            if controller.c_manager.delete(contingent):
                ChartGenerator(controller.env).invalidate_cache(sprint_name=self.sprint.name)


class ContingentResourceManager(Component):
    
    implements(IResourceManager)
    
    def get_resource_realms(self):
        yield Realm.CONTINGENT
    
    def get_resource_description(self, resource, format=None, context=None,
                                 **kwargs):
        desc = resource.id
        if format != 'compact':
            desc =  _('Contingent %(name)s') % dict(name=resource.id)
        if context:
            return self._render_link(context, resource.id, desc)
        else:
            return desc
    
    def _render_link(self, context, name, label, extra=''):
        """Renders the Contingent as a link"""
        contingent = self.c_manager.get(name=name)
        href = context.href(CONTINGENTS_URL, name)
        if contingent and contingent.exists:
            severity = (contingent.is_critical and 'critical ') or \
                       (contingent.is_warning and 'warning ') or ''
            return tag.a(label, class_='%scontingent' % severity, href=href+extra)
        else: 
            return tag.a(label, class_='missing contingent', href=href+extra,
                         rel="nofollow")



