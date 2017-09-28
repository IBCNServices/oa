#!/usr/bin/env python3
#
# Copyright © 2017 Ghent University and imec.
# License is described in `LICENSE` file.
#
import logging
import datetime
import time
import math
import sys

import pykka
import yaml

from hadoop import HadoopOA
from spark import SparkOA
from mongodb import MongoDBSA
from helpers import merge_dicts, add_relation
from simulators import RecursiveOA

logger = logging.getLogger('oa')
# sys.setrecursionlimit(15000)


class Operator(pykka.ThreadingActor):
    def __init__(self, response):
        super(Operator, self).__init__()
        self._children = {}
        self.start_time = time.time()
        self.response = response

    def notify_new_state(self, actor_ref):
        state = actor_ref.view_state().get()
        name = state['name']
        logger.debug("changed for: " + name)
        if state == self._children[name]['previous-state']:
            return
        logger.debug("New State: {}".format(state))
        self._children[name]['previous-state'] = state
        if self._all_children_ready():
            logger.debug("REQUESTING OPERATOR TO STOP")
            self.actor_ref.stop(block=False)

    def _all_children_ready(self):
        for name, child in self._children.items():
            if not child['previous-state'].get('ready', False):
                return False
            req_rels = child['agent'].num_req_relations().get()
            cur_rels = len(child['previous-state'].get('relations', []))
            logger.debug("{} has {} requested relation, {} actual relations".format(
                         name, req_rels, cur_rels))
            if req_rels != cur_rels:
                return False
        return True

    def on_stop(self):
        c_mod = {}
        a_state = [c['previous-state'] for c in self._children.values()]
        full_model = []
        logger.debug("stopping all children")
        for child in [c['agent'] for c in self._children.values()]:
            merge_dicts(child.concrete_model().get(), c_mod)
            full_model.append(child.full_model().get())
            child.stop()
        elapsed_time = time.time() - self.start_time
        self.response['elapsed_time'] = elapsed_time
        self.response['treedepth'] = a_state[0].get('treedepth', 0)
        logger.debug("ELAPSED TIME: {}".format(elapsed_time))
        logger.debug(
            "\nCONCRETE MODEL:"
            "\n-----------"
            "\n{}"
            "-----------"
            "\n".format(yaml.dump(c_mod, default_flow_style=False)))
        logger.debug(
            "\nABSTRACT STATE:"
            "\n-----------"
            "\n{}"
            "-----------"
            "\n".format(yaml.dump(a_state, default_flow_style=False)))
        logger.debug(
            "\nFULL MODEL:"
            "\n-----------"
            "\n{}"
            "-----------"
            "\n".format(yaml.dump(full_model, default_flow_style=False)))


class HadoopOperator(Operator):
    def __init__(self, response, numworkers):
        super(HadoopOperator, self).__init__(response)

        hadoop_oa = HadoopOA.start(name='hadoop-cluster').proxy()
        hadoop_oa.update_model({
            'num-workers': math.ceil(0.1 + numworkers - numworkers/2),
        })
        hadoop_oa.subscribe(self.actor_ref.proxy())

        spark_oa = SparkOA.start(name='spark').proxy()
        spark_oa.update_model({
            'num-workers': numworkers,
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
        add_relation(self._children['spark']['agent'],
                     self._children['hadoop-cluster']['agent'])


class LimeDSOperator(Operator):
    def __init__(self):
        super(LimeDSOperator, self).__init__()
        mongodb_sa = MongoDBSA.start(name='mongodb').proxy()
        mongodb_sa.subscribe(self.actor_ref.proxy())
        self._children = {
            'mongodb': {
                'agent': mongodb_sa,
                'previous-state': {},
            },
        }


class RecursiveOperator(Operator):
    def __init__(self, resp, numchildren, req_treesize):
        super(RecursiveOperator, self).__init__(resp)
        recursive_oa = RecursiveOA.start(
            name='r').proxy()
        recursive_oa.subscribe(self.actor_ref.proxy())
        self._children = {
            'r': {
                'agent': recursive_oa,
                'previous-state': {},
            },
        }
        recursive_oa.update_model({
            'numchildren': numchildren,
            'treesize': req_treesize,
        })


def benchmark_numworkers():
    print("workers\telapsed_time")
    for _ in range(0, 9):
        for numw in range(5, 101, 5):
            resp = {}
            HadoopOperator.start(resp, numw)
            while(not resp.get('elapsed_time')):
                time.sleep(0.02)
            print("{}\t{}".format(numw, resp['elapsed_time']))


def benchmark_numclusters():
    # Benchmark the speed of orchestrating multiple spark-on-yarn clusters
#    # for numoa in range(5, 101, 5):
    for numoa in range(5, 101, 5):
        for _ in range(0, 10):

            start_time = time.time()
            responses = []
            for _ in range(0, numoa):
                resp = {}
                HadoopOperator.start(resp, 1)
                responses.append(resp)

            while(responses):
                responses[:] = [x for x in responses if not x]
                time.sleep(0.02)

            finish_time = time.time()
            el_time = finish_time - start_time
            print("{}\t{}".format(numoa, el_time))


def benchmark_numchildren_list():
    # Benchmark the usage of concurrency potential
    resp = {}

    print("childrn\tagents\tdepth\telapsed_time")
    for numchildren in range(1, 3, 1):
        treedepth = 0
        for numagents in range(10, 251, 10):
            for _ in range(0, 5):
                resp = {}
                RecursiveOperator.start(resp, numchildren, numagents)
                while(resp.get('elapsed_time') is None):
                    time.sleep(0.02)
                elapsed_time = resp['elapsed_time']
                while(resp.get('treedepth') is None):
                    time.sleep(0.02)
                treedepth = resp['treedepth']
                print("{}\t{}\t{}\t{}".format(
                    numchildren, numagents,
                    treedepth, seconds=elapsed_time))


benchmark_numworkers()
# benchmark_numclusters()
# benchmark_numchildren_list()
