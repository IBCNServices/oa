#!/usr/bin/env python3
#
# Copyright © 2017 Ghent University and imec.
# License is described in `LICENSE` file.
#
import logging

from ModelManager import ModelManager
from helpers import OrchestrationEngine, split

logger = logging.getLogger('oa')


class RecursiveOA(ModelManager):
    def __init__(self, **kwargs):
        super(RecursiveOA, self).__init__(oe=RecursiveOE, kwargs=kwargs)


class RecursiveOE(OrchestrationEngine):
    def __init__(self, modelmanager, name=None):
        super(RecursiveOE, self).__init__(modelmanager)
        self._name = name
        # Null vars for linter
        self._numchildren = 0
        self._req_treesize = 0
        self._children = {}

    def _push_new_state(self):
        self._modelmanager.update_state(self._return_new_state())

    def _return_new_state(self):
        ready = True
        treesize = 1
        treedepth = 0
        for (name, childref) in self._children.items():
            childstate = childref.view_state().get()
            logger.debug("child {}: {}".format(name, childstate))
            if (not childstate) or (not childstate['ready']):
                ready = False
            treesize += childstate.get('treesize', 1)
            if childstate.get('treedepth', 0) > treedepth:
                treedepth = childstate['treedepth']
        treedepth = treedepth + 1
        return {
            'name': self._name,
            'treesize': treesize,
            'ready': ready,
            'treedepth': treedepth,
        }

    def update_model(self, new_model):
        if new_model.get('numchildren') and new_model.get('treesize'):
            self._numchildren = new_model.get('numchildren')
            self._req_treesize = new_model.get('treesize')
            self._process_change()

    def _process_change(self):
        chunks = split(self._req_treesize-1, self._numchildren)

        if len(self._children) >= len(chunks):
            self._push_new_state()
            return

        logger.info(
            "oa {}:"
            "\n\treq: {}"
            "\n\tchildr: {}"
            "\n\tchunks: {}".format(self._name, self._req_treesize, len(self._children), chunks)
        )

        for idx, chunk in enumerate(chunks):
            c_name = "{}-{}".format(self._name, idx)
            childref = RecursiveOA.start(
                name=c_name,
            ).proxy()
            self._children[c_name] = childref
            childref.subscribe(self.actor_ref.proxy())
            childref.update_model({
                'numchildren': self._numchildren,
                'treesize': chunk,
            })

        self._push_new_state()
