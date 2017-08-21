#!/usr/bin/env python3
#
# Copyright © 2017 Ghent University and imec.
# License is described in `LICENSE` file.
#
from collections import defaultdict
import logging


from ModelManager import ModelManager
from helpers import RelationEngine

logger = logging.getLogger('oa')


class JujuSA(ModelManager):
    def __init__(self, **kwargs):
        super(JujuSA, self).__init__(oe=JujuSE, kwargs=kwargs)


class JujuSE(RelationEngine):
    def __init__(self, modelmanager, name=None, charm=None):
        super(JujuSE, self).__init__(modelmanager)
        if not all([name, charm]):
            logger.error("params wrong")
        self._name = name
        self._charm = charm
        self._num_units = None
        self._relations = defaultdict(lambda: {
            'data': {},
            'state': 'unconnected',
        })
        self._config = {}

    def _push_new_state(self):
        self._modelmanager.update_state({
            'name': self._name,
            'charm': self._charm,
            'num-units': self._num_units,
            'relations': self._get_relation_states(),
            'ready': self._is_ready(),
        })

    def _is_ready(self):
        return self._name and self._charm and self._num_units

    #
    # Public API
    #
    def update_model(self, new_model):
        if 'num-units' in new_model:
            self._num_units = new_model.get('num-units')
        if 'config' in new_model:
            self._config = new_model['config']
        self._push_new_state()

    def concrete_model(self):
        logger.debug("Generating concrete model for {}".format(self._name))
        c_model = {
            'services': {
                self._name: {
                    'charm': self._charm,
                }
            },
            'relations': [

            ]
        }
        if self._num_units is not None:
            # if num_units is None, the charm is a subordinate charm that doesn't
            # specify number of units.
            c_model['services'][self._name]['num_units'] = self._num_units
        if self._config:
            # if we have config, add it.
            c_model['services'][self._name]['options'] = self._config
        for rel in self._relations.values():
            if (rel['state'] == 'connected' and rel['provides']):
                c_model['relations'].append([
                    self._name,
                    rel['data']['remote-name']
                ])
                logger.debug(c_model['relations'])
        return c_model

    def on_failure(self, exception_type, exception_value, traceback):
        logger.debug("FAILED! {} {} {}".format(exception_type, exception_value, traceback))
        self.on_stop()


class JujuRelationSE(JujuSE):
    def __init__(self, modelmanager, **kwargs):
        super(JujuRelationSE, self).__init__(modelmanager, **kwargs)
        self._required_relations = set()

    def _is_ready(self):
        present_relations = {
            r['data'].get('remote-name', '')
            for r in self._relations.values()}
        logger.debug("Present relations: {}".format(present_relations))
        return (super(JujuRelationSE, self)._is_ready
                and self._required_relations.issubset(present_relations))
