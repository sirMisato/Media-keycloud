#!/usr/bin/env python3
"""Tim Hermes Media Keycloud. Python stdlib; rahasia hanya diminta di TTY VPS."""
from __future__ import annotations

import argparse
import fcntl
import getpass
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request

BOARD = "media-keycloud"
SERVICE = "media-hermes.service"
DEFAULT_CODEX = "gpt-5.3-codex"
DEFAULT_GEMINI = "gemini-3.8-flash"
REPO_URL = "https://github.com/sirMisato/Media-keycloud.git"
OTHER_PLATFORMS = ("local", "discord", "whatsapp", "whatsapp_cloud", "slack", "signal",
                   "mattermost", "matrix", "homeassistant", "email", "sms", "dingtalk",
                   "api_server", "webhook", "msgraph_webhook", "feishu", "wecom",
                   "wecom_callback", "weixin", "bluebubbles", "qqbot", "yuanbao", "relay")
ROLES = {
    "pm": ("PM", "Koordinator Telegram dan perutean task; bukan worker implementasi."),
    "uiux": ("UI/UX", "Rancangan dan implementasi Blade/CSS/JS, responsif dan aksesibilitas."),
    "backend": ("Backend", "Laravel, database, otorisasi, API dan integrasi commit."),
    "qa": ("QA/QC", "Pengujian independen acceptance criteria, regresi dan browser."),
    "security": ("Security", "Review defensif akses, data privat, unggahan dan dependensi."),
    "devops": ("DevOps", "Build, deployment yang diizinkan, health check dan backup."),
}


class TeamError(Exception):
    pass


