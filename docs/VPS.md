# Menjalankan media Ma’had Aly di VPS

Paket ini berisi aplikasi, bukan hanya kerangka prompt. Hermes tidak diperlukan agar situs tetap hidup. Docker menjalankan web, PostgreSQL, dan scheduler dengan `restart: unless-stopped`. tmux mempertahankan sesi kerja ketika SSH terputus; sesi tmux tidak otomatis kembali setelah reboot.

## 1. Sebelum instalasi

Installer disiapkan untuk Ubuntu 24.04 dengan akses sudo. Periksa ruang penyimpanan, RAM, dan layanan yang sudah berjalan. Build Docker membutuhkan internet dan ruang tambahan untuk image serta dependensi. Installer tidak mengubah konfigurasi Hermes atau kredensial Gemini/Codex.

Buat DNS berikut:

| Jenis | Nama | Tujuan |
|---|---|---|
| A | media | IP publik VPS |
| A | media-dev | IP publik VPS |

Jika ada record AAAA, pastikan IPv6-nya juga menuju VPS dan bisa melayani domain. Port 80/443 harus terbuka di firewall VPS/provider. Installer tidak mengubah firewall. Bila menggunakan proxy DNS/CDN, pastikan penerbitan sertifikat dapat mencapai origin; jangan aktifkan cache untuk `/redaksi`, `/masuk`, `/media`, atau respons privat.

```bash
sudo apt-get update
sudo apt-get install -y git tmux
getent ahostsv4 media.keycloud.id
getent ahostsv4 media-dev.keycloud.id
sudo ss -ltnp
```

Jangan jalankan instalasi otomatis jika 80/443 dikelola Apache, Caddy, panel hosting, atau proxy selain Nginx. Ikuti bagian proxy yang sudah ada di bawah. Port internal 8081 dan 8082 harus kosong. Nginx lain di VPS boleh tetap digunakan; installer menambah file khusus dua domain ini.

## 2. Clone dan tmux

```bash
cd ~
git clone https://github.com/sirMisato/Media-keycloud.git
cd Media-keycloud
tmux new -s media-install
sudo bash scripts/install-vps.sh
```

Installer melakukan tes SQLite dan PostgreSQL, build image production, pembuatan secret unik per lingkungan, migrasi dan kategori, data demo khusus development, Nginx/HTTPS, lalu pembuatan admin pada kedua lingkungan. Proses build pertama bisa memakan waktu beberapa menit.

Isian interaktif:

1. Password **Basic Auth development**, username `reviewer`.
2. Email penerbitan sertifikat HTTPS.
3. Email admin media.
4. Password admin production, diulang; minimal 12 karakter.
5. Password admin development, diulang; gunakan password berbeda.

Password tidak ditampilkan. Tidak ada akun bawaan yang dapat ditebak. Keluar sementara dari tmux dengan **Ctrl+B**, lepaskan, lalu **D**. Kembali dengan `tmux attach -t media-install`.

## 3. Buka aplikasi

| Tujuan | URL |
|---|---|
| Pembaca | https://media.keycloud.id |
| Admin/kontributor production | https://media.keycloud.id/masuk |
| Situs pengujian | https://media-dev.keycloud.id |
| Redaksi pengujian | https://media-dev.keycloud.id/masuk |

Production awal berisi kategori dan halaman profil; artikel ditulis dan disetujui redaksi. Development berisi artikel contoh bertanda demo. Data tersebut tidak dipindahkan ke production saat promosi image.

Admin → Identitas media: isi nama, logo, tagline, tentang media, alamat email, dan susunan redaksi. Admin → Kontributor: buat akun penulis. Tidak ada pendaftaran terbuka atau pengiriman password lewat email otomatis.

PWA bisa dipasang pada browser/perangkat yang mendukung setelah HTTPS aktif. Aset dan halaman offline disimpan, sedangkan artikel, naskah privat, login, gambar unggahan, dan dashboard tidak dicache. Saat offline tampil pemberitahuan untuk menyambungkan koneksi. Editor tidak memiliki autosave offline: tekan **Simpan draf** sebelum meninggalkan halaman.

## 4. Pengoperasian

Jalankan perintah dari root repo. Seluruh perintah Docker menggunakan sudo agar tidak perlu menambah user ke grup Docker.

```bash
sudo bash scripts/compose.sh prod ps
sudo bash scripts/compose.sh dev ps
sudo bash scripts/compose.sh prod logs --tail=100 app scheduler
sudo bash scripts/compose.sh dev logs --tail=100 app
sudo bash scripts/compose.sh prod exec -u www-data app php artisan media:publish-due
```

Scheduler di Docker memeriksa jadwal setiap sekitar 30 detik; waktu tayang memakai WIB. Tidak perlu cron host kedua. Jangan jalankan dua scheduler untuk environment yang sama.

Password yang lupa dipulihkan dari console:

```bash
sudo bash scripts/compose.sh prod exec -u www-data app php artisan media:reset-password email-admin-anda@example.com
```

## 5. Melanjutkan instalasi yang terhenti

Jangan hapus `.deploy/*.env` atau membuat `APP_KEY` baru. Jika file secret sudah dibuat, installer memang menolak menimpanya. Perbaiki penyebab kegagalan, lalu jalankan bagian yang belum selesai:

