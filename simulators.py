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

from ModelManager import ModelManager
from helpers import OrchestrationEngine

logger = logging.getLogger('oa')


class RecursiveOA(ModelManager):
    def __init__(self, **kwargs):
        super(RecursiveOA, self).__init__(oe=RecursiveOE, kwargs=kwargs)


class RecursiveOE(OrchestrationEngine):
    def __init__(self, modelmanager, name=None, level=None):
        super(RecursiveOE, self).__init__(modelmanager)
        if not all([name, modelmanager]):
            logger.error("params wrong for {}".format(name))
        if level is None:
            logger.error("params wrong for {}: level is none".format(name))

        self._name = name
        self._numchildren = 0
        self._level = level

        self._children = {}

    def _push_new_state(self):
        self._modelmanager.update_state(self._return_new_state())

    def _return_new_state(self):
        ready = True
        treesize = 1
        for (name, childref) in self._children.items():
            childstate = childref.view_state().get()
            logger.debug("child {}: {}".format(name, childstate))
            if (not childstate) or (not childstate['ready']):
                ready = False
            treesize += childstate.get('treesize', 0)
        return {
            'name': self._name,
            'treesize': treesize,
            'ready': ready,
        }

    def update_model(self, new_model):
        if new_model.get('numchildren'):
            self._numchildren = new_model.get('numchildren')
            self._process_change()

    def _process_change(self):
        if self._level < 1:
            self._push_new_state()
            return
        for c_num in range(len(self._children), self._numchildren):
            c_name = "{}-{}".format(self._name, c_num)
            self._children[c_name] = RecursiveOA.start(
                name=c_name,
                level=self._level-1,
            ).proxy()
        for childref in self._children.values():
            childref.subscribe(self.actor_ref.proxy())
            childref.update_model({
                'numchildren': self._numchildren,
            })

        self._push_new_state()
