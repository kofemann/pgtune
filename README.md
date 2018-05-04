pgtune
======

A tool to optimize PostgreSQL for dCache namespace or any other *on line transaction processing*
(OLTP) workloads.

Based on information from [Tuning Your PostgreSQL Server][3] wiki page.

Usage:
------
```
$ ./pgtune.py >> /var/lib/pgsql/9.x/data/postgresql.conf
```

Example output:
--------------
```
$ ./pgtune.py
#
# dCache's chimera friendly configuration
#
# Config for 7GB memory and 100 connections
#
checkpoint_completion_target = 0.9
checkpoint_segments = 64
default_statistics_target = 100
effective_cache_size = 5GB
maintenance_work_mem = 496MB
max_connections = 100
shared_buffers = 1GB
synchronous_commit = off
vacuum_cost_delay = 50
wal_buffers = 16MB
wal_writer_delay = 10s
work_mem = 19MB
#
# other goodies
#
log_line_prefix = '%m <%d %u %r> %%'
log_temp_files = 0
log_min_duration_statement = 20
log_checkpoints = on
log_lock_waits = on
listen_addresses = 'localhost'
```

Streaming replication
---------------------
The **pgtune** script creates a configuration stubs for streaming master-slave
replication, however you still have to create corresponding **recovery.conf** on
the slave nodes as well as adjust **archive_command**.

See [PostgreSQL wiki][1] on streaming replication configuration.

OS Configuration
----------------
For optimal DB performance an optimal hardware and OS configuration required.
On RHEL7 based system it's ideal to use **tuned** profile.

Copy **tuned.conf** file into **/etc/tuned/postgres-db-server/tuned.conf** and select the
profile:

```
$ yum install tuned
$ wget -O /etc/tuned/postgres-db-server/tuned.conf \
   https://raw.githubusercontent.com/kofemann/pgtune/master/tuned.conf
$ tuned-adm profile postgres-db-server
```

**IMPORTANT**: don't forget to do benchmarks defore and after.

LICENSE
-------
This work is published under [public domain][2] license.

[1]: https://wiki.postgresql.org/wiki/Streaming_Replication
[2]: https://creativecommons.org/licenses/publicdomain/
[3]: https://wiki.postgresql.org/wiki/Tuning_Your_PostgreSQL_Server
