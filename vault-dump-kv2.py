#!/usr/bin/env python

from __future__ import print_function
import datetime
import os
import sys

import hvac
import base64

# Source: https://hvac.readthedocs.io/en/stable/usage/secrets_engines/kv_v2.html
client = hvac.Client(url=os.environ['VAULT_ADDR'], token=os.environ['VAULT_TOKEN'], verify=False)
#print(client.is_authenticated())


def is_secret_latest_version_deleted(path, mountpoint):
    metadata = client.secrets.kv.v2.read_secret_metadata(path, mount_point=mountpoint)['data']
    deletion_time = metadata['versions'][str(metadata['current_version'])]['deletion_time']
    return deletion_time != ''


def print_secret(path, mountpoint):
    # ignore secrets that are marked as deleted (but not destroyed), don't bother backing up old versions
    if is_secret_latest_version_deleted(path, mountpoint):
        return

    content = client.secrets.kv.v2.read_secret_version(path, mount_point=mountpoint)['data']['data']

    print("vault kv put {}{}".format(vault_dump_mountpoint, path), end='')
    if content:
        for key in sorted(content.keys()):
            value = str(content[key])
            #print("key, value", key, value)
            #try:
            #  value = base64.b64encode(value.encode("utf-8"))
            #except AttributeError:
            #  value = value
            print(" {0}=\"{1}\"".format(key, value.replace('"', '\\"')), end='')
    else:
        # print a "" to indicate to Vault CLI that we'd like to put an empty secret
        print(" \"\"", end='')
    print()


def recurse_secrets(path_prefix, mountpoint):
    sys.stderr.write("Recursing into path prefix \"{0}\"\n".format(path_prefix))
    keys = client.secrets.kv.v2.list_secrets(path_prefix, mount_point=mountpoint)['data']['keys']
    for key in keys:
        item_path = path_prefix + key
        if key.endswith('/'):
            recurse_secrets(item_path, mountpoint)
        else:
            print_secret(item_path, mountpoint)


vault_dump_mountpoint = os.environ.get('VAULT_DUMP_MOUNTPOINT', '/secret/')
vault_dump_path_prefix = os.environ.get('VAULT_DUMP_PATH_PREFIX', '')

print('#')
print('# vault-dump-kv2.py backup')
print("# backup date: {} UTC".format(datetime.datetime.utcnow()))
print("# VAULT_DUMP_MOUNTPOINT setting: {}".format(vault_dump_mountpoint))
print("# VAULT_DUMP_PATH_PREFIX setting: {}".format(vault_dump_path_prefix))
print('# STDIN encoding: {}'.format(sys.stdin.encoding))
print('# STDOUT encoding: {}'.format(sys.stdout.encoding))
print('#')
print('# WARNING: not guaranteed to be consistent!')
print('#')

recurse_secrets(vault_dump_path_prefix, vault_dump_mountpoint)
