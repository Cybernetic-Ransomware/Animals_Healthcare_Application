#!/bin/sh -xe

# Non-secret config only -- credentials come from the base image's own entrypoint at runtime; DB creation lives in the couchdb_init step.
cat >/opt/couchdb/etc/local.ini <<EOF
[couchdb]
single_node=true

[chttpd]
port = 5982
bind_address = 0.0.0.0

[httpd]
port = 5982
bind_address = 0.0.0.0

[log]
level = info

[metrics]
rate = 1.0

EOF
