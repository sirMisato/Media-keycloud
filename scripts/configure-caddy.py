#!/usr/bin/env python3
"""Add media routes to an existing Caddyfile, preserving and validating its contents."""
import argparse
import getpass
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request

DOMAINS = {"media.keycloud.id", "media-dev.keycloud.id"}
MARKER = "# Managed by Media-keycloud: Caddy routes v1"


class SetupError(RuntimeError):
    pass


class CaddySetup:
    def __init__(self, config, backup_dir, env=None):
        self.config = Path(config).resolve(strict=True)
        self.snippet = self.config.parent / "media-keycloud.caddy"
        self.backup_dir = Path(backup_dir)
        self.env = env

    def command(self, *args, input=None):
        result = subprocess.run(args, input=input, text=True, capture_output=True, env=self.env)
        if result.returncode:
            raise SetupError(f"{args[0]} {args[1]} gagal: {result.stderr.strip()}")
        return result.stdout

    def adapt(self):
        return json.loads(self.command("caddy", "adapt", "--config", str(self.config), "--adapter", "caddyfile"))

    def validate(self):
        self.command("caddy", "validate", "--config", str(self.config), "--adapter", "caddyfile")

    def reload(self):
        self.command("caddy", "reload", "--config", str(self.config), "--adapter", "caddyfile")

    @staticmethod
    def hosts(value):
        hosts = set()
        if isinstance(value, dict):
            for key, child in value.items():
                if key == "host" and isinstance(child, list):
                    hosts.update(h.lower() for h in child if isinstance(h, str))
                hosts.update(CaddySetup.hosts(child))
        elif isinstance(value, list):
            for child in value:
                hosts.update(CaddySetup.hosts(child))
        return hosts

    def runtime(self, config):
        admin = config.get("admin", {})
        address = admin.get("listen", (self.env or os.environ).get("CADDY_ADMIN", "localhost:2019"))
        parsed = urllib.parse.urlsplit("http://" + address)
        if admin.get("disabled") or parsed.hostname not in {"localhost", "127.0.0.1", "::1"} or parsed.path:
            raise SetupError("Admin Caddy memakai konfigurasi khusus. Gunakan integrasi manual di docs/CADDY.md.")
        # Never send a local admin request through an HTTP proxy configured in the shell.
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        try:
            with opener.open("http://" + address + "/config/", timeout=5) as response:
                return json.load(response)
        except (OSError, ValueError) as error:
            raise SetupError("Konfigurasi Caddy aktif tidak dapat diperiksa. Lihat docs/CADDY.md.") from error

    def check(self):
        current = self.adapt()
        if self.runtime(current) != current:
            raise SetupError("Konfigurasi Caddy aktif berbeda dari Caddyfile. Sinkronkan melalui pengelola Caddy sebelum instalasi; tidak ada konfigurasi yang ditimpa.")
        self.validate()
        existing = self.hosts(current) & DOMAINS
        if self.snippet.exists():
            if self.snippet.is_symlink() or not self.snippet.read_text().startswith(MARKER):
                raise SetupError(f"File {self.snippet} sudah ada dan bukan milik installer.")
            if existing == DOMAINS:
                return current, True
            raise SetupError("Konfigurasi media Caddy belum lengkap. Periksa import di Caddyfile; lihat docs/CADDY.md.")
        if existing:
            raise SetupError("Domain media sudah dikonfigurasi di Caddy. Integrasikan manual tanpa menimpa rute yang ada.")
        return current, False

    def render(self, password_hash):
        version = self.command("caddy", "version")
        match = re.search(r"v?(\d+)\.(\d+)\.(\d+)", version)
        if not match or int(match[1]) != 2:
            raise SetupError("Installer memerlukan Caddy 2 dengan versi yang dapat dikenali.")
        auth = "basic_auth" if int(match[2]) >= 8 else "basicauth"
        return f'''{MARKER}
media.keycloud.id {{
    encode gzip
    request_body {{
        max_size 8MB
    }}
    reverse_proxy 127.0.0.1:8081
}}

media-dev.keycloud.id {{
    header X-Robots-Tag "noindex, nofollow"
    {auth} {{
        reviewer {password_hash}
    }}
    encode gzip
    request_body {{
        max_size 8MB
    }}
    reverse_proxy 127.0.0.1:8082
}}
'''

    def apply(self, password_reader=getpass.getpass):
        current, installed = self.check()
        if installed:
            print("Rute media sudah aktif di Caddy; password dan konfigurasi dipertahankan.")
            return
        password = password_reader("Password Basic Auth development (reviewer), 12–72 byte: ")
        if not 12 <= len(password.encode()) <= 72 or "\n" in password or "\r" in password:
            raise SetupError("Password harus sepanjang 12–72 byte tanpa baris baru.")
        if password != password_reader("Ulangi password Basic Auth: "):
            raise SetupError("Password tidak sama.")
        password_hash = self.command("caddy", "hash-password", "--algorithm", "bcrypt", input=password).strip()
        del password
        if not re.fullmatch(r"\$2[aby]\$\d\d\$[./A-Za-z0-9]{53}", password_hash):
            raise SetupError("Caddy tidak menghasilkan hash bcrypt yang valid.")
        snippet_content = self.render(password_hash)
        if self.adapt() != current or self.runtime(current) != current:
            raise SetupError("Konfigurasi Caddy berubah saat memasukkan password. Ulangi tanpa menimpa perubahan tersebut.")
        original = self.config.read_bytes()
        self.backup_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        backup = Path(tempfile.mkdtemp(prefix="caddy-", dir=self.backup_dir))
        shutil.copy2(self.config, backup / "Caddyfile")
        expected = original
        snippet_created = False
        try:
            with self.snippet.open("x") as target:
                snippet_created = True
                target.write(snippet_content)
            self.snippet.chmod(0o644)
            included = self.hosts(self.adapt()) & DOMAINS
            if not included:
                expected = original + f'\n# Media-keycloud\nimport "{self.snippet}"\n'.encode()
                self.config.write_bytes(expected)
            elif included != DOMAINS:
                raise SetupError("Import Caddy hanya memuat sebagian rute media.")
            self.validate()
            if self.runtime(current) != current:
                raise SetupError("Konfigurasi Caddy aktif berubah; pemasangan dibatalkan.")
            self.reload()
        except BaseException:
            if self.config.read_bytes() == expected:
                self.config.write_bytes(original)
            else:
                print(f"Caddyfile berubah dari proses lain; periksa backup {backup}.", file=sys.stderr)
            if snippet_created:
                self.snippet.unlink(missing_ok=True)
            # Caddy retains its running configuration when a reload is rejected.
            print(f"Pemasangan Caddy gagal; backup tersedia di {backup}.", file=sys.stderr)
            raise
        print(f"Caddy berhasil di-reload. Backup konfigurasi: {backup}")
        print("HTTPS diterbitkan otomatis oleh Caddy setelah DNS dan port 80/443 sesuai.")