def run(args, *, env=None, cwd=None, timeout=90):
    """Capture output; callers print only known non-secret diagnostics."""
    try:
        result = subprocess.run([str(a) for a in args], env=env, cwd=cwd,
                                capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        raise TeamError(f"Perintah {Path(str(args[0])).name} tidak tersedia atau timeout.") from None
    if result.returncode:
        # Do not echo child output: Hermes may report credential-bearing URLs.
        raise TeamError(f"Perintah {Path(str(args[0])).name} gagal (exit {result.returncode}).")
    return result.stdout.strip()


def write_private(path, content, *, mode=0o600):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if path.is_symlink():
        raise TeamError(f"Menolak menulis symlink: {path.name}")
    fd, temporary = tempfile.mkstemp(prefix=".media-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            os.fchmod(handle.fileno(), mode)
            handle.write(content)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def write_json(path, value):
    # JSON is valid YAML; no PyYAML installation is needed on the VPS.
    write_private(path, json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def isolated_env(root):
    # Fresh environment: do not inherit another bot, provider, profile selector,
    # yolo setting, terminal pin, or a system-wide allow-all setting.
    keep = ("HOME", "USER", "LOGNAME", "PATH", "LANG", "LC_ALL", "TERM", "SHELL",
            "XDG_RUNTIME_DIR", "DBUS_SESSION_BUS_ADDRESS", "XDG_CONFIG_HOME",
            "INVOCATION_ID", "JOURNAL_STREAM", "SYSTEMD_EXEC_PID", "NOTIFY_SOCKET",
            "SSL_CERT_FILE", "SSL_CERT_DIR", "SSH_AUTH_SOCK")
    env = {name: os.environ[name] for name in keep if name in os.environ}
    env.update(HERMES_HOME=str(root), HERMES_KANBAN_HOME=str(root),
               HERMES_KANBAN_BOARD=BOARD, HERMES_REDACT_SECRETS="true",
               TELEGRAM_ALLOW_ALL_USERS="false", TELEGRAM_ALLOW_BOTS="false",
               GATEWAY_ALLOW_ALL_USERS="false", PYTHONUNBUFFERED="1")
    return env


def user_bus_env():
    env = os.environ.copy()
    runtime = f"/run/user/{os.getuid()}"
    env["XDG_RUNTIME_DIR"] = runtime
    env["DBUS_SESSION_BUS_ADDRESS"] = f"unix:path={runtime}/bus"
    return env


def control(action):
    return run(["systemctl", "--user", action, SERVICE], env=user_bus_env())


def assert_linger():
    name = getpass.getuser()
    enabled = run(["loginctl", "show-user", name, "-p", "Linger", "--value"])
    if enabled != "yes" or not Path(f"/run/user/{os.getuid()}/bus").exists():
        raise TeamError(f"Jalankan `sudo loginctl enable-linger {name}`, lalu ulangi. "
                        "Gateway dan worker membutuhkan user D-Bus agar tetap hidup setelah logout.")
    run(["systemctl", "--user", "show-environment"], env=user_bus_env())


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def api_json(url, label, *, headers=None, body=None):
    data = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request(url, data=data, headers={
        "Content-Type": "application/json", **(headers or {})})
    try:
        with urllib.request.build_opener(NoRedirect).open(request, timeout=30) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        hint = {401: "kredensial tidak valid", 403: "akses ditolak",
                404: "model/endpoint tidak tersedia", 409: "bot dipakai proses lain",
                429: "batas quota/rate limit"}.get(error.code, "permintaan gagal")
        raise TeamError(f"{label}: HTTP {error.code}, {hint}. Tidak ada rahasia yang dicetak.") from None
    except (OSError, ValueError, urllib.error.URLError):
        raise TeamError(f"{label}: koneksi/TLS atau respons tidak valid.") from None


def model_id(value):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,100}", value):
        raise TeamError("ID model tidak valid; gunakan ID langsung dari provider.")
    return value


def ask_secret(label):
    value = getpass.getpass(label + ": ").strip()
    if not re.fullmatch(r"[A-Za-z0-9._:-]{20,}", value):
        raise TeamError("Format kredensial tidak valid. Masukkan langsung dari konsol provider.")
    return value


def check_models(openai_key, gemini_key, codex_model, gemini_model):
    oa = api_json("https://api.openai.com/v1/models/" + model_id(codex_model),
                  "OpenAI", headers={"Authorization": "Bearer " + openai_key})
    gm = api_json("https://generativelanguage.googleapis.com/v1beta/models/" + model_id(gemini_model),
                  "Gemini", headers={"x-goog-api-key": gemini_key})
    if oa.get("id") != codex_model or "generateContent" not in gm.get("supportedGenerationMethods", []):
        raise TeamError("Model yang dipilih tidak lolos pemeriksaan metadata provider.")
    print("Akses metadata OpenAI dan Gemini valid. Inference/billing diuji melalui chat setelah aktif.")


def telegram(token, method, body=None):
    response = api_json(f"https://api.telegram.org/bot{token}/{method}", "Telegram", body=body or {})
    if not response.get("ok"):
        raise TeamError("Telegram menolak permintaan. Periksa token dan status bot di VPS.")
    return response["result"]


def reject_reused_bot(token):
    roots = {Path.home() / ".hermes"}
    if os.environ.get("HERMES_HOME"):
        roots.add(Path(os.environ["HERMES_HOME"]).expanduser())
    for root in roots:
        for path in [root / ".env", *root.glob("profiles/*/.env")]:
            if path.is_file() and token in path.read_text(encoding="utf-8"):
                raise TeamError("Token bot ditemukan pada Hermes lama. Buat bot khusus Media melalui BotFather.")


def pair_bot(token):
    if not re.fullmatch(r"[0-9]{5,}:[A-Za-z0-9_-]{20,}", token):
        raise TeamError("Format token Telegram tidak valid.")
    reject_reused_bot(token)
    bot = telegram(token, "getMe")
    if not bot.get("is_bot") or not bot.get("username"):
        raise TeamError("Token bukan milik bot Telegram yang valid.")
    if telegram(token, "getWebhookInfo").get("url"):
        raise TeamError("Bot mempunyai webhook aktif. Gunakan bot baru agar integrasi lama tetap berjalan.")
    challenge = "MEDIA-" + secrets.token_hex(8)
    print(f"Buka https://t.me/{bot['username']} lalu kirim pesan privat berikut:")
    print(challenge)
    for _ in range(3):
        input("Tekan Enter setelah pesan dikirim: ")
        updates = telegram(token, "getUpdates", {"timeout": 0, "allowed_updates": ["message"]})
        user_id = paired_user(updates, challenge)
        if user_id:
            print(f"Pemilik terverifikasi: Telegram user ID {user_id} (akses privat saja).")
            return str(user_id), bot["username"]
        print("Pesan verifikasi belum ditemukan. Kirim teks persis melalui chat privat bot.")
    raise TeamError("Verifikasi pemilik belum berhasil; tidak ada gateway yang dinyalakan.")


def paired_user(updates, challenge):
    for update in updates:
        message = update.get("message", {})
        sender, chat = message.get("from", {}), message.get("chat", {})
        identity = sender.get("id")
        if (message.get("text", "").strip() == challenge and chat.get("type") == "private"
                and isinstance(identity, int) and identity > 0
                and chat.get("id") == identity and not sender.get("is_bot", True)):
            return identity
    return None


def profile_config(role, codex_model, gemini_model, owner):
    google = role in ("uiux", "qa")
    pm = role == "pm"
    tools = ["kanban", "memory", "todo"] if pm else ["terminal", "file", "kanban", "todo"]
    if role in ("uiux", "qa"):
        tools.append("browser")
    return {
        "model": {"default": gemini_model if google else codex_model,
                  "provider": "gemini" if google else "openai-api",
                  "base_url": ("https://generativelanguage.googleapis.com/v1beta" if google
                               else "https://api.openai.com/v1")},
        "agent": {"max_turns": 40, "reasoning_effort": "medium",
                  "disabled_toolsets": ["delegation"]},
        # '.' is essential: worker terminal must follow its assigned worktree.
        "terminal": {"backend": "local", "cwd": ".", "timeout": 180},
        "platform_toolsets": {"cli": tools, "telegram": tools if pm else []},
        "security": {"redact_secrets": True},
        "gateway": {"multiplex_profiles": False},
        "platforms": {**{name: {"enabled": False} for name in OTHER_PLATFORMS},
                      "telegram": {"enabled": pm, "guest_mode": False, "extra": {
            "dm_policy": "allowlist", "allow_from": [owner] if pm else [],
            "allow_admin_from": [owner] if pm else [], "group_policy": "disabled",
            "group_allow_from": [], "group_allow_admin_from": [],
            "drop_pending_on_cold_boot": True}}},
        "kanban": {"dispatch_in_gateway": pm, "notify_in_gateway": pm,
                   "auto_decompose": False, "auto_subscribe_on_create": True,
                   "dispatch_interval_seconds": 15, "max_in_progress": 2,
                   "max_in_progress_per_profile": 1, "failure_limit": 2,
                   "dispatch_profiles": ["media-" + r for r in ROLES if r != "pm"] if pm else []},
    }


def profile_env(role, root, credentials, owner):
    values = {"HERMES_KANBAN_HOME": str(root), "HERMES_KANBAN_BOARD": BOARD,
              "HERMES_REDACT_SECRETS": "true", "GATEWAY_ALLOW_ALL_USERS": "false",
              "GATEWAY_ALLOWED_USERS": "", "TELEGRAM_ALLOW_ALL_USERS": "false",
              "TELEGRAM_ALLOW_BOTS": "false", "TELEGRAM_GROUP_ALLOWED_USERS": "",
              "TELEGRAM_GROUP_ALLOWED_CHATS": ""}
    if role in ("uiux", "qa"):
        values["GOOGLE_API_KEY"] = credentials["gemini"]
    else:
        values["OPENAI_API_KEY"] = credentials["openai"]
    values["TELEGRAM_BOT_TOKEN"] = credentials["telegram"] if role == "pm" else ""
    values["TELEGRAM_ALLOWED_USERS"] = owner if role == "pm" else ""
    return "".join(f"{key}={json.dumps(value)}\n" for key, value in values.items())


def render_soul(repo, role, state):
    roles = repo / "hermes" / "roles"
    text = (roles / "common.md").read_text() + "\n\n" + (roles / f"{role}.md").read_text()
    for name, value in {"DEPLOY_REPO": state["deploy_repo"], "WORKSPACE": state["workspace"],
                        "DATA_DIR": state["data_dir"]}.items():
        text = text.replace("@@" + name + "@@", value)
    google = role in ("uiux", "qa")
    return text + f"\nKonfigurasi awal: provider {'gemini' if google else 'openai-api'}, model " + (
        state["gemini_model"] if google else state["codex_model"]) + ".\n"


def unit_text(data_dir):
    if any(ord(c) < 32 for c in str(data_dir)):
        raise TeamError("Path data tidak boleh mengandung karakter kontrol.")
    def quote(value):
        # systemd expands %, even inside quotes.
        return json.dumps(str(value).replace("%", "%%"))
    return ("# Managed by Media Keycloud Hermes Team\n[Unit]\n"
            "Description=Media Keycloud Hermes PM and Telegram\nAfter=network-online.target\n"
            "Wants=network-online.target\nStartLimitIntervalSec=300\nStartLimitBurst=5\n\n"
            "[Service]\nType=simple\n"
            f"WorkingDirectory={str(data_dir).replace('%', '%%')}\n"
            f"ExecStart=/usr/bin/python3 {quote(data_dir / 'control.py')} --data-dir "
            f"{quote(data_dir)} _gateway\n"
            "Restart=on-failure\nRestartSec=10\nTimeoutStopSec=45\nKillMode=control-group\n"
            "UMask=0077\nEnvironment=PYTHONUNBUFFERED=1\n\n[Install]\nWantedBy=default.target\n")


def unit_path():
    return Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))) / "systemd/user" / SERVICE


