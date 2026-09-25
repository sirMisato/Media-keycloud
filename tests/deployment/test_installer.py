"""Check installer orchestration in a disposable checkout with isolated command stubs."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]

STUB = r'''#!/bin/bash
program=${0##*/}
printf '%s %s\n' "$program" "$*" >> "$TEST_COMMAND_LOG"
case "$program" in
  ss)
    if [[ "$*" == *':80 '* ]]; then
      printf 'LISTEN 0 4096 *:80 *:* users:(("%s",pid=1005,fd=6))\n' "${TEST_PROXY_OWNER:-caddy}"
    fi
    ;;
  apt-get)
    if [[ "$*" == *'docker.io'* ]]; then
      /bin/cp "$0" "${0%/*}/docker"
      /bin/chmod +x "${0%/*}/docker"
    fi
    ;;
  python3)
    if [[ "$*" == *'scripts/init-env.py'* ]]; then
      /bin/mkdir -p .deploy
      : > .deploy/prod.env
      : > .deploy/dev.env
    fi
    ;;
  git) printf 'testcommit\n' ;;
esac
'''


class InstallerOrchestration(unittest.TestCase):
    def setUp(self):
        if os.geteuid() != 0:
            self.skipTest("Installer root check requires sudo for this isolated orchestration test")
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        shutil.copytree(ROOT / "scripts", self.root / "scripts")
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.log = self.root / "commands.log"
        for name in ("ss", "apt-get", "systemctl", "python3", "git", "caddy"):
            executable = self.bin / name
            executable.write_text(STUB)
            executable.chmod(0o755)
        for name in ("dirname", "grep"):
            (self.bin / name).symlink_to(shutil.which(name))
        (self.bin / "bash").symlink_to("/bin/bash")
        self.env = dict(os.environ, PATH=str(self.bin), TEST_COMMAND_LOG=str(self.log))

    def run_installer(self, *args):
        return subprocess.run(["/bin/bash", "scripts/install-vps.sh", *args], cwd=self.root, env=self.env, input="admin@example.test\n", text=True, capture_output=True)

    def test_existing_caddy_installs_missing_docker_and_leaves_caddy_hermes_services(self):
        for arguments in ((), ("--proxy=caddy",)):
            with self.subTest(arguments=arguments):
                shutil.rmtree(self.root / ".deploy", ignore_errors=True)
                (self.bin / "docker").unlink(missing_ok=True)
                self.log.unlink(missing_ok=True)
                result = self.run_installer(*arguments)
                self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
                log = self.log.read_text()
                self.assertIn("apt-get install -y docker.io docker-compose-v2", log)
                self.assertIn("configure-caddy.py --config /etc/caddy/Caddyfile --check", log)
                self.assertNotIn("nginx", log)
                self.assertNotIn("certbot", log)
                self.assertNotIn("hermes", log)
                self.assertNotIn("systemctl stop", log)
                self.assertNotIn("systemctl restart", log)
                self.assertNotIn("systemctl enable --now caddy", log)

    def test_other_web_server_is_reported_before_installing_anything(self):
        self.env["TEST_PROXY_OWNER"] = "apache2"
        result = self.run_installer("--proxy=caddy")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("apache2", result.stderr)
        self.assertNotIn("apt-get", self.log.read_text())
        self.assertFalse((self.root / ".deploy").exists())


if __name__ == "__main__":
    unittest.main()
