#!/usr/bin/env bash
set -euo pipefail
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$root"
image=${1:?Gunakan: bash scripts/promote.sh mahad-media:COMMIT_SHA}
[[ -f .deploy/tested-image && "$(cat .deploy/tested-image)" == "$image" ]] || { echo 'Image belum melewati scripts/release-dev.sh.' >&2; exit 1; }
[[ "$(sed -n 's/^APP_IMAGE=//p' .deploy/dev.env)" == "$image" ]] || { echo 'Image berbeda dari development saat ini.' >&2; exit 1; }
container=$(bash scripts/compose.sh dev ps -q app)
[[ "$(docker inspect --format '{{.State.Health.Status}}' "$container")" == healthy ]] || { echo 'Development tidak sehat.' >&2; exit 1; }
bash scripts/backup.sh prod
python3 scripts/set-image.py prod "$image"
bash scripts/start.sh prod
printf '%s\n' 'Production memakai image yang sama dengan development.'
