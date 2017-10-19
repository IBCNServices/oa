#!/usr/bin/env python3
#
# Copyright © 2017 Ghent University and imec.
# License is described in `LICENSE` file.
#
import time
import json
import subprocess

import yaml


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


def time_until_ready():
    start_time = time.time()
    print("STARTED: {}".format(start_time))
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
    return elapsed_time


def wait_until_empty():
    while True:
        time.sleep(10)
        status = json.loads(subprocess.check_output(
            ['juju', 'status', '--format', 'json'], universal_newlines=True))
        if (not status['applications']) and (not status['machines']):
            break


def remove_applications():
    status = json.loads(subprocess.check_output(
        ['juju', 'status', '--format', 'json'], universal_newlines=True))
    applications = status['applications']
    for app_name in applications:
        subprocess.check_call(['juju', 'remove-application', app_name])


def benchmark_deploy(num_workers):
    with open('bundle.yaml') as f:
        bundle = yaml.load(f)
    bundle['services']['worker']['num_units'] = num_workers
    with open("bundle.yaml", "w") as f:
        yaml.dump(bundle, f)
    subprocess.check_call(['juju', 'deploy', './bundle.yaml'])
    t = time_until_ready()
    with open('benchmark.log', 'a') as f:
        f.write("{}\t{}\n".format(num_workers, t))
    remove_applications()
    wait_until_empty()

# Run a series of tests
for numw in range(5, 101, 5):
    benchmark_deploy(numw)

# Run a single test
wait_until_empty()
benchmark_deploy(70)
