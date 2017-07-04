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
import pykka

from HadoopOA import HadoopOA


class Operator(pykka.ThreadingActor):
    def __init__(self):
        super(Operator, self).__init__()
        hadoop_oa = HadoopOA.start().proxy()

        hadoop_oa.update_model({
            'num_workers': 3,
        })

        hadoop_oa.subscribe(self.actor_ref.proxy())
        self.children = [hadoop_oa]

    def notify_new_state(self, actor_ref):
        print("new_state")
        if actor_ref.view_state().get()['ready']:
            self.actor_ref.stop(block=False)

    def on_stop(self):
        print("stopping all children")
        for child in self.children:
            print("Concrete model: {}".format(child.concrete_model().get()))
            child.stop()


operator = Operator.start()
print("started operator")
