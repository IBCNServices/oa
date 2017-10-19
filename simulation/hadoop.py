#!/usr/bin/env python3
#
# Copyright © 2017 Ghent University and imec.
# License is described in `LICENSE` file.
#
import logging

from juju import JujuRelationSE
from ModelManager import ModelManager
from helpers import merge_dicts, OrchestrationEngine, add_relation

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


class HadoopPluginSA(ModelManager):
    def __init__(self, **kwargs):
        super(HadoopPluginSA, self).__init__(oe=HadoopPluginSE, kwargs=kwargs)


class HadoopOE(OrchestrationEngine):
    def __init__(self, modelmanager, name=None):
        super(HadoopOE, self).__init__(modelmanager)
        if not all([name]):
            logger.error("params wrong")

        self._name = name
        self._num_workers = 1

        self._children = {
            'namenode': HadoopNamenodeSA.start(
                name='namenode', charm='hadoop-namenode').proxy(),
            'resourcemanager': HadoopResourcemanagerSA.start(
                name='resourcemanager', charm='hadoop-resourcemanager').proxy(),
            'worker': HadoopWorkerSA.start(
                name='worker', charm='hadoop-slave').proxy(),
        }
        self._children['namenode'].update_model({
            'num-units': 1
        })
        self._children['resourcemanager'].update_model({
            'num-units': 1
        })
        self._children['worker'].update_model({
            'num-units': 1
        })

        for childref in self._children.values():
            childref.subscribe(self.actor_ref.proxy())

        add_relation(self._children['namenode'],
                     self._children['worker'])
        add_relation(self._children['namenode'],
                     self._children['resourcemanager'])
        add_relation(self._children['resourcemanager'],
                     self._children['worker'])

        self._push_new_state()

    def _push_new_state(self):
        #print("pushing new state for " + self._name)
        self._modelmanager.update_state(self._return_new_state())

    def _return_new_state(self):
        # childnotready = ""
        ready = True
        num_workers = 0
        for (name, childref) in self._children.items():
            childstate = childref.view_state().get()
            logger.debug("child: {}".format(childstate))
            if childstate and childstate['ready']:
                #print("child is ready")
                if name == "worker":
                    num_workers = childstate['num-units']
            else:
                #print("child is not")
                ready = False
                # childnotready = name
        # push the updated state also to your relationships
        for relid, relation in self._relations.items():
            if relation['data'].get('num-workers') is not None:
                relation['agent'].relation_set(
                    relid,
                    {'num-workers': num_workers})
            if relation['data'].get('type', '') == 'hadoop-client':
                self._ensure_plugin_present()
                relation['agent'].relation_set(
                    relid,
                    {'plugin-agent': self._children['plugin']})
        return {
            'name': self._name,
            'num-workers': num_workers,
            'ready': ready,
            'relations': self._get_relation_states(),
            # 'childnotready': childnotready,
        }


    def _ensure_plugin_present(self):
        if not self._children.get('plugin'):
            self._children['plugin'] = HadoopPluginSA.start(
                name='plugin', charm='hadoop-plugin').proxy()
            self._children['plugin'].subscribe(self.actor_ref.proxy())
            add_relation(self._children['namenode'],
                         self._children['plugin'])
            add_relation(self._children['resourcemanager'],
                         self._children['plugin'])

    def update_model(self, new_model):
        if new_model.get('num-workers'):
            self._num_workers = new_model.get('num-workers')
            self._process_change()

    def _process_change(self):
        num_workers_list = [self._num_workers]
        num_workers_list.extend([
            r['data'].get('num-workers', 0) for r in self._relations.values()
        ])
        self._children['worker'].update_model({
            'num-units': max(num_workers_list),
        })


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
