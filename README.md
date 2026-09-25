# Media Ma’had Aly Situbondo

Portal media Islam dan fiqih kontemporer: Laravel 13 / PHP 8.3, PostgreSQL 16, Blade, CSS/JavaScript lokal, Docker, Nginx, dan PWA. Antarmuka mengambil inspirasi hierarki kanal NU Online dan komunikasi media Muhammadiyah, dengan identitas Ma’had Aly sendiri.

## Instalasi VPS

Untuk Ubuntu 24.04, Docker Compose v2, Nginx. Hermes yang sudah ada tidak perlu diubah. Arahkan DNS A `media.keycloud.id` dan `media-dev.keycloud.id` ke IP VPS; port 80/443 harus dapat diakses untuk HTTPS.

```bash
git clone https://github.com/sirMisato/Media-keycloud.git
cd Media-keycloud
tmux new -s media-install
sudo bash scripts/install-vps.sh
```

Installer menjalankan tes, build image, membuat dua database beserta kunci terpisah, mengisi kategori, menyiapkan domain/HTTPS, dan meminta pembuatan admin. Tidak ada kata sandi bawaan. Installer berhenti jika port/domain bentrok atau konfigurasi sudah pernah dibuat. Petunjuk lengkap: [docs/VPS.md](docs/VPS.md).

| Lingkungan | Alamat | Database | Akses |
|---|---|---|---|
| Production | https://media.keycloud.id | media_prod | Publik; artikel awal kosong |
| Development | https://media-dev.keycloud.id | media_dev | Basic Auth + noindex; artikel demo |

Login redaksi: `/masuk`. Admin menambah kontributor melalui **Kontributor → Tambah akun**. Setiap domain punya akun dan sesi terpisah.

## Kemampuan

- Portal, kanal, pencarian, artikel, metadata sosial, sitemap, dan layout ponsel.
- Editor Markdown dengan teks Arab, pratinjau privat, sampul privat, dan rujukan.
- Draf → review → permintaan revisi / penolakan / terbit / jadwal tayang.
- Revisi artikel tayang dibuat sebagai versi baru; versi publik tidak berubah sebelum disetujui.
- Hak akses admin/kontributor, penonaktifan akun, ganti/reset password, dan jejak keputusan.
- Identitas media, logo, email kontak, dan susunan redaksi dapat diubah admin.
- Manifest PWA, ikon, pemasangan pada browser yang mendukung, dan fallback offline. Draf dan halaman redaksi tidak dicache; pekerjaan redaksi tetap memerlukan internet.
- Backup database/unggahan/kunci, pemulihan, dan promosi image yang sudah diuji.

## Pengembangan lokal

PHP 8.3 dengan mbstring, dom, xml, pdo_sqlite, fileinfo, dan gd; Composer 2.

```bash
composer setup
php artisan db:seed --class=DemoSeeder
php artisan media:admin admin@example.com
php artisan serve
php artisan test
```

Development lokal memakai SQLite. CI juga menguji PostgreSQL dan image Docker. Tidak diperlukan Node atau build frontend untuk menjalankan situs. Jalankan `php artisan schedule:work` pada terminal terpisah untuk publikasi terjadwal lokal.

## Pembaruan

```bash
# Jalankan dari checkout pengembangan yang sudah di-commit dan bersih.
sudo bash scripts/release-dev.sh
# Uji di browser development. Gunakan tag yang dicetak oleh build / cat .deploy/tested-image.
sudo bash scripts/promote.sh mahad-media:COMMIT_SHA
```

Lihat [panduan redaksi](docs/REDAKSI.md), [Hermes](docs/HERMES.md), [verifikasi](docs/VERIFIKASI.md). Persetujuan ilmiah dilakukan admin/manusia; aplikasi tidak menghasilkan fatwa otomatis.

## Lisensi & aset

Lisensi proyek mengikuti `LICENSE`. Laravel dan dependensinya memiliki lisensi masing-masing. Ilustrasi editorial bundled dibuat dengan AI; bukan foto lokasi Ma’had Aly, NU, atau Muhammadiyah. Artikel demo hanya untuk pengujian dan ditolak oleh seeder pada production. Tidak menyertakan logo, artikel, atau foto milik NU Online/Muhammadiyah.
