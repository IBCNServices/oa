#!/usr/bin/env python3
#
# Copyright © 2017 Ghent University and imec.
# License is described in `LICENSE` file.
#
import uuid
import logging
from collections import defaultdict

import pykka


class SanePykkaFilter(logging.Filter):
    def filter(self, record):
        msg = record.msg
        if msg.startswith("Exception"):
            record.level = logging.ERROR
            return True
        return False


logging.basicConfig(level=logging.WARNING)
logging.getLogger('pykka').level = logging.DEBUG
logging.getLogger('pykka').addFilter(SanePykkaFilter())

logger = logging.getLogger('oa')


def split(number, parts):
    base = int(number/parts)
    rest = number % parts
    result = [base] * parts
    for i in range(0, rest):
        result[i] = result[i] + 1
    return [x for x in result if x]


def merge_dicts(source, destination):
    for key, value in source.items():
        if isinstance(value, dict):
            # get node or create one
            node = destination.setdefault(key, {})
            merge_dicts(value, node)
        elif isinstance(value, list):
            destination.setdefault(key, []).extend(value)
        else:
            destination[key] = value
    return destination


def needs_merge(source, destination):
    for key, value in source.items():
        if isinstance(value, dict):
            # get node or create one
            node = destination.setdefault(key, {})
            needs_merge(value, node)
        else:
            if destination.get(key) != value:
                logger.debug(
                    "SOURCE: {}\n"
                    "DESTINATION: {}\n"
                    "NEEDS MERGE BECAUSE {} != {}".format(
                        source, destination, destination.get(key), value))
                return True
    return False


def add_relation(provides, requires):
    t_uuid = uuid.uuid4()
    provides.add_relation(t_uuid, requires, True)
    requires.add_relation(t_uuid, provides, False)


class RelationEngine(pykka.ThreadingActor):
    def __init__(self, modelmanager):
        super(RelationEngine, self).__init__()
        self._modelmanager = modelmanager
        self._relations = defaultdict(lambda: {
            'data': {},
            'state': 'unconnected',
        })
        self._name = None

    def add_relation(self, relid, remote, provides):
        logger.debug("add_relation called")
        relation = self._relations[relid]
        relation['agent'] = remote
        relation['provides'] = provides
        remote.relation_set(relid, {
            'relation-initiated': True,
            'remote-name': self._name
        })
        self._relation_data_changed(relid)

    def relation_set(self, relid, data):
        logger.debug("relation_set called")
        relation = self._relations[relid]
        merge_dicts(data, relation['data'])
        self._relation_data_changed(relid)

    def _relation_data_changed(self, relid):
        logger.debug('relation_data_changed called')
        relation = self._relations[relid]
        if not relation.get('agent'):
            logger.debug('relation not initiated')
            return
        if relation['data'].get('relation-initiated'):
            # logger.debug('relation connected')
            relation['state'] = 'connected'
            self._process_change()
            self._push_new_state()

    def _push_new_state(self):
        pass

    def _process_change(self):
        pass

    def _get_relation_states(self):
        rels = {}
        for relid, rel in self._relations.items():
            rels[relid] = rel['state']
        return rels


class OrchestrationEngine(RelationEngine):
    def __init__(self, modelmanager):
        super(OrchestrationEngine, self).__init__(modelmanager)
        self._children = {}

    def on_stop(self):
        for proxy in self._children.values():
            proxy.stop()

    def concrete_model(self):
        c_mod = {}
        logger.debug('I have {} children'.format(len(self._children)))
        for se in self._children.values():
            c_mod = merge_dicts(se.concrete_model().get(), c_mod)
        return c_mod

    def full_model(self):
        # f_mod = self._modelmanager.view_state().get()
        f_mod = self._return_new_state()
        f_mod['children'] = {}
        for se in self._children.values():
            c_mod = se.full_model().get()
            f_mod['children'][c_mod['name']] = c_mod
        return f_mod

    def notify_new_state(self, actor_ref):
        self._push_new_state()

    def on_failure(self, exception_type, exception_value, traceback):
        logger.error("FAILED! {} {} {}".format(exception_type, exception_value, traceback))
        self.on_stop()
