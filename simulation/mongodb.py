#!/usr/bin/env python3
#
# Copyright © 2017 Ghent University and imec.
# License is described in `LICENSE` file.
#
import logging

from juju import JujuRelationSE
from ModelManager import ModelManager

logger = logging.getLogger('oa')


class MongoDBSA(ModelManager):
    def __init__(self, **kwargs):
        super(MongoDBSA, self).__init__(oe=MongoDBSE, kwargs=kwargs)


class MongoDBSE(JujuRelationSE):
    pass
