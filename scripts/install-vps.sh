#!/usr/bin/env bash
set -euo pipefail
[[ $EUID -eq 0 ]] || { echo 'Gunakan: sudo bash scripts/install-vps.sh' >&2; exit 1; }
proxy=auto
caddy_config=/etc/caddy/Caddyfile
for argument in "$@"; do
    case "$argument" in
        --proxy=auto|--proxy=caddy|--proxy=nginx) proxy=${argument#*=} ;;
        --caddy-config=*) caddy_config=${argument#*=} ;;
        *) echo 'Gunakan: sudo bash scripts/install-vps.sh [--proxy=auto|caddy|nginx] [--caddy-config=/path/Caddyfile]' >&2; exit 1 ;;
    esac
done
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$root"
[[ "$root" != *' '* ]] || { echo 'Gunakan path tanpa spasi, misalnya /srv/Media-keycloud.' >&2; exit 1; }
[[ ! -e .deploy/prod.env && ! -e .deploy/dev.env ]] || { echo 'Instalasi sudah diinisialisasi. Lanjutkan dengan scripts/start.sh atau panduan pemulihan, bukan membuat kunci baru.' >&2; exit 1; }
command -v apt-get >/dev/null || { echo 'Installer ditujukan untuk Ubuntu 24.04. Gunakan instalasi manual untuk distro lain.' >&2; exit 1; }
command -v ss >/dev/null || { echo 'Pasang iproute2 agar port layanan dapat diperiksa.' >&2; exit 1; }
if [[ "$proxy" == auto ]]; then
    if systemctl is-active --quiet caddy; then proxy=caddy; else proxy=nginx; fi
fi
internal_listeners=$(ss -H -ltnp '( sport = :8081 or sport = :8082 )')
if [[ -n "$internal_listeners" ]]; then
    echo 'Port 8081/8082 sudah dipakai. Ubah port dalam scripts/init-env.py dan scripts/configure-web.sh terlebih dahulu.' >&2; exit 1
fi
if [[ "$proxy" == nginx ]] && command -v nginx >/dev/null && nginx -T 2>/dev/null | grep -E 'server_name .*media(-dev)?\.keycloud\.id' >/dev/null; then
    echo 'Domain media sudah memiliki konfigurasi Nginx. Integrasikan melalui panduan manual agar tidak menimpa situs.' >&2; exit 1
fi
web_listeners=$(ss -H -ltnp '( sport = :80 or sport = :443 )')
if [[ -n "$web_listeners" ]] && printf '%s\n' "$web_listeners" | grep -v "\"$proxy\"" >/dev/null; then
    printf 'Port web dikelola layanan selain %s. Ikuti docs/VPS.md untuk proxy yang ada.\n%s\n' "$proxy" "$web_listeners" >&2; exit 1
fi
if [[ "$proxy" == caddy ]]; then
    command -v caddy >/dev/null || { echo 'Binary Caddy tidak ditemukan.' >&2; exit 1; }
    command -v python3 >/dev/null || { echo 'Pasang python3 terlebih dahulu.' >&2; exit 1; }
    python3 scripts/configure-caddy.py --config "$caddy_config" --check
fi
apt-get update
apt-get install -y git tmux python3 curl
if [[ "$proxy" == nginx ]]; then
    apt-get install -y nginx apache2-utils certbot python3-certbot-nginx
fi
if ! command -v docker >/dev/null; then apt-get install -y docker.io docker-compose-v2; fi
if ! docker compose version >/dev/null 2>&1; then
    if dpkg-query -W -f='${Status}' docker.io 2>/dev/null | grep -q 'install ok installed'; then
        apt-get install -y docker-compose-v2
    else
        echo 'Pasang plugin Compose v2 dari sumber instalasi Docker yang digunakan.' >&2; exit 1
    fi
fi
docker compose version
systemctl enable --now docker
if [[ "$proxy" == nginx ]]; then systemctl enable --now nginx; fi
bash scripts/test.sh
image="mahad-media:$(git -c safe.directory="$root" rev-parse --short=12 HEAD 2>/dev/null || date +%Y%m%d%H%M%S)"
docker build --target production -t "$image" .
MEDIA_IMAGE="$image" python3 scripts/init-env.py
bash scripts/start.sh dev
bash scripts/compose.sh dev exec -T -u www-data app php artisan db:seed --class=DemoSeeder --force
bash scripts/start.sh prod
printf '%s\n' "$image" > .deploy/tested-image
if [[ "$proxy" == caddy ]]; then
    python3 scripts/configure-caddy.py --config "$caddy_config"
else
    bash scripts/configure-web.sh
fi
read -r -p 'Email admin media pertama: ' admin_email
bash scripts/compose.sh prod exec -u www-data app php artisan media:admin "$admin_email" --name='Admin Ma’had Aly'
bash scripts/compose.sh dev exec -u www-data app php artisan media:admin "$admin_email" --name='Admin Development'
printf '\n%s\n' 'Aplikasi terpasang: https://media.keycloud.id dan https://media-dev.keycloud.id. Login: /masuk. Periksa DNS dan status HTTPS pada proxy.'
