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


class ModelManager(pykka.ThreadingActor):
    def __init__(self, oe=None):
        super(ModelManager, self).__init__()
        self.count = 0
        self.oe = oe.start(self.actor_ref.proxy()).proxy()
        self.requested_model = {}
        self.state = {}
        self.subscribers = []

    def on_failure(self, exception_type, exception_value, traceback):
        print("FAILED! {} {} {}".format(exception_type, exception_value, traceback))
        self.on_stop()

    def on_stop(self):
        self.oe.stop()

    #
    # Public API
    #
    def view_state(self):
        return self.state

    def update_state(self, new_state):
        self.state = new_state
        for subscriber in self.subscribers:
            subscriber.notify_new_state(self.actor_ref.proxy())

    def update_model(self, new_model):
        self.requested_model = new_model
        self.oe.update_model(new_model)

    def subscribe(self, actor_ref):
        self.subscribers.append(actor_ref)

    def unsubscribe(self, actor_ref):
        self.subscribers.remove(actor_ref)

    def concrete_model(self):
        return self.oe.concrete_model().get()

    def add_relation(self, *args, **kwargs):
        self.oe.add_relation(*args, **kwargs)

    def relation_set(self, *args, **kwargs):
        self.oe.relation_set(*args, **kwargs)
