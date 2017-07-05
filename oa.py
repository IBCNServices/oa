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

import pykka
import yaml

from hadoop import HadoopOA
from spark import SparkOA
from helpers import merge_dicts


class Operator(pykka.ThreadingActor):
    def __init__(self):
        super(Operator, self).__init__()
        hadoop_oa = HadoopOA.start(name='hadoop-cluster').proxy()
        hadoop_oa.update_model({
            'num_workers': 3,
        })
        hadoop_oa.subscribe(self.actor_ref.proxy())

        spark_oa = SparkOA.start(name='spark').proxy()
        spark_oa.update_model({
            'num_workers': 4,
        })
        spark_oa.subscribe(self.actor_ref.proxy())
        self._children = {
            'hadoop-cluster': {
                'agent': hadoop_oa,
                'previous-state': {},
            },
            'spark': {
                'agent': spark_oa,
                'previous-state': {},
            },
        }
        t_uuid = uuid.uuid4()
        self._children['spark']['agent'].add_relation(
            t_uuid,
            self._children['hadoop-cluster']['agent'],
            True)
        self._children['hadoop-cluster']['agent'].add_relation(
            t_uuid,
            self._children['spark']['agent'],
            False)

    def notify_new_state(self, actor_ref):
        state = actor_ref.view_state().get()
        name = state['name']
        print("changed for: " + name)
        if state == self._children[name]['previous-state']:
            return
        print("New State: {}".format(state))
        self._children[name]['previous-state'] = state
        if self._all_children_ready():
            print("REQUESTING OPERATOR TO STOP")
            self.actor_ref.stop(block=False)

    def _all_children_ready(self):
        for name, child in self._children.items():
            if not child['previous-state'].get('ready', False):
                return False
            req_rels = child['agent'].view_requested_relations().get()
            cur_rels = len(child['previous-state'].get('relations', []))
            print("{} has {} requested relation, {} actual relations".format(
                name, req_rels, cur_rels))
            if req_rels != cur_rels:
                return False
        return True

    def on_stop(self):
        c_mod = {}
        print("stopping all children")
        for child in [c['agent'] for c in self._children.values()]:
            merge_dicts(child.concrete_model().get(), c_mod)
            child.stop()
        print(
            "\nCONCRETE MODEL:"
            "\n-----------"
            "\n{}"
            "-----------"
            "\n".format(yaml.dump(c_mod, default_flow_style=False)))


operator = Operator.start()
print("started operator")