```bash
sudo bash scripts/start.sh dev
sudo bash scripts/start.sh prod
# Hanya jika data contoh dev belum ada; seeder idempoten.
sudo bash scripts/compose.sh dev exec -u www-data app php artisan db:seed --class=DemoSeeder --force
# Jalankan jika Nginx/HTTPS belum selesai. Tidak menimpa file Nginx yang sudah ada.
sudo bash scripts/configure-web.sh
# Jalankan untuk lingkungan yang belum memiliki admin.
sudo bash scripts/compose.sh prod exec -u www-data app php artisan media:admin email-admin-anda@example.com
sudo bash scripts/compose.sh dev exec -u www-data app php artisan media:admin email-admin-anda@example.com
```

Jika pembuatan konfigurasi berhenti setelah hanya satu env terbentuk, pulihkan dari salinan konfigurasi atau buat env kedua secara manual dengan secret baru; jangan menimpa environment yang sudah berjalan. Bila image build gagal sebelum `.deploy` terbentuk, perbaiki error build lalu ulangi installer.

## 6. Pengembangan dengan Hermes

Gunakan user biasa untuk Hermes; hanya script operasi memakai sudo. Semua proses web berjalan dari image sehingga perubahan file oleh Hermes tidak langsung mengubah production.

```bash
git fetch origin
git switch develop
tmux new -s media-work
hermes
```

Berikan prompt pada [HERMES.md](HERMES.md). Simpan kode dan commit di `develop`. Setelah pekerjaan selesai dan working tree bersih:

```bash
sudo bash scripts/release-dev.sh
sudo cat .deploy/tested-image
```

Perintah ini menguji aplikasi di SQLite/PostgreSQL, build image dengan tag commit, membuat backup development, lalu memasang image tersebut di development. Periksa tampilan, login, artikel, approval, revisi, dan gambar lewat browser. Sebelum promosi, gabungkan commit yang diuji ke `main` melalui alur review repo; jangan mengubah isi image.

```bash
# Ganti COMMIT_SHA dengan tag sebenarnya dari .deploy/tested-image.
sudo bash scripts/promote.sh mahad-media:COMMIT_SHA
```

Promosi memastikan image sama dengan development sehat, membackup production, menjalankan migrasi dan kategori, lalu menyalakan web/scheduler. Data development dan `.env` tidak disalin. Ada jeda layanan singkat selama backup dan migrasi.

## 7. Backup dan pemulihan

```bash
sudo bash scripts/backup.sh prod
sudo bash scripts/backup.sh dev
```

Hasil di `.deploy/backups/ENV-TIMESTAMP/`: dump PostgreSQL, unggahan, konfigurasi runtime termasuk kunci, dan identitas lingkungan. Aplikasi/scheduler dihentikan sementara agar tidak ada penulisan selama snapshot, lalu dinyalakan lagi. Simpan salinan terenkripsi di luar VPS dan tetapkan retensi sesuai kebutuhan. Jangan commit folder `.deploy`; file backup memuat secret.

Pulihkan ke instalasi dan lingkungan **yang sama**:

```bash
sudo bash scripts/restore.sh prod /path/repo/.deploy/backups/prod-TIMESTAMP
```

Restore mengganti database dengan snapshot dan memilih image lama dari backup. Image tersebut harus masih ada di Docker; jangan prune image yang masih dibutuhkan. Data setelah waktu backup tidak termasuk snapshot. Jika restore gagal, layanan tetap berhenti agar tidak menulis ke database yang belum selesai dipulihkan; perbaiki penyebabnya dan ulangi. Pada VPS baru, pindahkan secret dengan aman, sesuaikan `ENV_FILE` ke path baru, sediakan image dengan tag yang sama, buat database kosong dengan kredensial backup, lalu gunakan `pg_restore` dan arsip unggahan sesuai operator. Script sengaja menolak lintas path/database agar backup prod tidak tertukar dengan dev.

Rollback kode tanpa memulihkan database hanya aman bila skema kompatibel. Gunakan backup sebelum migrasi bila perubahan skema tidak kompatibel.

## 8. Bila proxy/VPS sudah dikelola panel lain

Pasang Docker Compose v2 melalui mekanisme resmi distro/panel, jangan jalankan installer Nginx. Dari repo:

```bash
sudo bash scripts/test.sh
sudo docker build --target production -t mahad-media:initial .
sudo python3 scripts/init-env.py
sudo bash scripts/start.sh dev
sudo bash scripts/start.sh prod
```

Tambahkan dua reverse proxy di panel yang ada:

| Domain | Upstream HTTP |
|---|---|
| media.keycloud.id | 127.0.0.1:8081 |
| media-dev.keycloud.id | 127.0.0.1:8082 |

Teruskan `Host` asli, set `X-Forwarded-Proto` ke skema request, dan timpa `X-Forwarded-For` dengan alamat client. Aktifkan HTTPS, batas upload 8 MB, Basic Auth khusus dev, dan header `X-Robots-Tag: noindex, nofollow` pada dev. Jangan membuka PostgreSQL atau port aplikasi ke internet. Lalu jalankan pembuatan akun dan seeding demo dev dari bagian pemulihan.

## 9. Batas paket awal

Belum mencakup SMTP/notifikasi email, pendaftaran mandiri, video hosting, komentar pembaca, analytics, atau push notification. Konten kajian/fatwa harus diverifikasi redaksi keilmuan. Paket ini tidak otomatis mengakses VPS; keberhasilan domain, DNS, HTTPS, dan pemasangan PWA pada perangkat perlu diperiksa setelah installer dijalankan.
