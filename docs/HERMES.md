# Hermes + Gemini + Codex

Aplikasi sudah berfungsi tanpa agent AI. Gunakan Hermes untuk perubahan berikutnya. Kredensial provider tetap berada di konfigurasi Hermes milik user; jangan dimasukkan ke repo, Docker Compose, atau prompt.

```bash
cd ~/Media-keycloud
git switch develop
tmux new -s media-hermes
hermes
```

Konfigurasi model yang sudah berjalan tidak ditimpa installer. Verifikasi versi melalui `hermes --help` dan pilihan model melalui `hermes model`. Sesuaikan nama model dengan yang tersedia pada akun/provider Anda.

Pembagian kerja:

| Pelaksana | Lingkup |
|---|---|
| Hermes dengan model utama Codex | Orkestrasi, backend, integrasi, otorisasi, pengujian, migrasi |
| Delegasi Gemini | UI/UX, Blade, CSS, JavaScript publik, aksesibilitas |

Dokumentasi Hermes menjelaskan `delegation.model`/`delegation.provider` pada konfigurasi. Pin ini berlaku secara global untuk delegasi; jangan mengasumsikan tiap `delegate_task` bisa memilih model sendiri. Gunakan runtime Hermes yang mendukung delegation. Verifikasi konfigurasi terhadap versi terpasang sebelum mengubahnya.

Prompt siap pakai:

```text
Baca README.md, docs/REDAKSI.md, docs/VPS.md, dan docs/VERIFIKASI.md.
Ini aplikasi media Ma’had Aly Situbondo yang sudah dibangun, bukan repo kosong.
Kerjakan pada branch develop. Gunakan Codex untuk backend dan integrasi;
delegasikan perubahan UI/UX kepada Gemini melalui konfigurasi delegasi yang
sudah tersedia. Baca prompts/GEMINI_UI.txt dan prompts/CODEX_BACKEND.txt.

Pertahankan persetujuan admin sebelum publikasi; perubahan pada artikel
terbit wajib menjadi revisi baru. Jangan bocorkan naskah, gambar privat,
atau konfigurasi prod ke publik/development. Jangan membuat konten fiqih
seolah-olah fatwa lembaga. Uji perilaku yang diubah, lalu commit hasil.

Untuk deployment, gunakan script release-dev dan image yang teruji.
Tugas berikutnya: [isi perubahan yang Anda inginkan].
```

Tmux: **Ctrl+B, D** untuk detach; `tmux attach -t media-hermes` untuk kembali. Laptop boleh offline, tetapi VPS dan akses provider AI harus online. Setelah VPS reboot, Docker menyalakan web/scheduler; mulai ulang sesi Hermes jika ingin bekerja lagi.

Referensi yang diperiksa saat penyusunan:
- https://hermes-agent.nousresearch.com/docs/user-guide/features/delegation
- https://laravel.com/framework/docs/13.x/deployment
- https://nu.or.id/
- https://muhammadiyah.or.id/

Lensamu adalah bagian referensi komunikasi media Muhammadiyah; paket menggunakan identitas dan aset sendiri. Tidak menyalin logo/artikel/foto dari kedua organisasi.
