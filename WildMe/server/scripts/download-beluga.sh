#!/usr/bin/env bash
# Downloads the LILA Beluga ID 2022 dataset (Wild Me, CDLA-Permissive 1.0) into $1.
set -euo pipefail
dest=${1:-/opt/wildme/datasets/beluga-2022}
base=https://storage.googleapis.com/public-datasets-lila/wild-me
mkdir -p "$dest" && cd "$dest"
curl -sSfL -O "$base/beluga.coco.tar.gz" -O "$base/beluga-id-test.zip"
tar xzf beluga.coco.tar.gz 2>/dev/null
python3 -c "import zipfile; zipfile.ZipFile('beluga-id-test.zip').extractall('test')"
find . -name '._*' -delete
rm beluga.coco.tar.gz beluga-id-test.zip