def capabilities(hermes, root):
    env = isolated_env(root)
    checks = [(["profile", "create", "--help"], ["--no-alias", "--description"]),
              (["kanban", "boards", "create", "--help"], ["--default-workdir"]),
              (["kanban", "create", "--help"], ["--workspace", "--max-runtime"]),
              (["gateway", "run", "--help"], ["--external-supervisor"])]
    for args, expected in checks:
        try:
            output = run([hermes, *args], env=env, cwd=root)
            if not all(flag in output for flag in expected):
                raise TeamError("Fitur Hermes belum tersedia.")
        except TeamError:
            raise TeamError("Hermes ini belum lolos pemeriksaan profiles/Kanban/gateway. "
                            "Periksa `hermes --help` dan `hermes update`, lalu ulangi. "
                            "Installer tidak memperbarui Hermes lama secara otomatis.") from None


def install_profiles(repo, state, credentials):
    root = Path(state["root"])
    env = isolated_env(root)
    for role, (label, description) in ROLES.items():
        name = "media-" + role
        profile = root / "profiles" / name
        if profile.exists():
            raise TeamError(f"Profil {name} sudah ada; tidak ditimpa.")
        run([state["hermes"], "profile", "create", name, "--no-alias",
             "--description", description], env=env, cwd=root, timeout=180)
        if not profile.is_dir():
            raise TeamError("Versi Hermes tidak menempatkan profil pada home tim. Hentikan setup.")
        os.chmod(profile, 0o700)
        write_json(profile / "config.yaml", profile_config(role, state["codex_model"],
                                                           state["gemini_model"], state["owner"]))
        write_private(profile / ".env", profile_env(role, root, credentials, state["owner"]))
        write_private(profile / "SOUL.md", render_soul(repo, role, state))
        print(f"Profil {name} ({label}) siap.")


