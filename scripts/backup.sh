#!/usr/bin/env bash
set -euo pipefail
umask 077
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
environment=${1:?Pilih prod atau dev}
dc() { bash "$root/scripts/compose.sh" "$environment" "$@"; }
backup="$root/.deploy/backups/$environment-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$backup"
dc stop scheduler app
resume() { dc up -d app scheduler >/dev/null; }
trap resume EXIT
dc exec -T db sh -c 'pg_dump -Fc -U "$POSTGRES_USER" "$POSTGRES_DB"' > "$backup/database.dump"
dc run --rm --no-deps --entrypoint tar app -czf - -C /var/www/html/storage app > "$backup/uploads.tar.gz"
cp "$root/.deploy/$environment.env" "$backup/runtime.env"
printf '%s\n' "$environment" > "$backup/environment"
chmod -R go-rwx "$backup"
printf '%s\n' "Backup selesai: $backup"
