# Pembaruan OpenAI, tampilan ponsel, dan profil pendidikan

Untuk instalasi Media-keycloud yang sudah live. Jalankan di VPS sebagai user `ubuntu` yang memasang tim Hermes; hanya operasi Docker menggunakan `sudo`. Pembaruan ini tidak memerlukan instalasi ulang Caddy atau perubahan domain.

## 1. Ambil kode terbaru

```bash
cd ~/Media-keycloud
git status --short
git pull --ff-only origin main
```

Working tree harus bersih. Bila ada perubahan lokal, commit atau simpan perubahan tersebut terlebih dahulu; jangan gunakan reset paksa. Bila pull menolak karena cabang berbeda, periksa cabangnya sebelum melanjutkan.

## 2. Pindahkan enam profil ke OpenAI

Berlaku untuk tim yang dipasang melalui `scripts/hermes-team.py setup`:

```bash
python3 scripts/hermes-team.py use-codex
python3 scripts/hermes-team.py models
python3 scripts/hermes-team.py start
```

PM, UI/UX, Backend, QA/QC, Security, dan DevOps harus menunjukkan `provider=openai-api` dengan model Codex yang sama. Migrasi mengambil API key/model dari profil PM, mempertahankan bot Telegram dan peran agen, serta menghapus Gemini key dari konfigurasi aktif tim. Tidak ada API key di frontend situs.

Migrasi berhenti bila masih ada worker dengan task `running`. Tunggu task selesai, lalu ulangi `use-codex`; jangan membunuh pekerjaan yang masih berlangsung. Bila setup tim belum pernah dilakukan, ikuti [HERMES.md](HERMES.md). API key yang pernah dibagikan di chat harus diganti melalui `rotate-keys`; jangan menuliskan key di Git atau tangkapan layar.

## 3. Pasang dan periksa development

```bash
sudo bash scripts/release-dev.sh
sudo cat .deploy/tested-image
```

Perintah menjalankan pengujian, build image, backup, dan memperbarui development. Buka `https://media-dev.keycloud.id/` memakai Basic Auth development.

Periksa:

- Ponsel: header ringkas, kanal bisa digeser, navigasi Beranda/Kanal/Cari/Profil tidak menutupi konten.
- Pencarian: buka Cari, masukkan kata kunci, buka hasil. Form pencarian juga tersedia tanpa JavaScript.
- Profil: `/profil-mahad-aly` memuat identitas pendidikan, takhassus, sumber, dan tautan situs resmi.
- PWA: tombol **Pasang aplikasi** menampilkan prompt browser jika tersedia atau petunjuk pemasangan. iPhone/iPad memakai Safari → Bagikan → Tambah ke Layar Utama. Dukungan prompt bergantung perangkat/browser; Basic Auth development bisa membatasi pemasangan.
- Buka artikel dan pastikan judul, rujukan, sampul, serta tombol Bagikan berfungsi. Proses redaksi tetap memerlukan internet.

PWA hanya menyimpan aset antarmuka dan halaman offline. Artikel, gambar unggahan, halaman redaksi, login, serta profil HTML tidak dicache. Artikel yang ditarik redaksi tidak akan tetap tersedia melalui cache offline.

## 4. Terapkan image yang sama ke production

Setelah development diperiksa, jalankan dengan tag persis yang dicetak pada langkah sebelumnya:

```bash
sudo bash scripts/promote.sh mahad-media:COMMIT_SHA
```

Ganti `mahad-media:COMMIT_SHA` dengan hasil `sudo cat .deploy/tested-image`. Promosi membuat backup dan tidak menyalin artikel demo ke production. Ada jeda layanan singkat selama backup/restart. Cek kembali `https://media.keycloud.id/` dan `/profil-mahad-aly`. Buka ulang PWA agar service worker versi baru aktif; aset CSS/JS memiliki penanda versi otomatis.

## Isi profil pendidikan

Profil di `resources/views/public/institution.blade.php` memuat identitas dan takhassus yang terverifikasi. Situs `maalysitubondo.ac.id` belum dapat dibaca saat pembaruan; identitas pesantren diperiksa melalui `sukorejo.com`, sedangkan jenjang/program melalui daftar PBSB Kementerian Agama. Tautan sumber tersedia di halaman profil. Tidak ditambahkan data pengurus, akreditasi, jadwal, biaya, atau klaim penerimaan yang belum diverifikasi.

Referensi tampilan adalah hierarki kanal dan editorial NU Online. Identitas, konten, logo, dan foto NU Online tidak disalin. Lambang dekoratif pada halaman profil bukan logo resmi lembaga. Logo media tetap dapat diatur di ruang redaksi.

## Verifikasi kode

```bash
php artisan test
node --test tests/pwa/service-worker.test.cjs
node --check public/assets/app.js
node --check public/sw.js
```

Node hanya diperlukan untuk tes PWA, bukan untuk menjalankan aplikasi di VPS. CI juga menguji Hermes native, Caddy, PostgreSQL, build Docker, dan pemulihan backup.
