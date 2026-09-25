#!/usr/bin/env bash
set -euo pipefail
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$root"
[[ -z "$(git -c safe.directory="$root" status --porcelain)" ]] || { echo 'Commit perubahan terlebih dahulu agar rilis dapat dilacak.' >&2; exit 1; }
image="mahad-media:$(git -c safe.directory="$root" rev-parse --short=12 HEAD)"
bash scripts/test.sh
docker build --target production -t "$image" .
bash scripts/backup.sh dev
python3 scripts/set-image.py dev "$image"
bash scripts/start.sh dev
printf '%s\n' "$image" > .deploy/tested-image
printf '%s\n' 'Rilis development selesai. Uji di media-dev.keycloud.id sebelum promosi.'
