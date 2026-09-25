#!/usr/bin/env bash
set -euo pipefail
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
environment=${1:?Pilih prod atau dev}
dc() { bash "$root/scripts/compose.sh" "$environment" "$@"; }
dc up -d --wait db
dc stop scheduler app
dc run --rm --no-deps app sh -c 'su -s /bin/sh www-data -c "php artisan migrate --force && php artisan db:seed --force"'
dc up -d --wait app scheduler
printf '%s\n' "Environment $environment aktif."
