#!/usr/bin/env python

from __future__ import print_function
import string
import getopt
import sys
from math import floor, log

B = 1
K = 1024
M = K * K
G = K * M

DATA_SIZES = {'b': B, 'k': K, 'm': M, 'g': G}
SIZE_SUFFIX = ["", "KB", "MB", "GB", "TB"]


def get_size(s):
    last_symbol = s[-1:].lower()
    if last_symbol in string.digits:
        return long(s)

    if not DATA_SIZES.has_key(last_symbol):
        raise Exception('Invalid format: %s' % s)

    return long(s[:-1]) * DATA_SIZES[last_symbol]


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

def calculate(total_mem, max_connections):
    pg_conf = {}
    pg_conf['max_connections'] = max_connections
    pg_conf['shared_buffers'] = to_bytes(total_mem/4, 8*G)  # max 8GB
    pg_conf['effective_cache_size'] = to_bytes(total_mem * 3/4)
    pg_conf['work_mem'] = to_bytes((total_mem - pg_conf['shared_buffers']) / (max_connections * 3))
    pg_conf['maintenance_work_mem'] = to_bytes(total_mem/16, 2*G)  # max 2GB
    pg_conf['checkpoint_segments'] = 64
    pg_conf['checkpoint_completion_target'] = 0.9
    pg_conf['wal_buffers'] = to_bytes(pg_conf['shared_buffers']*0.03, 16*M)  # 3% of shared_buffers, max of 16MB.
    pg_conf['default_statistics_target'] = 100
    pg_conf['synchronous_commit'] = 'off'
    pg_conf['vacuum_cost_delay'] = 50
    pg_conf['wal_writer_delay'] = '10s'
    return pg_conf


def usage_and_exit():
    print("Usage: %s [-m <size>] [-c <conn>] [-s] [-S] [-l <listen_addresses>] [-h]")
    print("")
    print("where:")
    print("  -m <size> : max memory to use, default total available memory")
    print("  -c <conn> : max inumber of concurent client connections, default 100")
    print("  -s        : database located on SSD disks (or fully fit's into memory)")
    print("  -S        : enable tracking of SQL statement execution (require pg >= 9.0)")
    print("  -l <addr> : address(es) on which the server is to listen for incomming connections, default localhost")
    print("  -h        : print this help message")
    sys.exit(1)


def main():
    mem = None
    max_connections = 100
    have_ssd = False
    enable_stat = False
    listen_addresses = 'localhost'

    try:
        opts, args = getopt.getopt(sys.argv[1:], 'l:m:c:sSh')

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

    print("#")
    print("# dCache's chimera friendly configuration")
    print("#")
    print("# Config for %s memory and %d connections" % (to_size_string(mem), max_connections))
    print("#")
    pg_conf = calculate(mem, max_connections)
    for s in sorted(pg_conf.keys()):
        print("%s = %s" % (s, beautify(pg_conf[s])))
    if have_ssd:
        print("random_page_cost = 1.5")

    print("#")
    print("# other goodies")
    print("#")
    print("log_line_prefix = '%m <%d %u %r> %%'")
    print("log_temp_files = 0")
    print("log_min_duration_statement = 20")
    print("log_checkpoints = on")
    print("log_lock_waits = on")
    print("listen_addresses = '%s'" % (listen_addresses))
    if enable_stat:
        print("shared_preload_libraries = 'pg_stat_statements'")
    

if __name__ == '__main__':
    main()

