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

from JujuOA import JujuOA
from ModelManager import ModelManager
from helpers import merge_dicts


class HadoopOA(ModelManager):
    def __init__(self):
        super(HadoopOA, self).__init__(oe=HadoopOE)


class HadoopOE(pykka.ThreadingActor):
    def __init__(self):
        super(HadoopOE, self).__init__()

        self.name = 'hadoop-cluster'
        self.num_workers = 1

        self.children = {
            'namenode': JujuOA.start().proxy(),
            'resourcemanager': JujuOA.start().proxy(),
            'worker': JujuOA.start().proxy(),
        }
        self.children['namenode'].update_model({
            'name': 'namenode',
            'charm': 'hadoop-namenode',
            'num_units': 1
        })
        self.children['resourcemanager'].update_model({
            'name': 'resourcemanager',
            'charm': 'hadoop-resourcemanager',
            'num_units': 1
        })
        self.children['worker'].update_model({
            'name': 'worker',
            'charm': 'hadoop-worker',
            'num_units': 1
        })

        t_uuid = uuid.uuid4()
        self.children['namenode'].add_relation(
            t_uuid,
            self.children['worker'],
            True)
        self.children['worker'].add_relation(
            t_uuid,
            self.children['namenode'],
            False)

        t_uuid = uuid.uuid4()
        self.children['resourcemanager'].add_relation(
            t_uuid,
            self.children['worker'],
            True)
        self.children['worker'].add_relation(
            t_uuid,
            self.children['resourcemanager'],
            False)

        t_uuid = uuid.uuid4()
        self.children['namenode'].add_relation(
            t_uuid,
            self.children['resourcemanager'],
            True)
        self.children['resourcemanager'].add_relation(
            t_uuid,
            self.children['namenode'],
            False)
        print('INIT has been called')

    def on_stop(self):
        for proxy in self.children.values():
            proxy.stop()

    def update_model(self, new_model):
        if new_model.get('name'):
            self.name = new_model.get('name')
        if new_model.get('num_workers'):
            self.num_workers = new_model.get('num_workers')
            self.children['worker'].update_model({
                'name': 'worker',
                'charm': 'hadoop-worker',
                'num_units': new_model.get('num_workers'),
            })

    def concrete_model(self):
        c_mod = {}
        print('I have {} children'.format(len(self.children)))
        for se in self.children.values():
            c_mod = merge_dicts(se.concrete_model().get(), c_mod)
        return c_mod

    def on_failure(self, exception_type, exception_value, traceback):
        print("FAILED! {} {} {}".format(exception_type, exception_value, traceback))
        self.on_stop()
