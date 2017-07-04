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
from collections import defaultdict

import pykka

from ModelManager import ModelManager
from helpers import merge_dicts


class JujuOA(ModelManager):
    def __init__(self):
        super(JujuOA, self).__init__(oe=JujuSE)


class JujuSE(pykka.ThreadingActor):
    def __init__(self, modelmanager):
        super(JujuSE, self).__init__()
        self._modelmanager = modelmanager
        self._name = None
        self._charm = None
        self._num_units = None
        self._relations = defaultdict(lambda: {
            'data': {},
            'state': 'unconnected',
        })

    def _push_new_state(self):
        rels = {}
        for relid, rel in self._relations.items():
            rels[relid] = rel['state']
        self._modelmanager.update_state({
            'name': self._name,
            'charm': self._charm,
            'num_units': self._num_units,
            'relations': rels,
        })
        print("STATE PUSHED")

    def _relation_data_changed(self, relid):
        print('relation_data_changed called')
        relation = self._relations[relid]
        if not relation.get('remote'):
            print('relation not initiated')
            return
        if relation['data'].get('relation-initiated'):
            # logger.debug('relation connected')
            relation['state'] = 'connected'
            self._push_new_state()

    #
    # Public API
    #
    def update_model(self, new_model):
        if new_model.get('name'):
            self._name = new_model.get('name')
        if new_model.get('charm'):
            self._charm = new_model.get('charm')
        if new_model.get('num_units'):
            self._num_units = new_model.get('num_units')

    def concrete_model(self):
        print("I'm {}".format(self._name))
        c_model = {
            'services': {
                self._name: {
                    'charm': self._charm,
                    'num_units': self._num_units,
                }
            },
            'relations': [

            ]
        }
        for rel in self._relations.values():
            # if rel['state'] == 'connected':
            #     print("CONNECTED!")
            # if rel['provides']:
            #     print("PROVIDES!")
            if (rel['state'] == 'connected' and rel['provides']):
                print("BOTH!")

                c_model['relations'].append([
                    self._name,
                    rel['data']['remote-name']
                ])
                print(c_model['relations'])
        return c_model

    def add_relation(self, relid, remote, provides):
        print("add_relation called")
        relation = self._relations[relid]
        relation['remote'] = remote
        relation['provides'] = provides
        remote.relation_set(relid, {
            'relation-initiated': True,
            'remote-name': self._name
        })
        self._relation_data_changed(relid)

    def relation_set(self, relid, data):
        print("relation_set called")
        relation = self._relations[relid]
        merge_dicts(data, relation['data'])
        self._relation_data_changed(relid)

    def on_failure(self, exception_type, exception_value, traceback):
        print("FAILED! {} {} {}".format(exception_type, exception_value, traceback))
        self.on_stop()
