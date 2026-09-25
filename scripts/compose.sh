#!/usr/bin/env bash
set -euo pipefail
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
environment=${1:?Gunakan: bash scripts/compose.sh prod|dev <perintah compose>}
shift
case "$environment" in prod|dev) ;; *) echo 'Environment harus prod atau dev.' >&2; exit 1;; esac
config="$root/.deploy/$environment.env"
[[ -f "$config" ]] || { echo 'Jalankan installer terlebih dahulu.' >&2; exit 1; }
exec docker compose --project-name "mahad-$environment" --env-file "$config" -f "$root/compose.yaml" "$@"
