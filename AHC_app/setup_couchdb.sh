#!/bin/sh -xe

cat >/opt/couchdb/etc/local.ini <<EOF
[couchdb]
single_node=true

[admins]
${COUCHDB_USER} = ${COUCHDB_PASSWORD}
EOF

nohup bash -c "/docker-entrypoint.sh /opt/couchdb/bin/couchdb &"
sleep 15

curl -X PUT http://127.0.0.1:5984/_users
curl -X PUT http://127.0.0.1:5984/_replicator