# Wildbook server

Wildbook (pinned in `../Wildbook`) running with Docker Compose on `65.108.33.121`.

| Service    | Image                                   | Exposure              |
|------------|-----------------------------------------|-----------------------|
| wildbook   | `tomcat:9.0.113-jre17-temurin-jammy`    | public, port 80       |
| db         | `pgvector/pgvector:pg13`                | 127.0.0.1:5433        |
| opensearch | `opensearchproject/opensearch:3.1.0`    | 127.0.0.1:9200        |

The Tomcat image is stock: the unpacked WAR, data dir and logs are bind-mounted
from `/opt/wildme/deploy`. Postgres and OpenSearch data are in named Docker volumes.

## Layout on the server

```
/opt/macawid           checkout of this repo (with submodules)
  WildMe/server/.env   secrets, git-ignored (copy of .env.example)
/opt/wildme/deploy     webapps/wildbook (app), webapps/wildbook_data_dir (media), logs/
/opt/wildme/datasets   beluga-2022 (see below)
```

`./wb` wraps `docker compose` with the upstream compose file from the submodule,
`docker-compose.override.yml` and `.env`: `./wb ps`, `./wb logs -f wildbook`, `./wb up -d`.

## Fresh install

```sh
# on your machine: build the WAR from the pinned submodule (JDK 17, Maven 3, Node 22)
cd WildMe/Wildbook && mvn clean install -DskipTests

# on the server
git clone --recurse-submodules https://github.com/EcoDex-DAO/MacawID.git /opt/macawid
mkdir -p /opt/wildme/deploy/webapps /opt/wildme/deploy/logs
cd /opt/macawid/WildMe/server
cp .env.example .env   # then set real passwords
./wb up -d

# back on your machine
WildMe/server/scripts/deploy-war.sh WildMe/Wildbook/target/wildbook-*.war
```

Wildbook creates an admin `tomcat` / `tomcat123` on first start. Change it straight away:
the server has no firewall.

## Updating

Config changes: `git pull` in `/opt/macawid`, then `./wb up -d`.
New app build: rebuild the WAR and run `scripts/deploy-war.sh`.

## Beluga ID 2022 dataset

`scripts/download-beluga.sh` fetches the [LILA Beluga ID 2022](https://lila.science/datasets/beluga-id-2022/)
dataset (Wild Me, CDLA-Permissive 1.0): 5,902 training images of 788 whales in COCO format,
plus a 3,401-image test split. It is not committed here (~700 MB) and not yet imported into Wildbook.