def read_env(path):
    # Files generated here have JSON-quoted values. Never source them in a shell.
    result = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line and not line.startswith("#"):
            key, value = line.split("=", 1)
            result[key] = json.loads(value)
    return result


def read_state(data_dir):
    try:
        state = json.loads((data_dir / "team.json").read_text())
    except (OSError, ValueError):
        raise TeamError("Tim belum selesai diinstal. Jalankan setup dari repository.") from None
    if state.get("schema") != 1 or state.get("data_dir") != str(data_dir):
        raise TeamError("Manifest tim tidak cocok dengan direktori ini.")
    return state


def check_team(state, *, live=True):
    root = Path(state["root"])
    pm = read_env(root / "profiles/media-pm/.env")
    ui = read_env(root / "profiles/media-uiux/.env")
    credentials = {"openai": pm.get("OPENAI_API_KEY", ""), "gemini": ui.get("GOOGLE_API_KEY", ""),
                   "telegram": pm.get("TELEGRAM_BOT_TOKEN", "")}
    if not all(credentials.values()) or not re.fullmatch(r"[1-9][0-9]*", state["owner"]):
        raise TeamError("Kredensial/pemilik pada profil tidak lengkap.")
    for role in ROLES:
        profile = root / "profiles" / ("media-" + role)
        for filename in (".env", "config.yaml", "SOUL.md"):
            path = profile / filename
            if not path.is_file() or path.is_symlink() or path.stat().st_mode & 0o077:
                raise TeamError(f"File profil media-{role}/{filename} hilang atau izin bukan privat.")
        cfg = json.loads((profile / "config.yaml").read_text())
        env = read_env(profile / ".env")
        expected = profile_config(role, state["codex_model"], state["gemini_model"], state["owner"])
        if cfg != expected:
            raise TeamError(f"Konfigurasi media-{role} berubah dari manifest. Tinjau di VPS sebelum mulai.")
        expected_env = dict(line.split("=", 1) for line in profile_env(
            role, root, credentials, state["owner"]).splitlines())
        if env != {key: json.loads(value) for key, value in expected_env.items()}:
            raise TeamError(f"Kredensial/allowlist media-{role} tidak cocok dengan konfigurasi tim.")
    if live:
        check_models(pm["OPENAI_API_KEY"], ui["GOOGLE_API_KEY"],
                     state["codex_model"], state["gemini_model"])
        bot = telegram(pm["TELEGRAM_BOT_TOKEN"], "getMe")
        if bot.get("username") != state["bot_username"]:
            raise TeamError("Identitas bot berbeda dari manifest pemasangan.")
        if telegram(pm["TELEGRAM_BOT_TOKEN"], "getWebhookInfo").get("url"):
            raise TeamError("Webhook aktif; gateway polling tidak boleh dinyalakan.")
    print("Enam profil, perutean provider, izin file, dan allowlist lolos pemeriksaan.")


