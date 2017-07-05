#!/usr/bin/env python3
# Copyright (C) 2017  Ghent University
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
import uuid
import logging

from juju import JujuRelationSE
from ModelManager import ModelManager
from helpers import merge_dicts, RelationEngine

logger = logging.getLogger('oa')


class HadoopOA(ModelManager):
    def __init__(self, **kwargs):
        super(HadoopOA, self).__init__(oe=HadoopOE, kwargs=kwargs)


class HadoopWorkerSA(ModelManager):
    def __init__(self, **kwargs):
        super(HadoopWorkerSA, self).__init__(oe=HadoopWorkerSE, kwargs=kwargs)


class HadoopResourcemanagerSA(ModelManager):
    def __init__(self, **kwargs):
        super(HadoopResourcemanagerSA, self).__init__(oe=HadoopResourcemanagerSE, kwargs=kwargs)


class HadoopNamenodeSA(ModelManager):
    def __init__(self, **kwargs):
        super(HadoopNamenodeSA, self).__init__(oe=HadoopNamenodeSE, kwargs=kwargs)


class HadoopOE(RelationEngine):
    def __init__(self, modelmanager, name=None):
        if not all([name]):
            print("WARNING, params wrong")
        super(HadoopOE, self).__init__()
        self._modelmanager = modelmanager

        self._name = name
        self._num_workers = 1

        self._children = {
            'namenode': HadoopNamenodeSA.start(
                name='namenode', charm='hadoop-namenode').proxy(),
            'resourcemanager': HadoopResourcemanagerSA.start(
                name='resourcemanager', charm='hadoop-resourcemanager').proxy(),
            'worker': HadoopWorkerSA.start(
                name='worker', charm='hadoop-worker').proxy(),
        }
        self._children['namenode'].update_model({
            'num_units': 1
        })
        self._children['resourcemanager'].update_model({
            'num_units': 1
        })
        self._children['worker'].update_model({
            'num_units': 1
        })

        for childref in self._children.values():
            childref.subscribe(self.actor_ref.proxy())

        t_uuid = uuid.uuid4()
        self._children['namenode'].add_relation(
            t_uuid,
            self._children['worker'],
            True)
        self._children['worker'].add_relation(
            t_uuid,
            self._children['namenode'],
            False)

        t_uuid = uuid.uuid4()
        self._children['resourcemanager'].add_relation(
            t_uuid,
            self._children['worker'],
            True)
        self._children['worker'].add_relation(
            t_uuid,
            self._children['resourcemanager'],
            False)

        t_uuid = uuid.uuid4()
        self._children['namenode'].add_relation(
            t_uuid,
            self._children['resourcemanager'],
            True)
        self._children['resourcemanager'].add_relation(
            t_uuid,
            self._children['namenode'],
            False)
        self._push_new_state()

    def _push_new_state(self):
        ready = True
        num_workers = 0
        for (name, childref) in self._children.items():
            childstate = childref.view_state().get()
            logger.debug("child: {}".format(childstate))
            if childstate and childstate['ready']:
                if name == "worker":
                    num_workers = childstate['num_units']
            else:
                ready = False
        self._modelmanager.update_state({
            'name': self._name,
            'num_workers': num_workers,
            'ready': ready,
            'relations': self._get_child_states(),
        })

    def on_stop(self):
        for proxy in self._children.values():
            proxy.stop()

    def update_model(self, new_model):
        if new_model.get('num_workers'):
            self._num_workers = new_model.get('num_workers')
            self._children['worker'].update_model({
                'num_units': new_model.get('num_workers'),
            })

    def concrete_model(self):
        c_mod = {}
        logger.debug('I have {} children'.format(len(self._children)))
        for se in self._children.values():
            c_mod = merge_dicts(se.concrete_model().get(), c_mod)
        return c_mod

    def notify_new_state(self, actor_ref):
        self._push_new_state()

    def on_failure(self, exception_type, exception_value, traceback):
        logger.debug("FAILED! {} {} {}".format(exception_type, exception_value, traceback))
        self.on_stop()


class HadoopNamenodeSE(JujuRelationSE):
    def __init__(self, modelmanager, **kwargs):
        super(HadoopNamenodeSE, self).__init__(modelmanager, **kwargs)
        self._required_relations = {'resourcemanager', 'worker'}


class HadoopResourcemanagerSE(JujuRelationSE):
    def __init__(self, modelmanager, **kwargs):
        super(HadoopResourcemanagerSE, self).__init__(modelmanager, **kwargs)
        self._required_relations = {'namenode', 'worker'}


class HadoopWorkerSE(JujuRelationSE):
    def __init__(self, modelmanager, **kwargs):
        super(HadoopWorkerSE, self).__init__(modelmanager, **kwargs)
        self._required_relations = {'namenode', 'resourcemanager'}


class HadoopPluginSE(JujuRelationSE):
    def __init__(self, modelmanager, **kwargs):
        super(HadoopPluginSE, self).__init__(modelmanager, **kwargs)
        self._required_relations = {'namenode', 'resourcemanager'}
