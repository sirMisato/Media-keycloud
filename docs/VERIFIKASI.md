# Hasil verifikasi

Versi awal aplikasi pada commit `020fb22487dbb4b64736cd27da9a8d53de4c99e9` lulus seluruh job [Media CI #36145964851](https://github.com/sirMisato/Media-keycloud/actions/runs/36145964851). Hasilnya tercatat di tabel berikut. Dukungan Caddy ditambahkan dan diuji terpisah sebagaimana dijelaskan di bawah.

| Pemeriksaan | Hasil |
|---|---|
| Tes aplikasi dengan SQLite | 18 tes, 108 assertion; lulus |
| Tes aplikasi dengan PostgreSQL 16 | 18 tes, 108 assertion; lulus |
| Instalasi dependensi dari Composer lock | Lulus |
| Kompilasi template Blade | Lulus |
| Sintaks Bash, Python, dan JavaScript | Lulus |
| Build image Docker production | Lulus |
| Startup stack development dan production | Keduanya sehat dan merespons HTTP |
| Pemisahan konten awal | Production kosong; artikel demo tampil di development |
| Backup dan restore development | Selesai; artikel demo kembali terbaca melalui HTTP |

Pengujian lokal juga meliputi validasi Composer dan respons HTTP beranda, kanal, artikel, login, manifest, serta service worker. Tidak diperlukan proses build frontend.

## Dukungan Caddy yang sudah berjalan

Job `caddy` pada [Media CI #36156830059](https://github.com/sirMisato/Media-keycloud/actions/runs/36156830059), commit `dfd23ed4d39ac11a5e3b559824213d6ec06e26bb`, lulus **6 tes integrasi dengan binary Caddy 2.6.2** dan **2 tes alur installer dengan perintah sistem yang disimulasikan**.

Tes integrasi menjalankan proses Caddy lokal dan memeriksa respons HTTP situs lama sebelum/sesudah pemasangan. Cakupannya: penambahan kedua domain beserta Basic Auth, konfigurasi upstream, password berbentuk hash, backup, pemanggilan ulang tanpa mengganti password, import wildcard tanpa duplikasi, penolakan domain yang sudah ada, dan penolakan jika konfigurasi aktif berbeda dari file. Konfigurasi tidak valid serta simulasi reload ditolak menguji pemulihan file dan kelangsungan respons situs lama.

Tes alur installer memeriksa pemilihan Caddy otomatis/eksplisit, pemasangan Docker/Compose ketika belum tersedia, tidak adanya perintah pemasangan Nginx/Certbot atau penghentian Caddy/Hermes, serta penolakan bentrok layanan sebelum instalasi. Tes ini tidak menjalankan apt pada VPS pengguna. Kode tes tersedia di `tests/deployment/`.

## Skenario redaksi yang diuji

Tes berada di `tests/Feature/EditorialWorkflowTest.php`. Cakupannya meliputi batas hak akses admin/kontributor, kepemilikan draf, pencegahan publikasi lewat manipulasi input, pratinjau privat, persetujuan versi yang tepat, dan penguncian naskah yang sedang direview.

Tes juga memastikan revisi tidak mengganti artikel live sebelum disetujui, keputusan tidak dapat diproses dua kali, jadwal menerbitkan artikel saat waktunya tiba, serta penarikan artikel bekerja. Sampul draf tetap privat. Rujukan kajian dan catatan penolakan divalidasi; HTML mentah dan tautan berbahaya pada Markdown disaring.

Login/logout, akun nonaktif, pengelolaan pengguna dan identitas media, halaman redaksi, larangan seeding demo di production, serta header privasi/noindex turut diuji.

## Pemeriksaan setelah pemasangan VPS

VPS pengguna tidak diakses dalam sesi pembangunan ini. DNS, integrasi Caddy/Nginx pada VPS sebenarnya, sertifikat HTTPS publik, dan pemasangan PWA pada perangkat belum diverifikasi. Pemeriksaan visual dengan browser juga belum selesai karena browser pengujian tidak dapat mengakses server lokal; pemeriksaan HTTP dan template tidak menggantikan peninjauan visual.

Setelah installer selesai, gunakan development untuk memeriksa:

1. Tampilan desktop dan ponsel, navigasi, pencarian, dan teks Arab.
2. Login admin, pembuatan kontributor, penulisan draf beserta gambar dan rujukan.
3. Pengajuan, pratinjau, persetujuan, serta revisi artikel yang sudah terbit.
4. Jadwal tayang dan privasi draf/gambar sebelum persetujuan.
5. HTTPS kedua domain, Basic Auth development, dan instalasi PWA pada perangkat yang akan digunakan.

Panduan operasi, pemulihan, dan pemeriksaan port tersedia di [VPS.md](VPS.md).
