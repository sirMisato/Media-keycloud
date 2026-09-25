# Hasil verifikasi

Kode aplikasi pada commit `020fb22487dbb4b64736cd27da9a8d53de4c99e9` lulus seluruh job [Media CI #36145964851](https://github.com/sirMisato/Media-keycloud/actions/runs/36145964851). Commit sesudahnya hanya memperbarui dokumen hasil ini.

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

## Skenario redaksi yang diuji

Tes berada di `tests/Feature/EditorialWorkflowTest.php`. Cakupannya meliputi batas hak akses admin/kontributor, kepemilikan draf, pencegahan publikasi lewat manipulasi input, pratinjau privat, persetujuan versi yang tepat, dan penguncian naskah yang sedang direview.

Tes juga memastikan revisi tidak mengganti artikel live sebelum disetujui, keputusan tidak dapat diproses dua kali, jadwal menerbitkan artikel saat waktunya tiba, serta penarikan artikel bekerja. Sampul draf tetap privat. Rujukan kajian dan catatan penolakan divalidasi; HTML mentah dan tautan berbahaya pada Markdown disaring.

Login/logout, akun nonaktif, pengelolaan pengguna dan identitas media, halaman redaksi, larangan seeding demo di production, serta header privasi/noindex turut diuji.

## Pemeriksaan setelah pemasangan VPS

VPS pengguna tidak diakses dalam sesi pembangunan ini. DNS, konfigurasi Nginx pada VPS sebenarnya, sertifikat HTTPS, dan pemasangan PWA pada perangkat belum diverifikasi. Pemeriksaan visual dengan browser juga belum selesai karena browser pengujian tidak dapat mengakses server lokal; pemeriksaan HTTP dan template tidak menggantikan peninjauan visual.

Setelah installer selesai, gunakan development untuk memeriksa:

1. Tampilan desktop dan ponsel, navigasi, pencarian, dan teks Arab.
2. Login admin, pembuatan kontributor, penulisan draf beserta gambar dan rujukan.
3. Pengajuan, pratinjau, persetujuan, serta revisi artikel yang sudah terbit.
4. Jadwal tayang dan privasi draf/gambar sebelum persetujuan.
5. HTTPS kedua domain, Basic Auth development, dan instalasi PWA pada perangkat yang akan digunakan.

Panduan operasi, pemulihan, dan pemeriksaan port tersedia di [VPS.md](VPS.md).
