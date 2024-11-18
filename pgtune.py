#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import string
import getopt
import sys
from math import floor, log, ceil
from distutils.version import LooseVersion
import multiprocessing

B = 1
K = 1024
M = K * K
G = K * M

DATA_SIZES = {'b': B, 'k': K, 'm': M, 'g': G}
SIZE_SUFFIX = ["", "KB", "MB", "GB", "TB"]

DEFAULT_PG_VERSION = '12'

def get_size(s):
    last_symbol = s[-1:].lower()
    if last_symbol in string.digits:
        return int(s)

    if last_symbol not in DATA_SIZES:
        raise Exception('Invalid format: %s' % s)

    return int(s[:-1]) * DATA_SIZES[last_symbol]


def available_memory():
    meminfo = {}
    with open('/proc/meminfo') as f:
        for line in f:
            s = line.split(': ')
            meminfo[s[0]] = s[1].split()[0].strip()

    return int(meminfo['MemTotal'])*1024

def beautify(n):
    if type(n) is int and n > 1024:
        return to_size_string(n)
    return str(n)


def to_size_string(n):
    f = int(floor(log(n, 1024)))
    return "%d%s" % (int(n/1024**f), SIZE_SUFFIX[f])


def to_bytes(n, max_size=None):
    v = int(floor(n))
    if max_size is not None:
        return min(max_size, v)
    return v

def calculate(total_mem, max_connections, pg_version):
    pg_conf = {}
    pg_conf['max_connections'] = max_connections
    pg_conf['shared_buffers'] = to_bytes(total_mem/4)
    pg_conf['effective_cache_size'] = to_bytes(total_mem * 3/4)
    pg_conf['work_mem'] = to_bytes((total_mem - pg_conf['shared_buffers']) / (max_connections * 3))
    pg_conf['maintenance_work_mem'] = to_bytes(total_mem/16, 2*G)  # max 2GB
    if LooseVersion(pg_version) < LooseVersion('9.5'):
        pg_conf['checkpoint_segments'] = 64
    else:
      # http://www.postgresql.org/docs/current/static/release-9-5.html
      # max_wal_size = (3 * checkpoint_segments) * 16MB
      pg_conf['min_wal_size'] = '2GB'
      pg_conf['max_wal_size'] = '4GB'
    pg_conf['checkpoint_completion_target'] = 0.9
    pg_conf['wal_buffers'] = to_bytes(pg_conf['shared_buffers']*0.03, 16*M)  # 3% of shared_buffers, max of 16MB.
    pg_conf['default_statistics_target'] = 100
    pg_conf['synchronous_commit'] = 'off'
    pg_conf['vacuum_cost_delay'] = 50
    pg_conf['wal_writer_delay'] = '10s'
    if LooseVersion(pg_version) >= LooseVersion('10'):
        workers = multiprocessing.cpu_count()
        pg_conf['max_worker_processes'] = workers
        pg_conf['max_parallel_workers'] = workers
        pg_conf['max_parallel_workers_per_gather'] = int(ceil(workers/2.))

    return pg_conf


def usage_and_exit():
    print("Usage: %s [-m <size>] [-c <conn>] [-r master|stand-by] [-s] [-S] [-l <listen_addresses>] [-v <version>] [-h]")
    print("")
    print("where:")
    print("  -c <conn> : max number of concurrent client connections, default 100")
    print("  -h        : print this help message")
    print("  -l <addr> : address(es) on which the server is to listen for incoming connections, default localhost")
    print("  -m <size> : max memory to use, default total available memory")
    print("  -r <mode> : configure streaming replication mode: `master` or `stand-by`")
    print("  -s        : database located on SSD disks (or fully fit's into memory)")
    print("  -S        : enable tracking of SQL statement execution (require pg >= 9.0)")
    print("  -v <vers> : PostgreSQL version number. Default: %s" % DEFAULT_PG_VERSION)

    sys.exit(1)


def main():
    mem = None
    max_connections = 100
    have_ssd = False
    enable_stat = False
    listen_addresses = 'localhost'
    pg_version = None
    replication = None

    try:
        opts, args = getopt.getopt(sys.argv[1:], 'c:hl:m:r:sSv:')

        for o, a in opts:
            if o == '-m':
                mem = get_size(a)
            elif o == '-c':
                max_connections = int(a)
            elif o == '-s':
                have_ssd = True
            elif o == '-S':
                enable_stat = True
            elif o == '-l':
                listen_addresses = a
            elif o == '-v':
                pg_version = a
            elif o == '-r':
                if a not in ['master', 'stand-by']:
                    print('invalid replication mode: %s' % a)
                    usage_and_exit()
                replication = a
            elif o == '-h':
                usage_and_exit()
            else:
                print('invalid option: %s' % o)
                usage_and_exit()
    except getopt.GetoptError as err:
        print(err)
        usage_and_exit()

    if mem is None:
        mem = available_memory()

    if pg_version is None:
        pg_version = DEFAULT_PG_VERSION

    print("#")
    print("# dCache's chimera friendly configuration fot PostgreSQL %s" % pg_version)
    print("#")
    print("# Config for %s memory and %d connections" % (to_size_string(mem), max_connections))
    print("#")
    pg_conf = calculate(mem, max_connections, pg_version)
    for s in sorted(pg_conf.keys()):
        print("%s = %s" % (s, beautify(pg_conf[s])))
    if have_ssd:
        print("random_page_cost = 1.5")

    if replication == 'master':
        print("#")
        print("# replica configuration stub for master")
        print("#")
        print("# See: https://wiki.postgresql.org/wiki/Streaming_Replication")
        print("#")
        print("archive_mode = on")
        print("archive_command = '/bin/true'")
        print("archive_timeout = 0")
        print("max_wal_senders = 2")
        print("wal_keep_segments = 32")
        print("wal_level = hot_standby")
    elif replication == 'stand-by':
        print("#")
        print("# replica configuration stub for hot stand-by")
        print("#")
        print("# See: https://wiki.postgresql.org/wiki/Streaming_Replication")
        print("#")
        print("hot_standby = on")

    print("#")
    print("# other goodies")
    print("#")
    print("log_line_prefix = '%m <%d %u %a %r> %%'")
    print("log_temp_files = 0")
    print("log_min_duration_statement = 20")
    print("log_checkpoints = on")
    print("log_lock_waits = on")
    print("bytea_output = 'escape'")
    print("listen_addresses = '%s'" % (listen_addresses))
    if enable_stat:
        print("shared_preload_libraries = 'pg_stat_statements'")
        print("pg_stat_statements.track = top")


if __name__ == '__main__':
    main()
