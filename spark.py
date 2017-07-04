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
import logging

import pykka

from juju import JujuRelationSE
from ModelManager import ModelManager
from helpers import merge_dicts

logger = logging.getLogger('oa')


class SparkOA(ModelManager):
    def __init__(self, **kwargs):
        super(SparkOA, self).__init__(oe=SparkOE, kwargs=kwargs)


class SparkSA(ModelManager):
    def __init__(self, **kwargs):
        super(SparkSA, self).__init__(oe=SparkSE, kwargs=kwargs)


class SparkOE(pykka.ThreadingActor):
    def __init__(self, modelmanager, name='spark'):
        super(SparkOE, self).__init__()
        self._modelmanager = modelmanager

        self._name = name
        self._num_workers = 1

        self._children = {
            'spark': SparkSA.start(name='spark', charm='spark').proxy(),
        }
        self._children['spark'].update_model({
            'num_units': 4,
        })
        self._children['spark'].subscribe(self.actor_ref.proxy())
        self._push_new_state()

    def _push_new_state(self):
        state = self._children['spark'].view_state().get()
        print("state: {}".format(state))
        self._modelmanager.update_state({
            'name': self._name,
            'num_workers': state.get('num_units', 0),
            'ready': state.get('ready', False),
        })
        print("UPDDDDDDDDDDDDDDDDDDDDDDDDDD")

    def on_stop(self):
        for proxy in self._children.values():
            proxy.stop()

    def update_model(self, new_model):
        if new_model.get('num_workers'):
            self._num_workers = new_model.get('num_workers')
            self._children['spark'].update_model({
                'num_units': new_model.get('num_workers'),
            })

    def concrete_model(self):
        c_mod = {}
        logger.debug('I have {} children'.format(len(self._children)))
        for se in self._children.values():
            c_mod = merge_dicts(se.concrete_model().get(), c_mod)
        return c_mod

    def notify_new_state(self, actor_ref):
        print("NEW STATE")
        self._push_new_state()

    def on_failure(self, exception_type, exception_value, traceback):
        logger.error("FAILED! {} {} {}".format(exception_type, exception_value, traceback))
        self.on_stop()


class SparkSE(JujuRelationSE):
    def add_relation(self, relid, remote, provides):
        # Relation with YARN created, we're operating in yarn-cluster mode
        self._required_relations = {'plugin'}
        super(SparkSE, self).add_relation(relid, remote, provides)
