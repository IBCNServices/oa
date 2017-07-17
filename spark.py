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

from juju import JujuRelationSE
from ModelManager import ModelManager
from helpers import merge_dicts, OrchestrationEngine, add_relation

logger = logging.getLogger('oa')


class SparkOA(ModelManager):
    def __init__(self, **kwargs):
        super(SparkOA, self).__init__(oe=SparkOE, kwargs=kwargs)


class SparkSA(ModelManager):
    def __init__(self, **kwargs):
        super(SparkSA, self).__init__(oe=SparkSE, kwargs=kwargs)


class SparkOE(OrchestrationEngine):
    def __init__(self, modelmanager, name=None):
        if not all([name]):
            logger.error("params wrong")
        super(SparkOE, self).__init__()
        self._modelmanager = modelmanager

        self._name = name
        self._num_workers = 1

        self._children = {
            'spark': SparkSA.start(name='spark', charm='spark').proxy(),
        }
        self._children['spark'].update_model({
            'num-units': 4,
        })
        self._children['spark'].subscribe(self.actor_ref.proxy())
        self._push_new_state()

    def _push_new_state(self):
        child_state = self._children['spark'].view_state().get()
        logger.debug("state: {}".format(child_state))
        # if we are running in yarn mode (if we have relation) then child must
        # run in yarn mode too, otherwise, we're not ready.
        ready = False
        if len(self._relations) == 0:
            ready = child_state.get('ready', False)
        elif len(self._relations) <= len(child_state.get('relations', [])):
            _, rel = self._hadoop_relation()
            ready = (
                child_state.get('ready', False)
                and rel['data'].get('num-workers', 0) >= self._num_workers
            )
        else:
            ready = False
        self._modelmanager.update_state({
            'name': self._name,
            'num-workers': child_state.get('num-units', 0),
            'ready': ready,
            'relations': self._get_relation_states(),
        })

    def _hadoop_relation(self):
        return next(iter([
            (rid, r)
            for (rid, r) in self._relations.items()
            if "hadoop" in r['data'].get('remote-name', '')
        ]), (None, None))

    def _process_change(self):
        # See if we're connected to an Hadoop OA
        relid, relation = self._hadoop_relation()
        if not relation:
            self._children['spark'].update_model({
                'num-units': self._num_workers,
                'config': {}
            })
            return
        # Yes we are! Update the spark charm
        self._children['spark'].update_model({
            'num-units': 1,
            'config': {
                'spark_execution_mode': "yarn-client"
            }
        })
        # tell the OA what we want
        relation['agent'].relation_set(
            relid,
            {
                'num-workers': self._num_workers,
                'type': 'hadoop-client',
            })
        # Create relation between spark and the plugin if we received it.
        spark_agent = self._children['spark']
        plugin_agent = relation['data'].get('plugin-agent')
        if plugin_agent and (spark_agent.num_req_relations().get() < 1):
            add_relation(spark_agent, plugin_agent)

    def update_model(self, new_model):
        if new_model.get('num-workers'):
            self._num_workers = new_model.get('num-workers')
            self._process_change()


class SparkSE(JujuRelationSE):
    def add_relation(self, relid, remote, provides):
        # Relation with YARN created, we're operating in yarn-cluster mode
        self._required_relations = {'plugin'}
        super(SparkSE, self).add_relation(relid, remote, provides)
