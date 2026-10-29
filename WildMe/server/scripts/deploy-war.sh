#!/usr/bin/env bash
# Usage: deploy-war.sh <path/to/wildbook-*.war> [ssh-host]
# Copies a built WAR to the server, unpacks it into the Tomcat webapp and restarts Wildbook.
set -euo pipefail
war=$1
host=${2:-root@65.108.33.121}
rsync -az "$war" "$host:/opt/wildme/wildbook.war"
ssh "$host" 'set -e
rm -rf /opt/wildme/deploy/webapps/wildbook
mkdir -p /opt/wildme/deploy/webapps/wildbook
python3 -c "import zipfile; zipfile.ZipFile(\"/opt/wildme/wildbook.war\").extractall(\"/opt/wildme/deploy/webapps/wildbook\")"
/opt/macawid/WildMe/server/wb restart wildbook'
