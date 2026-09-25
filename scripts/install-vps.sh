#!/usr/bin/env bash
set -euo pipefail
[[ $EUID -eq 0 ]] || { echo 'Gunakan: sudo bash scripts/install-vps.sh' >&2; exit 1; }
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$root"
[[ "$root" != *' '* ]] || { echo 'Gunakan path tanpa spasi, misalnya /srv/Media-keycloud.' >&2; exit 1; }
[[ ! -e .deploy/prod.env && ! -e .deploy/dev.env ]] || { echo 'Instalasi sudah diinisialisasi. Lanjutkan dengan scripts/start.sh atau panduan pemulihan, bukan membuat kunci baru.' >&2; exit 1; }
command -v apt-get >/dev/null || { echo 'Installer ditujukan untuk Ubuntu 24.04. Gunakan instalasi manual untuk distro lain.' >&2; exit 1; }
if command -v ss >/dev/null && ss -ltnp '( sport = :8081 or sport = :8082 )' | tail -n +2 | grep -q .; then
    echo 'Port 8081/8082 sudah dipakai. Ubah port dalam scripts/init-env.py dan scripts/configure-web.sh terlebih dahulu.' >&2; exit 1
fi
if command -v nginx >/dev/null && nginx -T 2>/dev/null | grep -E 'server_name .*media(-dev)?\.keycloud\.id' >/dev/null; then
    echo 'Domain media sudah memiliki konfigurasi Nginx. Integrasikan melalui panduan manual agar tidak menimpa situs.' >&2; exit 1
fi
if command -v ss >/dev/null && ss -ltnp '( sport = :80 or sport = :443 )' | tail -n +2 | grep -v nginx | grep -q .; then
    echo 'Port web dikelola selain Nginx. Ikuti docs/VPS.md untuk proxy yang ada.' >&2; exit 1
fi
apt-get update
apt-get install -y nginx apache2-utils certbot python3-certbot-nginx git tmux python3 curl
if ! command -v docker >/dev/null; then apt-get install -y docker.io docker-compose-v2; fi
docker compose version >/dev/null || { echo 'Pasang plugin Docker Compose v2 terlebih dahulu.' >&2; exit 1; }
systemctl enable --now docker nginx
bash scripts/test.sh
image="mahad-media:$(git -c safe.directory="$root" rev-parse --short=12 HEAD 2>/dev/null || date +%Y%m%d%H%M%S)"
docker build --target production -t "$image" .
MEDIA_IMAGE="$image" python3 scripts/init-env.py
bash scripts/start.sh dev
bash scripts/compose.sh dev exec -T -u www-data app php artisan db:seed --class=DemoSeeder --force
bash scripts/start.sh prod
printf '%s\n' "$image" > .deploy/tested-image
bash scripts/configure-web.sh
read -r -p 'Email admin media pertama: ' admin_email
bash scripts/compose.sh prod exec -u www-data app php artisan media:admin "$admin_email" --name='Admin Ma’had Aly'
bash scripts/compose.sh dev exec -u www-data app php artisan media:admin "$admin_email" --name='Admin Development'
printf '\n%s\n' 'Selesai: https://media.keycloud.id dan https://media-dev.keycloud.id. Login: /masuk.'
