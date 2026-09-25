#!/usr/bin/env bash
set -euo pipefail
[[ $EUID -eq 0 ]] || { echo 'Jalankan dengan sudo.' >&2; exit 1; }
config=/etc/nginx/sites-available/mahad-media
if [[ ! -e "$config" ]]; then
    if ss -ltnp '( sport = :80 or sport = :443 )' | tail -n +2 | grep -v nginx | grep -q .; then
        echo 'Port 80/443 digunakan layanan selain Nginx. Sesuaikan reverse proxy yang ada; lihat docs/VPS.md.' >&2
        exit 1
    fi
    mkdir -p /etc/nginx/sites-available /etc/nginx/sites-enabled
    htpasswd -c /etc/nginx/.htpasswd-mahad-dev reviewer
    chmod 640 /etc/nginx/.htpasswd-mahad-dev
    chown root:www-data /etc/nginx/.htpasswd-mahad-dev
    cat > "$config" <<'NGINX'
# Managed initial configuration for Ma'had Aly Media. Other sites are untouched.
server {
    listen 80;
    server_name media.keycloud.id;
    client_max_body_size 8m;
    location / {
        proxy_pass http://127.0.0.1:8081;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-For $remote_addr;
        proxy_read_timeout 90;
    }
}
server {
    listen 80;
    server_name media-dev.keycloud.id;
    client_max_body_size 8m;
    add_header X-Robots-Tag "noindex, nofollow" always;
    auth_basic "Development Ma'had Aly";
    auth_basic_user_file /etc/nginx/.htpasswd-mahad-dev;
    location / {
        proxy_pass http://127.0.0.1:8082;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-For $remote_addr;
        proxy_read_timeout 90;
    }
}
NGINX
    ln -s "$config" /etc/nginx/sites-enabled/mahad-media
fi
nginx -t
systemctl reload nginx
read -r -p 'Email untuk sertifikat HTTPS: ' tls_email
certbot --nginx -d media.keycloud.id -d media-dev.keycloud.id --email "$tls_email" --agree-tos --non-interactive --redirect
printf '%s\n' 'HTTPS siap. Akun Basic Auth development: reviewer (password yang Anda masukkan).'
