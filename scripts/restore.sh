#!/usr/bin/env bash
set -euo pipefail
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
environment=${1:?Pilih prod atau dev}
backup=$(realpath -- "${2:?Pilih direktori backup}")
case "$environment" in prod|dev) ;; *) exit 1;; esac
[[ "$(cat "$backup/environment")" == "$environment" ]] || { echo 'Backup bukan untuk environment ini.' >&2; exit 1; }
for file in database.dump uploads.tar.gz runtime.env; do [[ -s "$backup/$file" ]] || exit 1; done
python3 - "$root/.deploy/$environment.env" "$backup/runtime.env" <<'PY'
import sys
from pathlib import Path
def env(p): return dict(line.split('=',1) for line in Path(p).read_text().splitlines() if '=' in line)
a,b=map(env,sys.argv[1:])
for key in ['APP_URL','DB_DATABASE','DB_USERNAME','DB_PASSWORD','ENV_FILE']:
 if a[key]!=b[key]: raise SystemExit('Konfigurasi database/lokasi backup berbeda. Gunakan panduan pemulihan VPS baru.')
PY
dc() { bash "$root/scripts/compose.sh" "$environment" "$@"; }
dc stop scheduler app
dc exec -T db sh -c 'pg_restore --clean --if-exists --no-owner --exit-on-error -U "$POSTGRES_USER" -d "$POSTGRES_DB"' < "$backup/database.dump"
dc run --rm --no-deps -T --entrypoint tar app -xzf - -C /var/www/html/storage < "$backup/uploads.tar.gz"
cp "$root/.deploy/$environment.env" "$root/.deploy/$environment.env.before-restore"
cp "$backup/runtime.env" "$root/.deploy/$environment.env"
dc up -d --wait app scheduler
printf '%s\n' 'Database, unggahan, kunci aplikasi, dan image dipulihkan. Uji login serta artikel publik.'