def service_environment(config):
    """Only automate a running, file-managed systemd service, never an API/resume setup."""
    subprocess.run(["systemctl", "is-active", "--quiet", "caddy"], check=True)
    pid = subprocess.check_output(["systemctl", "show", "caddy", "--property=MainPID", "--value"], text=True).strip()
    if not pid.isdigit() or int(pid) <= 0:
        raise SetupError("PID layanan Caddy tidak ditemukan.")
    args = Path(f"/proc/{pid}/cmdline").read_bytes().decode().strip("\0").split("\0")

    def option(name):
        for index, arg in enumerate(args):
            if arg == name and index + 1 < len(args):
                return args[index + 1]
            if arg.startswith(name + "="):
                return arg.split("=", 1)[1]
        return None

    configured = option("--config") or option("-c")
    if any(arg == "--resume" or arg.startswith("--resume=") for arg in args) or not configured:
        raise SetupError("Caddy tidak memakai alur Caddyfile standar. Gunakan panduan manual docs/CADDY.md.")
    if Path(configured).resolve() != Path(config).resolve() or option("--adapter") not in {None, "caddyfile"}:
        raise SetupError("Path/adapter layanan Caddy berbeda. Periksa systemctl cat caddy dan gunakan --caddy-config=/path/Caddyfile.")
    environment = dict(os.environ)
    for item in Path(f"/proc/{pid}/environ").read_bytes().split(b"\0"):
        if b"=" in item:
            key, value = item.split(b"=", 1)
            environment[os.fsdecode(key)] = os.fsdecode(value)
    return environment


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="/etc/caddy/Caddyfile")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if os.geteuid() != 0:
        raise SetupError("Jalankan dengan sudo.")
    environment = service_environment(args.config)
    setup = CaddySetup(args.config, "/var/backups/mahad-media", environment)
    if args.check:
        setup.check()
        print("Caddy aktif, Caddyfile sesuai, dan konfigurasi dapat diintegrasikan.")
    else:
        setup.apply()


if __name__ == "__main__":
    def interrupted(_signum, _frame):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, interrupted)
    try:
        main()
    except (SetupError, OSError, subprocess.CalledProcessError, ValueError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("Pemasangan Caddy dibatalkan.", file=sys.stderr)
        sys.exit(130)
