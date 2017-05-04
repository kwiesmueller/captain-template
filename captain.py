#!/usr/bin/env python3

try:
    import configparser
except:
    import ConfigParser as configparser
import json
import os
import subprocess as sp
import sys
import yaml


def execute(cmd, verbose=False):
    if verbose:
        print(cmd)
    process = sp.Popen(cmd, stdout=sp.PIPE)
    return process.wait()


def switch_k8s_context(context):
    print("* switching kubernetes context to: {}".format(context))
    exitcode = execute(["kubectl", "config", "use-context", context])
    if exitcode != 0:
        sys.exit(exitcode)


def apply_manifests(path):
    print("* apply: kubernetes manifests")
    execute(["kubectl", "apply", "-f", path])


def get_chart(release_filename):
    charts_dir = config.get('helm', 'local_charts_dir')

    stream = open(release_filename, 'r')
    release_data = yaml.load(stream)
    chart = release_data.get('chart', None)

    c = chart.split('/')
    if(len(c) == 2 and c[0] == 'local'):
        chart="{}/{}".format(charts_dir, c[1])

    return chart


def release_namespace(releases_dir):
    releases = {}

    for path, _, files in os.walk(releases_dir):
        if files:
            dirs = path.split('/')
            if len(dirs) == 2 and dirs[0] == releases_dir:
                namespace = dirs[1]
                for name in files:
                    if name.endswith('.yaml'):
                        release = name.split('.yaml')[0]
                        releases[release] = namespace
    return releases


def secret_set_parameter(namespace, release):
    with open('secrets.json') as json_secrets:
        secrets = json.load(json_secrets)

    set_string = ""
    for (key, val) in secrets.get(namespace, {}).get(release, {}).items():
        set_string += "{}={},".format(key, val)

    return set_string[:-1]


def kubernetes_tasks():
    k8s_context = config.get('kubernetes', 'context')
    manifests_dir = config.get('kubernetes', 'manifests_dir')

    switch_k8s_context(k8s_context)
    apply_manifests(manifests_dir)


def helm_tasks(specific_releases = []):
    releases_dir = config.get('helm', 'releases_dir')
    releases = release_namespace(releases_dir)

    for release, namespace in releases.items():
        if specific_releases and release not in specific_releases:
            continue
        
        release_file = "{}/{}/{}.yaml".format(releases_dir, namespace, release)

        chart = get_chart(release_file)
        if not chart:
            print("! no chart set in: {}".format(release_file))
            continue
        
        print("* helm apply: name={}, namespace={}, chart={}".format(release, namespace, chart))
        execute(
            [
                "helm", "upgrade", "-i", release, chart, 
                "--namespace", namespace, 
                "--set", secret_set_parameter(namespace, release), 
                "-f", release_file
            ], 
            verbose=False
        )


def main():
    kubernetes_tasks()
    helm_tasks(sys.argv[1:])


if __name__ == '__main__':
    config = configparser.ConfigParser()
    config.read('captain.cfg')

    main()
