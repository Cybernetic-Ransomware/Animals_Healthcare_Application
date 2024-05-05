#!/bin/sh -xe

cat >/opt/couchdb/etc/local.ini <<EOF
[couchdb]
single_node=true

[admins]
${COUCHDB_USER} = ${COUCHDB_PASSWORD}

[chttpd]
port = 5982
bind_address = 0.0.0.0

[httpd]
port = 5982
bind_address = 0.0.0.0

EOF

nohup bash -c "/docker-entrypoint.sh /opt/couchdb/bin/couchdb &"
sleep 15

#curl -X PUT http://127.0.0.1:5982/_users
#curl -X PUT http://127.0.0.1:5982/_replicator
#curl -X PUT http://127.0.0.1:5982/appendixes

response=$(curl -s -o /dev/null -w "%{http_code}" -X GET http://127.0.0.1:5982/_users)
if [ "$response" -ne "200" ]; then
    curl -X PUT http://127.0.0.1:5982/_users
    echo "Database _users was configured properly"
fi

response=$(curl -s -o /dev/null -w "%{http_code}" -X GET http://127.0.0.1:5982/_replicator)
if [ "$response" -ne "200" ]; then
    curl -X PUT http://127.0.0.1:5982/_replicator
    echo "Database _replicator was configured properly"
fi

response=$(curl -s -o /dev/null -w "%{http_code}" -X GET http://127.0.0.1:5982/appendixes)
if [ "$response" -ne "200" ]; then
    curl -X PUT http://127.0.0.1:5982/appendixes
    echo "Database appendixes was configured properly"
fi