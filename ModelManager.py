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
from collections import defaultdict

import pykka

from helpers import merge_dicts, needs_merge

logger = logging.getLogger('oa')


class ModelManager(pykka.ThreadingActor):
    def __init__(self, oe=None, kwargs=None):
        super(ModelManager, self).__init__()
        if not kwargs:
            kwargs = {}
        self._oe = oe.start(self.actor_ref.proxy(), **kwargs).proxy()
        self._requested_model = {}
        self._num_requested_relations = 0
        self._state = {}
        self._subscribers = []
        self._relations_data = defaultdict(dict)

    def on_failure(self, exception_type, exception_value, traceback):
        logger.error("FAILED! {} {} {}".format(exception_type, exception_value, traceback))
        self.on_stop()

    def on_stop(self):
        self._oe.stop()

    #
    # Public API
    #
    def view_state(self):
        return self._state

    def update_state(self, new_state):
        # Don't notify if state hasn't really changed
        if self._state == new_state:
            return
        logger.debug("{} != {}".format(self._state, new_state))
        self._state = new_state
        for subscriber in self._subscribers:
            subscriber.notify_new_state(self.actor_ref.proxy())

    def update_model(self, new_model):
        self._requested_model = new_model
        self._oe.update_model(new_model)

    def num_req_relations(self):
        return self._num_requested_relations

    def subscribe(self, actor_ref):
        self._subscribers.append(actor_ref)
        # immediately notify subscriber if we already have a state.
        if self._state:
            actor_ref.notify_new_state(self.actor_ref.proxy())

    def unsubscribe(self, actor_ref):
        self._subscribers.remove(actor_ref)

    def concrete_model(self):
        return self._oe.concrete_model().get()

    def full_model(self):
        return self._oe.full_model().get()

    def add_relation(self, *args, **kwargs):
        self._num_requested_relations = self._num_requested_relations + 1
        self._oe.add_relation(*args, **kwargs)

    def relation_set(self, relid, data):
        if needs_merge(data, self._relations_data[relid]):
            merge_dicts(data, self._relations_data[relid])
            self._oe.relation_set(relid, self._relations_data[relid])
