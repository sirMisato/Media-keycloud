# VPS dengan Caddy dan Hermes yang sudah berjalan

Gunakan installer mode Caddy pada Ubuntu 24.04. Docker/Compose dipasang jika belum tersedia; Caddy tetap menangani domain, sedangkan aplikasi berjalan di `127.0.0.1:8081` dan `127.0.0.1:8082`. Konfigurasi dan layanan Hermes tidak diubah.

## Melanjutkan dari installer lama

Jika installer lama berhenti dengan pesan **Port web dikelola selain Nginx**, belum ada database atau konfigurasi aplikasi yang dibuat oleh percobaan tersebut. Dari clone yang sudah ada:

```bash
cd ~/Media-keycloud
git pull --ff-only origin main
sudo bash scripts/install-vps.sh --proxy=caddy
```

Jalankan dalam sesi tmux bila koneksi SSH mungkin terputus. Pastikan DNS A `media.keycloud.id` dan `media-dev.keycloud.id` menunjuk VPS, serta port 80/443 terbuka pada firewall/provider. Perbaiki record AAAA bila IPv6 tidak melayani VPS ini. Proses build pertama dapat berlangsung beberapa menit.

Installer meminta password Basic Auth development untuk username `reviewer`, kemudian email dan password admin untuk masing-masing lingkungan. Password Basic Auth minimal 12 karakter ASCII, maksimal 72 byte. Caddy menerbitkan HTTPS otomatis dengan pengaturan sertifikat yang sudah digunakan; mode ini tidak memasang Nginx atau Certbot.

## Cara integrasi bekerja

Pemeriksaan awal memastikan Caddy aktif sebagai layanan systemd, memakai Caddyfile yang ditunjuk, dan konfigurasi aktif cocok dengan isi file tersebut. Domain yang sudah didefinisikan tidak ditimpa. Pemakaian port 8081/8082 oleh aplikasi lain juga menghentikan installer sebelum pemasangan.

Installer menyimpan salinan Caddyfile ke direktori privat `/var/backups/mahad-media/caddy-*/`. File rute baru dibuat di `/etc/caddy/media-keycloud.caddy`; hanya baris `import` yang ditambahkan ke Caddyfile utama bila belum tercakup import wildcard. Blok situs dan pengaturan global lama tetap dipertahankan.

Konfigurasi lengkap divalidasi sebelum `caddy reload`. Bila validasi atau reload ditolak, perubahan file pemasangan dipulihkan; Caddy mempertahankan konfigurasi yang berjalan ketika reload ditolak. Password disimpan sebagai hash bcrypt. Caddy sebelum 2.8 menggunakan `basicauth`, sedangkan versi 2.8 ke atas menggunakan `basic_auth`.

Pemeriksaan dapat dijalankan sendiri tanpa mengubah konfigurasi:

```bash
sudo python3 scripts/configure-caddy.py --check
```

Jika layanan memakai lokasi Caddyfile lain, periksa `sudo systemctl cat caddy`, kemudian gunakan path sebenarnya:

```bash
sudo bash scripts/install-vps.sh --proxy=caddy --caddy-config=/path/Caddyfile
```

Installer otomatis ditujukan untuk Caddy yang dikelola melalui Caddyfile. Konfigurasi lewat API, `--resume`, admin endpoint Unix socket/nonaktif, atau panel pengelola harus diintegrasikan melalui pengelolanya; installer berhenti tanpa mengganti konfigurasi tersebut. Admin endpoint dipakai hanya secara lokal untuk membandingkan konfigurasi, dan tidak perlu dibuka ke internet.

## Bila pemasangan berhenti setelah database terbentuk

Jangan ulangi inisialisasi secret. Lanjutkan langkah yang belum selesai dari [VPS.md](VPS.md#5-melanjutkan-instalasi-yang-terhenti), lalu integrasikan Caddy:

```bash
sudo python3 scripts/configure-caddy.py
# Buat admin hanya pada lingkungan yang belum memiliki admin.
sudo bash scripts/compose.sh prod exec -u www-data app php artisan media:admin admin@domain-anda.id
sudo bash scripts/compose.sh dev exec -u www-data app php artisan media:admin admin@domain-anda.id
```

Script konfigurasi Caddy dapat dijalankan ulang: jika rute yang dikelolanya sudah aktif, file dan password dipertahankan. Bila terputus paksa saat penulisan file, periksa file import dan backup sebelum melanjutkan. Backup ini hanya salinan Caddyfile utama; import milik situs lain tidak diubah atau dihapus.

## Memeriksa hasil

```bash
sudo bash scripts/compose.sh prod ps
sudo bash scripts/compose.sh dev ps
curl --fail http://127.0.0.1:8081/up
curl --fail http://127.0.0.1:8082/up
sudo systemctl is-active caddy
sudo journalctl -u caddy -n 60 --no-pager
curl -I https://media.keycloud.id
curl -I https://media-dev.keycloud.id
```

Development tanpa kredensial Basic Auth semestinya merespons `401`; setelah login, situs development dapat dibuka. Jika upstream sehat tetapi HTTPS gagal, periksa DNS, akses port, dan log penerbitan sertifikat. Status aplikasi sehat belum membuktikan sertifikat sudah diterbitkan. Login redaksi berada di `/masuk` setelah melewati Basic Auth pada development.

## Konfigurasi Caddy manual

Untuk Caddy yang dikelola panel/API, pasang aplikasi mengikuti bagian proxy manual di [VPS.md](VPS.md#8-bila-proxyvps-sudah-dikelola-panel-lain). Tambahkan rute berikut melalui pengelola konfigurasi yang benar, dengan mempertahankan seluruh rute lain.

Buat hash terlebih dahulu; perintah meminta password tanpa menampilkannya:

```bash
caddy hash-password --algorithm bcrypt
```

Ganti `HASH_BCRYPT_DARI_PERINTAH` di bawah dengan hasil hash. Untuk Caddy sebelum 2.8, ganti nama direktif `basic_auth` menjadi `basicauth`.

```caddyfile
media.keycloud.id {
    encode gzip
    request_body {
        max_size 8MB
    }
    reverse_proxy 127.0.0.1:8081
}

media-dev.keycloud.id {
    header X-Robots-Tag "noindex, nofollow"
    basic_auth {
        reviewer HASH_BCRYPT_DARI_PERINTAH
    }
    encode gzip
    request_body {
        max_size 8MB
    }
    reverse_proxy 127.0.0.1:8082
}
```

Untuk pengelolaan berbasis Caddyfile, buat backup, tambahkan rute, lalu jalankan `caddy validate --config /path/Caddyfile --adapter caddyfile` sebelum `caddy reload --config /path/Caddyfile --adapter caddyfile`. Jika memakai API/panel, gunakan alur validasi dan penerapan dari pengelola tersebut.

Rujukan resmi: [reverse_proxy](https://caddyserver.com/docs/caddyfile/directives/reverse_proxy), [import](https://caddyserver.com/docs/caddyfile/directives/import), [basic_auth](https://caddyserver.com/docs/caddyfile/directives/basic_auth), [command line](https://caddyserver.com/docs/command-line), dan [API/reload](https://caddyserver.com/docs/api).
