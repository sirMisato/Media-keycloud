# Enam profil Hermes + Codex + Telegram

PM menerima perintah Telegram dan membagi pekerjaan melalui Kanban native
Hermes kepada lima worker. Tiap profil memiliki model, instruksi, memori, dan
sesi sendiri. Memakai Hermes yang sudah ada; tidak perlu Codex CLI/OpenRouter.

| Profil | Model awal | Tugas |
|---|---|---|
| `media-pm` | Codex / `gpt-5.3-codex` | Koordinasi, acceptance criteria, handoff, Telegram |
| `media-uiux` | Codex / `gpt-5.3-codex` | Rancangan, Blade/CSS/JS, responsif, aksesibilitas |
| `media-backend` | Codex / `gpt-5.3-codex` | Laravel, database, API, integrasi commit |
| `media-qa` | Codex / `gpt-5.3-codex` | Pengujian independen QA/QC |
| `media-security` | Codex / `gpt-5.3-codex` | Review akses dan keamanan data |
| `media-devops` | Codex / `gpt-5.3-codex` | Build, rilis, health check, backup |

ID model dipilih saat setup dan harus tersedia bagi akun/proyek. Codex di sini
memakai **OpenAI API berbayar**, provider Hermes `openai-api`, dan Responses API.
Provider Hermes `openai-codex` adalah jalur OAuth langganan, bukan API key.
Setup baru memakai Codex untuk semua profil. Konfigurasi Gemini pada instalasi
lama tetap didukung sampai pemilik menjalankan migrasi di bawah.

## Mengganti instalasi lama menjadi semua Codex

Pada Ubuntu, pastikan pembaca YAML tersedia untuk Python sistem yang dipakai
controller service: `sudo apt-get install -y python3-yaml`. Ini diperlukan
jika Hermes menyimpan ulang `config.yaml` sebagai YAML biasa.

Jalankan sebagai user pemasang Hermes, tanpa sudo, satu per satu setelah
perintah sebelumnya berhasil:

```bash
cd ~/Media-keycloud
git pull --ff-only origin main
/usr/bin/python3 scripts/hermes-team.py use-codex
/usr/bin/python3 scripts/hermes-team.py start
/usr/bin/python3 scripts/hermes-team.py models
```

`use-codex` mengambil **model Codex dan OpenAI API key dari profil PM yang
sudah tersimpan**, lalu mengubah keenam profil ke provider `openai-api`.
Migrasi memperbarui manifest dan controller service, memperbaiki konfigurasi
standalone PM bila masih versi lama, menghapus key Gemini dari `.env` profil,
serta menyesuaikan catatan model di SOUL.md. Token/allowlist Telegram,
instruksi peran lokal, memori, sesi, dan task dipertahankan. Tidak meminta
token/key baru dan tidak menghubungi Gemini. Semua biaya inference setelah
migrasi mengikuti akun OpenAI API yang dipakai PM.

Migrasi menghentikan gateway **media-hermes saja** untuk mencegah dispatch
baru. Jika masih ada task `running`, konfigurasi belum diubah: tunggu worker
menyelesaikan tugas, periksa `python3 scripts/hermes-team.py board`, lalu
ulangi `use-codex`. Gateway tetap berhenti selama menunggu. Tidak membunuh
worker atau otomatis menyalakan kembali gateway. Gunakan `start` setelah
migrasi berhasil, lalu kirim smoke test baru melalui Telegram untuk menguji
inference dan dispatch. `models` harus menampilkan `provider=openai-api`
pada **keenam baris**; nama model mengikuti pilihan Codex saat setup lama.

Perubahan file memakai penulisan atomik dan rollback dalam memori jika
penulisan gagal; jangan mematikan VPS saat migrasi. Jika Git menolak pull
karena perubahan lokal, selesaikan perubahan itu dahulu tanpa force-reset.

## Instalasi VPS

