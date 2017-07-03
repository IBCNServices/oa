#!/usr/bin/env python3
import logging


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
