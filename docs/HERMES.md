# Enam profil Hermes + Gemini/Codex + Telegram

PM menerima perintah Telegram dan membagi pekerjaan melalui Kanban native
Hermes kepada lima worker. Tiap profil memiliki model, instruksi, memori, dan
sesi sendiri. Memakai Hermes yang sudah ada; tidak perlu Codex CLI/OpenRouter.

| Profil | Model awal | Tugas |
|---|---|---|
| `media-pm` | Codex / `gpt-5.3-codex` | Koordinasi, acceptance criteria, handoff, Telegram |
| `media-uiux` | Gemini / `gemini-3.8-flash` | Rancangan, Blade/CSS/JS, responsif, aksesibilitas |
| `media-backend` | Codex / `gpt-5.3-codex` | Laravel, database, API, integrasi commit |
| `media-qa` | Gemini / `gemini-3.8-flash` | Pengujian independen QA/QC |
| `media-security` | Codex / `gpt-5.3-codex` | Review akses dan keamanan data |
| `media-devops` | Codex / `gpt-5.3-codex` | Build, rilis, health check, backup |

ID model dipilih saat setup dan harus tersedia bagi akun/proyek. Codex di sini
memakai **OpenAI API berbayar**, provider Hermes `openai-api`, dan Responses API.
Provider Hermes `openai-codex` adalah jalur OAuth langganan, bukan API key.
Gemini memakai provider native `gemini` dan API Google AI Studio.

## Instalasi VPS

1. Cabut key yang pernah dikirim di chat. Buat pengganti pada
   [OpenAI](https://platform.openai.com/api-keys) dan
   [Google AI Studio](https://aistudio.google.com/apikey).
2. Buka akun resmi [@BotFather](https://t.me/BotFather), jalankan `/newbot`,
   buat bot **khusus Media**, dan siapkan tokennya. Jangan memakai token bot
   Hermes lama karena dua poller akan bertabrakan.
3. SSH sebagai user pemilik Hermes, misalnya `ubuntu`:

```bash
cd ~/Media-keycloud
git pull --ff-only origin main
sudo loginctl enable-linger "$USER"
python3 scripts/hermes-team.py setup
```

Python dijalankan **tanpa sudo**. Linger menjaga user service/D-Bus tetap
tersedia setelah SSH putus dan reboot, termasuk scope worker. Jika checkout
bukan pada `main`, periksa `git status` dahulu; jangan force-reset perubahan.

Installer meminta model, dua key baru (input tersembunyi), dan token bot.
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

Kirim pesan biasa `Status tim`, lalu uji kedua provider dan kelima worker:

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

```bash
cd ~/Media-keycloud
python3 scripts/hermes-team.py status
python3 scripts/hermes-team.py profiles
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

Tidak membuat backup key lama. Cabut key lama pada konsol provider. Untuk
rotasi token **bot yang sama**, gunakan BotFather, hentikan tim, edit hanya
`TELEGRAM_BOT_TOKEN` dalam `.env` profil PM di VPS; pertahankan format string
berpetik ganda, nama bot, allowlist, dan izin `600`. Lalu `check` dan `start`.
Jangan kirim token ke chat.

Backup privat perlu mencakup data tim (mengandung rahasia), user unit, serta
backup aplikasi. Jangan commit data tim. Pantau pemakaian disk oleh task/log.

## Pengujian dan referensi

Tes offline: `python3 -m unittest discover -s tests/hermes -p 'test_*.py' -v`.
Tes kontrak native dijalankan bila `MEDIA_HERMES_BIN` menunjuk CLI Hermes dan
`MEDIA_HERMES_PYTHON` menunjuk Python runtime-nya. Memakai home sementara dan
kredensial dummy, tanpa inference atau bot live. CI memin source Hermes.
Tes native mereproduksi penolakan 78 dengan konfigurasi lama dan memastikan
PM hasil perbaikan lolos pemeriksaan startup serta tetap tidak multiplex.

Rujukan primer, diperiksa 26 September 2026:

- [Hermes profiles](https://hermes-agent.nousresearch.com/docs/user-guide/profiles)
- [Hermes gateway standalone dan multiplex](https://hermes-agent.nousresearch.com/docs/user-guide/multi-profile-gateways)
- [Hermes Kanban](https://hermes-agent.nousresearch.com/docs/user-guide/features/kanban)
- [Hermes providers](https://hermes-agent.nousresearch.com/docs/integrations/providers)
- [Hermes Telegram](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/telegram)
- [OpenAI GPT-5.3-Codex](https://developers.openai.com/api/docs/models/gpt-5.3-codex)
- [Gemini models](https://ai.google.dev/gemini-api/docs/models)
- [Telegram Bot API](https://core.telegram.org/bots/api)