1. Cabut key yang pernah dikirim di chat. Buat pengganti pada
   [OpenAI](https://platform.openai.com/api-keys).
2. Buka akun resmi [@BotFather](https://t.me/BotFather), jalankan `/newbot`,
   buat bot **khusus Media**, dan siapkan tokennya. Jangan memakai token bot
   Hermes lama karena dua poller akan bertabrakan.
3. SSH sebagai user pemilik Hermes, misalnya `ubuntu`:

```bash
cd ~/Media-keycloud
git pull --ff-only origin main
sudo apt-get install -y python3-yaml
sudo loginctl enable-linger "$USER"
/usr/bin/python3 scripts/hermes-team.py setup
```

Python dijalankan **tanpa sudo**. Linger menjaga user service/D-Bus tetap
tersedia setelah SSH putus dan reboot, termasuk scope worker. Jika checkout
bukan pada `main`, periksa `git status` dahulu; jangan force-reset perubahan.

Installer meminta model Codex, OpenAI API key (input tersembunyi), dan token bot.
Kirim kode sekali pakai `MEDIA-...` yang ditampilkan installer ke chat **privat**
bot baru, lalu tekan Enter di SSH. Telegram ID diambil dari pesan yang cocok;
tidak perlu mengirim key/token/ID ke ChatGPT. Akses group dinonaktifkan.

Installer memeriksa fitur Hermes, metadata model, bot/webhook, dan pemilik;
kemudian membuat enam profil, board, clone kerja khusus agen, dan user service
`media-hermes.service`. Rahasia disimpan di `.env` profil dengan izin `600`
di bawah direktori `700`. Tidak memerlukan port HTTP atau webhook publik baru.

Lokasi data: `~/.local/share/media-keycloud`. Home/antrean ini terpisah agar
Hermes lama tidak mengambil tugas tim. Caddy, situs, `.deploy`, default profile,
dan service Hermes lama tidak diubah. Binary Hermes tetap dipakai bersama.
Clone kerja tidak menyalin file yang diabaikan git seperti `.deploy`/`.env`.

Profil **bukan sandbox keamanan/akun OS terpisah**. Worker memiliki hak user
VPS; installer tidak memberi sudoers atau akses Docker baru. Bila memerlukan
pembatasan filesystem/jaringan yang kuat, gunakan akun OS/container terpisah.

`setup --no-start` menyiapkan konfigurasi tanpa menyalakan bot. Setelah linger
tersedia gunakan `python3 scripts/hermes-team.py start`. Jangan memasang
gateway tambahan dengan `hermes gateway install` untuk profil tim ini.

PM menggunakan `gateway.standalone: true` agar service khusus ini diizinkan
Hermes. Ini opsi kompatibilitas sementara dari upstream; `multiplex_profiles:
false` saja tidak cukup pada Hermes sekarang. Hanya PM menjalankan gateway.

## Perintah Telegram

Kirim pesan biasa `Status tim`, lalu uji Codex pada keenam profil:

```text
Jalankan smoke test enam profil. PM membuat lima task ringan untuk UI/UX,
Backend, QA/QC, Security, dan DevOps. Setiap worker hanya memeriksa direktori,
SHA repo dan README, lalu melaporkan profil/provider/model. Jangan edit atau
deploy. Laporkan hasil nyata semua task, termasuk error quota atau akses.
```

Contoh pekerjaan:

```text
Perbaiki navigasi kategori pada ponsel. PM tetapkan acceptance criteria,
UI/UX kerjakan tampilan, Backend bila perlu perubahan data, QA/QC dan
Security tinjau commit yang sama. Siapkan rilis development setelah lolos.
Production menunggu instruksi saya.
```

```text
Audit alur kontributor → review admin → publikasi. Jangan mengubah production.
```

```text
Promosikan image mahad-media:SHA_YANG_DILAPORKAN ke production setelah
verifikasi development dan laporan PASS QA serta Security pada commit itu.
```

`/help`, `/status`, `/whoami`, `/kanban list` merupakan perintah native Hermes.
Contoh di atas adalah pesan bahasa alami, bukan slash command baru.
`/stop` menghentikan giliran chat, bukan otomatis seluruh worker OS.

## Alur dan batas akses

Implementasi → integrasi satu kandidat SHA → QA/Security pada SHA itu → DevOps.
PM meneruskan hasil task melalui Kanban; task turunan menunggu parent selesai.
Review gagal memblokir pekerjaan. Perubahan baru perlu review SHA baru.
Production memerlukan instruksi pemilik untuk rilis yang dimaksud.

Konfigurasi native membatasi **dua worker sekaligus**, **satu per profil**,
40 iterasi alat per giliran, dan circuit breaker setelah dua kegagalan.
Instruksi PM menetapkan 30 menit per task serta dua siklus revisi. Ini bukan
plafon biaya uang; atur budget/quota di masing-masing provider.

PM hanya memakai Kanban/memory/todo; lima worker menggunakan worktree terpisah.
Tidak ada delegate_task berlapis atau bot tambahan untuk worker. Instruksi
[hermes/roles](../hermes/roles) dirender menjadi SOUL.md profil.
Review/promosi merupakan kebijakan orkestrasi LLM, bukan gerbang keamanan
independen yang menjamin kepatuhan model. Pembatasan native dan script deploy
tetap berlaku.

DevOps menggunakan `scripts/release-dev.sh` serta `scripts/promote.sh` yang
sudah ada. Promosi memeriksa tested-image, image dev, health container, dan
membuat backup. Hak sudo/Docker noninteraktif harus sudah diizinkan pemilik;
jika belum, worker memblokir tugas dan menjelaskan kebutuhan. Jangan memberi
`NOPASSWD: ALL` hanya agar tugas lewat. Push GitHub memerlukan autentikasi VPS
yang sudah tersedia; jika belum, hasil disimpan sebagai commit lokal.
Browser QA memerlukan tool/browser Hermes dan akses test/dev yang berfungsi.
Tes yang terhalang akses/dependensi harus dilaporkan, bukan dianggap PASS.

## Status dan diagnosis

Jika `use-codex` berhenti dengan pesan lama `Operasi lokal gagal`, ambil
skrip terbaru dan jalankan diagnosis **sebagai user pemasang Hermes, tanpa sudo**:

```bash
cd ~/Media-keycloud &&
git pull --ff-only origin main &&
python3 scripts/hermes-team.py diagnose
```

`diagnose` hanya membaca kondisi lokal: UID/izin file, akses direktori,
lock pemasangan, format `team.json`, konfigurasi/env enam profil, serta
kecocokan unit/controller. Tidak mencetak isi file, nilai konfigurasi,
key/token, atau path dari manifest. Tidak memanggil Hermes/API/Telegram,
mengubah file/izin, atau menghentikan service. Exit code `1` berarti ada
masalah pada laporan; `0` hanya berarti pemeriksaan lokal lolos.
Bagikan keluarannya untuk menentukan langkah berikutnya. Tidak perlu
membagikan `.env`, `config.yaml`, atau output traceback.

Label `direktori data tim` merujuk `~/.local/share/media-keycloud`, profil
berada di `hermes/profiles` di dalamnya, dan lock di
`~/.cache/media-keycloud/setup.lock`. Jika instalasi menggunakan lokasi
khusus, tambahkan `--data-dir /lokasi/tim` pada perintah.
Laporan `EACCES` menunjukkan masalah akses, bukan alasan menjalankan
installer dengan sudo atau mengubah seluruh home memakai `chown -R`.
Lock yang sibuk harus ditunggu, bukan dihapus. Manifest yang hilang atau
rusak perlu ditinjau bersama file tim yang masih ada sebelum setup ulang.

### Config PM/Backend dilaporkan bukan JSON

Skrip lama hanya membaca JSON walaupun nama file `config.yaml`. Hermes dapat
menyimpan file tersebut sebagai YAML (termasuk mapping dalam satu baris),
sehingga error JSON belum membuktikan bahwa file rusak. Pembaca baru menerima
kedua format; isi konfigurasi tetap harus cocok dengan manifest pemasangan.
`team.json` tetap memerlukan JSON, dan format `.env` tetap berpetik ganda.

```bash
sudo apt-get install -y python3-yaml
cd ~/Media-keycloud &&
git pull --ff-only origin main &&
/usr/bin/python3 scripts/hermes-team.py diagnose &&
/usr/bin/python3 scripts/hermes-team.py use-codex &&
/usr/bin/python3 scripts/hermes-team.py models &&
/usr/bin/python3 scripts/hermes-team.py start
```

`sudo` hanya untuk pemasangan paket Ubuntu. Interpreter `/usr/bin/python3`
memastikan skrip menggunakan paket YAML yang juga tersedia pada controller
systemd. Pembacaan/diagnosis tidak mengubah file. Migrasi yang berhasil
menulis konfigurasi enam profil dalam format JSON yang juga valid YAML,
serta memperbarui controller agar startup berikutnya bisa membaca YAML.
Sesi, task, instruksi peran lokal, token Telegram, dan OpenAI key dipertahankan.

Jika masih muncul `YAML tidak valid` atau `Konfigurasi ... berubah dari
manifest`, berhenti dan bagikan pesan error/diagnosis. Jangan mengganti
config dengan template kosong atau menjalankan setup ulang. Parser menolak
nama field ganda, tag objek, merge key, serta struktur rekursif/terlalu besar;
pesan error tidak menampilkan cuplikan isi file. Tidak ada perbaikan otomatis
untuk sintaks rusak atau perubahan pengaturan yang belum dikenali.

### Config terbaca, tetapi dianggap berubah dari manifest

Hermes dapat menambahkan `_config_version` saat migrasi otomatis. Pada
runtime Hermes yang diuji, migrasi profil PM/Backend menambahkan penanda
versi ini tanpa mengubah model, tool, atau allowlist. Hermes juga menyimpan
penanda petunjuk awal pada `onboarding.seen`, misalnya setelah kontak pertama
atau petunjuk progres tool. Validator lama membandingkan seluruh isi file
dan menolak metadata yang belum dikenali sebagai field tambahan.

Versi baru menerima `_config_version` berupa bilangan bulat positif serta
bagian `onboarding` dengan format yang dikenali dari Hermes:

- `seen` berupa mapping dengan nilai boolean untuk `busy_input_prompt`,
  `tool_progress_prompt`, `openclaw_residue_cleanup`, dan `profile_build_offered`.
- `profile_build` opsional bernilai `ask` atau `off` untuk preferensi tawaran
  pengenalan pengguna. Bagian/penanda yang belum tersimpan tidak ditambahkan.

Keduanya dipertahankan ketika `use-codex` atau `repair-gateway` menulis config.
Pemeriksaan model, endpoint, tool, terminal, dan akses Telegram tetap ketat;
field tambahan lain, penanda yang belum dikenal, dan nilai metadata yang
tidak valid tetap ditolak. Tidak perlu menghapus `onboarding`, penanda versi,
atau mereset file profil. Jalankan sebagai user pemasang, tanpa sudo:

```bash
cd ~/Media-keycloud &&
git pull --ff-only origin main &&
/usr/bin/python3 scripts/hermes-team.py diagnose &&
/usr/bin/python3 scripts/hermes-team.py use-codex &&
/usr/bin/python3 scripts/hermes-team.py models &&
/usr/bin/python3 scripts/hermes-team.py start
```

`Diagnosis lokal v2` memeriksa semua profil dan, jika masih berbeda,
menampilkan nama field dari skema installer, misalnya `model.default:
berbeda` atau `platforms.telegram.extra.allow_from: berbeda`. Nilai field
tidak dicetak. Field tambahan yang belum dikenal hanya dihitung; nama/nilai
arbitrer tidak dicetak karena dapat mengandung rahasia. Jika diagnosis
berhenti, bagikan baris `[GAGAL]` terbaru sebelum mengubah config. Jangan
menganggap setiap perbedaan sebagai penanda versi otomatis.

```bash
cd ~/Media-keycloud
python3 scripts/hermes-team.py status
python3 scripts/hermes-team.py profiles
python3 scripts/hermes-team.py models
python3 scripts/hermes-team.py board
python3 scripts/hermes-team.py check
python3 scripts/hermes-team.py logs
python3 scripts/hermes-team.py restart
```

`check` memeriksa file/config, metadata model, identitas bot, dan webhook.
`check --offline` tanpa jaringan. Status service aktif **belum membuktikan
balasan LLM**; smoke test Telegram membuktikan inference, tool use, dispatch,
dan handoff pada VPS. Tinjau/redaksi log sebelum membagikannya.

| Gejala | Tindakan |
|---|---|
| `hermes` tidak ditemukan | Pakai user pemasang; periksa `command -v hermes` dan PATH |
| Fitur profiles/Kanban gagal | Periksa `hermes --help`; jalankan updater resmi `hermes update` pada waktu sesuai, lalu ulang setup |
| Model 404/403 | Pilih ID model yang tersedia bagi API key/proyek pada prompt |
| 429 / insufficient quota | Periksa billing/quota; jangan mengulang tanpa batas |
| Telegram 409 | Bot dipakai poller lain; hentikan duplikat milik bot tersebut atau buat bot baru |
| Webhook aktif | Pakai bot khusus baru; installer tidak menghapus webhook lama |
| D-Bus/linger tidak ada | `sudo loginctl enable-linger "$USER"`, login ulang bila perlu, lalu `start` |
| `Profile 'media-pm' does not get a gateway of its own`, exit `78/CONFIG` | Jalankan pemulihan gateway di bawah; tidak perlu setup ulang |
| Bot diam | Periksa service/log, chat privat, `/whoami`, serta API/billing |
| Task blocked | Baca alasan, perbaiki sebab, minta PM melanjutkan task terkait |
| sudo/Docker/browser tidak ada | Siapkan hak/dependensi secara terpisah; worker tidak otomatis melewati batas |

Setup menolak direktori tim/unit yang sudah ada. Jika terputus sebelum
`team.json` tersedia, periksa `~/.local/share/media-keycloud` serta
`~/.config/systemd/user/media-hermes.service`. Hentikan unit tim bila ada,
lalu **pindahkan** keduanya ke nama backup unik sebelum setup ulang. Jangan
menghapus `~/.hermes`, checkout web, atau `.deploy`. Jika `team.json` ada dan
hanya startup gagal, gunakan `start`, bukan setup ulang.

### Memulihkan penolakan gateway PM (exit 78)

Paket awal belum menandai PM sebagai gateway standalone. Untuk instalasi
yang sudah menyimpan enam profil dan `team.json`, jalankan sebagai user
pemasang Hermes, **tanpa sudo**:

```bash
cd ~/Media-keycloud
git status --short
git pull --ff-only origin main
python3 scripts/hermes-team.py repair-gateway
python3 scripts/hermes-team.py start
python3 scripts/hermes-team.py logs
```

Jika Git menolak pembaruan karena perubahan lokal/divergensi, simpan dan
tinjau perubahan itu dahulu; jangan force-reset. Jalankan langkah berikutnya
hanya setelah langkah sebelumnya berhasil.

`repair-gateway` memeriksa konfigurasi lama, menghentikan **media-hermes saja**,
menambahkan `gateway.standalone: true` pada PM, memperbarui salinan
`control.py` yang dipakai service, serta menghapus status gagal systemd.
Key/token, allowlist, role, memori, sesi, dan task dipertahankan. Perintah ini
tidak menyalakan gateway; `start` melakukan pemeriksaan API/bot sebelum
menyalakannya. Unit baru tidak mengulang startup untuk error konfigurasi 78.
Pemulihan boleh diulang; unit atau konfigurasi lain yang tidak dikenali
ditolak sebelum service dihentikan. Jangan hanya mengedit config PM manual,
karena controller lama memeriksa konfigurasi tersebut secara ketat.

Tunggu sekitar 15 detik setelah `start`, periksa `status` dan `logs`, lalu
kirim `/whoami` dan `Status tim` di chat privat bot. Service `active` sesaat
setelah start belum membuktikan bot berhasil terhubung. Bila log masih
menyebut `automatic dependency repair limit reached`, simpan error lengkap
terbarunya untuk diagnosis dependensi; pesan itu terpisah dari penolakan 78.

## Penghentian dan rotasi

`python3 scripts/hermes-team.py stop` menghentikan gateway/dispatcher. Worker
aktif bisa bertahan dalam scope systemd sendiri. Untuk menghentikan semua
pekerjaan, hentikan gateway, catat task aktif dari board, kemudian block dan
hentikan **scope ID task tim ini saja**:

```bash
python3 scripts/hermes-team.py stop
python3 scripts/hermes-team.py board
# Ganti t_ID dengan task aktif dari board media-keycloud.
HERMES_HOME="$HOME/.local/share/media-keycloud/hermes" \
  hermes -p media-pm kanban --board media-keycloud block t_ID \
  --kind needs_input "Dihentikan oleh pemilik"
systemctl --user list-units 'hermes-worker-kanban-t_ID-run-*.scope'
# Gunakan nama scope persis yang tercetak untuk task itu:
systemctl --user stop NAMA_SCOPE_TASK
```

Ulangi untuk task lain. Jangan memakai wildcard seluruh worker Hermes karena
akan mencakup tim lama. Untuk mematikan auto-start saat boot:
`systemctl --user disable media-hermes.service`.

Setelah worker selesai/dihentikan, rotasi provider key:

```bash
python3 scripts/hermes-team.py rotate-keys
python3 scripts/hermes-team.py restart
```

Pada mode semua Codex, `rotate-keys` hanya meminta satu OpenAI API key dan
memperbaruinya pada keenam profil. Instalasi lama yang belum dimigrasi masih
meminta dua key sesuai pemetaan lamanya.
Tidak membuat backup key lama. Cabut key lama pada konsol provider. Untuk
rotasi token **bot yang sama**, gunakan BotFather, hentikan tim, edit hanya
`TELEGRAM_BOT_TOKEN` dalam `.env` profil PM di VPS; pertahankan format string
berpetik ganda, nama bot, allowlist, dan izin `600`. Lalu `check` dan `start`.
Jangan kirim token ke chat.

Backup privat perlu mencakup data tim (mengandung rahasia), user unit, serta
backup aplikasi. Jangan commit data tim. Pantau pemakaian disk oleh task/log.

## Pengujian dan referensi

Tes offline membutuhkan PyYAML (`python3-yaml` pada Ubuntu):
`python3 -m unittest discover -s tests/hermes -p 'test_*.py' -v`.
Tes kontrak native dijalankan bila `MEDIA_HERMES_BIN` menunjuk CLI Hermes dan
`MEDIA_HERMES_PYTHON` menunjuk Python runtime-nya. Memakai home sementara dan
kredensial dummy, tanpa inference atau bot live. CI memin source Hermes.
Tes native mereproduksi penolakan 78 dengan konfigurasi lama dan memastikan
PM hasil perbaikan lolos pemeriksaan startup serta tetap tidak multiplex.
Tes juga memigrasikan profil lama memakai CLI Kanban asli dan memeriksa
keenam runtime memakai OpenAI API dengan mode `codex_responses`, tanpa
inference berbayar. Regresi mencakup worker aktif, rollback penulisan gagal,
preservasi bot/riwayat/instruksi lokal, dan rotasi key tanpa Gemini.
Regresi YAML mencakup file hasil penulis konfigurasi Hermes asli, migrasi
format flow/block, diagnosis tanpa penulisan, serta penolakan konfigurasi
berubah/rusak dan redaksi rahasia pada pesan parser.
Tes native juga menjalankan migrasi skema Hermes pada PM/Backend sebelum
migrasi ke Codex, memanggil helper kontak pertama dan petunjuk onboarding
asli, lalu memastikan penanda versi/petunjuk tetap tersimpan. Penulisan
petunjuk setelah migrasi juga harus lolos pemeriksaan keenam profil.
Regresi meliputi metadata versi/onboarding tidak valid serta perubahan
akses yang tetap ditolak meskipun metadata tersedia.

Rujukan kompatibilitas onboarding, diperiksa 6 Oktober 2026:
[helper onboarding Hermes pada versi yang dipakai CI](https://github.com/NousResearch/hermes-agent/blob/11c50f05d070b2158afdca73f077d2501ecd77fc/agent/onboarding.py).

Rujukan primer, diperiksa 26 September 2026:

- [Hermes profiles](https://hermes-agent.nousresearch.com/docs/user-guide/profiles)
- [Hermes gateway standalone dan multiplex](https://hermes-agent.nousresearch.com/docs/user-guide/multi-profile-gateways)
- [Hermes Kanban](https://hermes-agent.nousresearch.com/docs/user-guide/features/kanban)
- [Hermes providers](https://hermes-agent.nousresearch.com/docs/integrations/providers)
- [Hermes Telegram](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/telegram)
- [OpenAI GPT-5.3-Codex](https://developers.openai.com/api/docs/models/gpt-5.3-codex)
- [Gemini models](https://ai.google.dev/gemini-api/docs/models)
- [Telegram Bot API](https://core.telegram.org/bots/api)
