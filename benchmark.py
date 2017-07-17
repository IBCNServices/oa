#!/usr/bin/env python3
import time
import json
import subprocess

import yaml

start_time = time.time()

print("STARTED: {}".format(start_time))


def check_all_ready(applications):
    for _, app_state in applications.items():
        for un_name, un_state in app_state.get('units', {}).items():
            if ("ready" in un_state['workload-status']['message']
                    and "active" in un_state['workload-status']['current']
                    and "idle" in un_state['juju-status']['current']
                    and "waiting" not in un_state['workload-status']['message']):
                # unit is ready
                pass
            else:
                # unit is NOT ready
                print("{} is not ready: {}".format(
                    un_name,
                    un_state['workload-status']['message']))
                return False
    print(yaml.dump(applications))
    return True


ready = False

while not ready:
    time.sleep(10)
    status = json.loads(subprocess.check_output(
        ['juju', 'status', '--format', 'json'], universal_newlines=True))
    ready = check_all_ready(status['applications'])

finish_time = time.time()
elapsed_time = finish_time - start_time
print(
    '########################################'
    '\nReady!'
    '\nStarted at: {}'
    '\nFinished at: {}'
    '\nElapsed time: {}'
    ''.format(
        start_time,
        finish_time,
        elapsed_time))
