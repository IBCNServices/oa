#!/usr/bin/env python3
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


class RelationEngine(pykka.ThreadingActor):
    def __init__(self):
        super(RelationEngine, self).__init__()
        self._relations = defaultdict(lambda: {
            'data': {},
            'state': 'unconnected',
        })
        self._name = None

    def add_relation(self, relid, remote, provides):
        logger.debug("add_relation called")
        relation = self._relations[relid]
        relation['remote'] = remote
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
        if not relation.get('remote'):
            print('relation not initiated')
            return
        if relation['data'].get('relation-initiated'):
            # logger.debug('relation connected')
            relation['state'] = 'connected'
            self._push_new_state()

    def _push_new_state(self):
        pass

    def _get_child_states(self):
        rels = {}
        for relid, rel in self._relations.items():
            rels[relid] = rel['state']
        return rels