def setup(args, data_dir):
    if not sys.stdin.isatty():
        raise TeamError("Setup harus dijalankan pada terminal SSH interaktif; jangan pipe kredensial.")
    repo = Path(__file__).resolve().parent.parent
    if not (repo / "hermes/roles/common.md").is_file():
        raise TeamError("Jalankan setup dari scripts/hermes-team.py di repository.")
    if data_dir.exists() or unit_path().exists():
        raise TeamError("Direktori tim atau unit media-hermes sudah ada; tidak ditimpa. "
                        "Gunakan status/start. Lihat docs/HERMES.md untuk instalasi parsial.")
    hermes = shutil.which("hermes")
    if not hermes:
        raise TeamError("Perintah hermes belum ada di PATH user ini. Aktifkan PATH instalasi Hermes.")
    if run(["git", "remote", "get-url", "origin"], cwd=repo).rstrip("/") not in (
            REPO_URL, REPO_URL.removesuffix(".git"), "git@github.com:sirMisato/Media-keycloud.git"):
        raise TeamError("Origin repository tidak cocok dengan Media-keycloud milik sirMisato.")
    if not args.no_start:
        assert_linger()
    # Capability probing is confined to a temporary Hermes home, not the old one.
    with tempfile.TemporaryDirectory(prefix="media-hermes-preflight-") as temp:
        capabilities(hermes, Path(temp))
    print("Gunakan kunci BARU yang sudah dirotasi, serta bot Telegram khusus Media.")
    codex = model_id(input(f"Model Codex [{DEFAULT_CODEX}]: ").strip() or DEFAULT_CODEX)
    gemini = model_id(input(f"Model Gemini [{DEFAULT_GEMINI}]: ").strip() or DEFAULT_GEMINI)
    credentials = {"openai": ask_secret("OpenAI API key baru"),
                   "gemini": ask_secret("Gemini API key baru")}
    check_models(credentials["openai"], credentials["gemini"], codex, gemini)
    credentials["telegram"] = ask_secret("Token bot Telegram dari BotFather")
    owner, username = pair_bot(credentials["telegram"])
    state = {"schema": 1, "data_dir": str(data_dir), "root": str(data_dir / "hermes"),
             "workspace": str(data_dir / "workspace"), "deploy_repo": str(repo),
             "hermes": hermes, "codex_model": codex, "gemini_model": gemini,
             "owner": owner, "bot_username": username}
    data_dir.mkdir(parents=True, mode=0o700)
    write_json(data_dir / "installing.json", {"schema": 1, "deploy_repo": str(repo)})
    root, workspace = Path(state["root"]), Path(state["workspace"])
    root.mkdir(mode=0o700)
    # An inert default profile prevents an accidentally started default dispatcher.
    write_json(root / "config.yaml", {"kanban": {"dispatch_in_gateway": False},
                                      "gateway": {"multiplex_profiles": False}})
    write_private(root / ".env", "HERMES_REDACT_SECRETS=true\n")
    run(["git", "clone", "--no-hardlinks", str(repo), str(workspace)], timeout=180)
    run(["git", "remote", "set-url", "origin", REPO_URL], cwd=workspace)
    run(["git", "checkout", "-b", "media-integration"], cwd=workspace)
    run(["git", "config", "user.name", "Media Hermes"], cwd=workspace)
    run(["git", "config", "user.email", "media-hermes@users.noreply.github.com"], cwd=workspace)
    with (workspace / ".git/info/exclude").open("a") as handle:
        handle.write("\n/.worktrees/\n")
    install_profiles(repo, state, credentials)
    run([hermes, "-p", "media-pm", "kanban", "boards", "create", BOARD,
         "--name", "Media Ma'had Aly Situbondo", "--default-workdir", str(workspace)],
        env=isolated_env(root), cwd=workspace)
    write_private(data_dir / "control.py", Path(__file__).read_text())
    write_private(unit_path(), unit_text(data_dir))
    write_json(data_dir / "team.json", state)
    (data_dir / "installing.json").unlink()
    check_team(state, live=False)
    if args.no_start:
        print("Konfigurasi siap; gateway belum aktif. Jalankan perintah start setelah linger tersedia.")
    else:
        run(["systemctl", "--user", "daemon-reload"], env=user_bus_env())
        run(["systemctl", "--user", "enable", "--now", SERVICE], env=user_bus_env())
        control("is-active")
        print(f"Service aktif. Buka https://t.me/{username} dan kirim: status tim")
        print("Lanjutkan: smoke test enam profil, tanpa mengubah kode atau deploy.")
    print("Logika agen memakai hak user saat ini; installer tidak menambah akses sudo/Docker.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path.home() / ".local/share/media-keycloud")
    parser.add_argument("command", choices=["setup", "check", "status", "start", "stop", "restart",
                                             "logs", "board", "profiles", "rotate-keys", "_gateway"])
    parser.add_argument("--no-start", action="store_true", help="setup saja: siapkan tanpa menyalakan bot")
    parser.add_argument("--offline", action="store_true", help="check saja: tanpa akses provider/Telegram")
    args = parser.parse_args()
    if os.geteuid() == 0:
        raise TeamError("Jalankan sebagai user pemilik Hermes (misalnya ubuntu), tanpa sudo.")
    data_dir = args.data_dir.expanduser().resolve()
    if args.command == "setup":
        # Serialize installers, without creating the final directory before preflight.
        lock_dir = Path.home() / ".cache/media-keycloud"
        lock_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        with (lock_dir / "setup.lock").open("w") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            setup(args, data_dir)
        return
    state = read_state(data_dir)
    env = isolated_env(Path(state["root"]))
    cmd = args.command
    if cmd == "_gateway":
        check_team(state, live=False)
        os.chdir(state["workspace"])
        os.execve(state["hermes"], [state["hermes"], "-p", "media-pm", "gateway", "run",
                                    "--external-supervisor"], env)
    elif cmd == "check":
        check_team(state, live=not args.offline)
    elif cmd in ("start", "restart"):
        assert_linger()
        check_team(state)
        run(["systemctl", "--user", "daemon-reload"], env=user_bus_env())
        run(["systemctl", "--user", "enable", SERVICE], env=user_bus_env())
        print(control(cmd))
        print(control("is-active"))
    elif cmd == "stop":
        print(control("stop"))
        print("Gateway/dispatcher dihentikan. Worker Kanban yang sedang berjalan dapat tetap hidup;")
        print("lihat docs/HERMES.md untuk membatalkan task dan menghentikan seluruh tim.")
    elif cmd == "status":
        check_team(state, live=False)
        print(control("is-active"))
        print(f"Telegram: https://t.me/{state['bot_username']}")
        print(f"Board: {BOARD}; dua worker maksimal, satu per profil.")
    elif cmd == "logs":
        os.execvpe("journalctl", ["journalctl", "--user", "-u", SERVICE, "-n", "80", "--no-pager"], user_bus_env())
    elif cmd in ("board", "profiles"):
        tail = ["kanban", "--board", BOARD, "list"] if cmd == "board" else ["profile", "list"]
        print(run([state["hermes"], "-p", "media-pm", *tail], env=env, cwd=state["workspace"]))
    elif cmd == "rotate-keys":
        if not sys.stdin.isatty():
            raise TeamError("Rotasi harus lewat terminal interaktif.")
        credentials = {"openai": ask_secret("OpenAI API key baru"), "gemini": ask_secret("Gemini API key baru")}
        check_models(credentials["openai"], credentials["gemini"], state["codex_model"], state["gemini_model"])
        # Do not copy old keys into backup files. Running workers retain their old
        # environment: operator should drain/stop tasks before rotation.
        for role in ROLES:
            path = Path(state["root"]) / "profiles" / ("media-" + role) / ".env"
            current = read_env(path)
            key = "GOOGLE_API_KEY" if role in ("uiux", "qa") else "OPENAI_API_KEY"
            current[key] = credentials["gemini" if role in ("uiux", "qa") else "openai"]
            write_private(path, "".join(f"{k}={json.dumps(v)}\n" for k, v in current.items()))
        print("Key diganti. Jalankan restart; worker lama perlu diselesaikan/dihentikan sebelum memakai key baru.")


if __name__ == "__main__":
    try:
        main()
    except (TeamError, OSError, ValueError, KeyError) as error:
        # Unknown OS/JSON errors can include sensitive paths/values; keep generic.
        print("GAGAL: " + (str(error) if isinstance(error, TeamError) else
                           "Operasi lokal gagal. Periksa izin/path, manifest, atau proses setup lain."), file=sys.stderr)
        sys.exit(1)
    except (KeyboardInterrupt, EOFError):
        print("Dibatalkan. Konfigurasi Hermes lama tetap terpisah.", file=sys.stderr)
        sys.exit(130)
