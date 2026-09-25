"""Exercise real Caddy adaptation/reload while keeping test sites on local high ports."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
import time
import unittest
from unittest.mock import patch
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("configure_caddy", ROOT / "scripts/configure-caddy.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def free_port():
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return listener.getsockname()[1]


class CaddyIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which("caddy"):
            raise RuntimeError("Install Caddy before running deployment integration tests.")

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.config = self.root / "Caddyfile"
        self.admin_port, self.http_port, self.https_port = free_port(), free_port(), free_port()
        self.original = f'''{{
    admin 127.0.0.1:{self.admin_port}
    auto_https off
    http_port {self.http_port}
    https_port {self.https_port}
}}
# Existing site must remain available after installation.
http://existing.example:{self.http_port} {{
    respond "existing-site-ok"
}}
'''
        self.config.write_text(self.original)
        self.env = dict(os.environ, XDG_DATA_HOME=str(self.root / "data"), XDG_CONFIG_HOME=str(self.root / "config"))
        self.setup = module.CaddySetup(self.config, self.root / "backups", self.env)
        self.log = (self.root / "caddy.log").open("w")
        self.addCleanup(self.log.close)
        self.process = subprocess.Popen(["caddy", "run", "--config", str(self.config), "--adapter", "caddyfile"], stdout=self.log, stderr=self.log, env=self.env)
        self.addCleanup(self.stop)
        for _ in range(100):
            try:
                self.assert_existing_site()
                return
            except (OSError, AssertionError):
                if self.process.poll() is not None:
                    self.fail((self.root / "caddy.log").read_text())
                time.sleep(0.05)
        self.fail("Test Caddy did not start.")

    def stop(self):
        self.process.terminate()
        self.process.wait(timeout=10)

    def assert_existing_site(self):
        request = urllib.request.Request(f"http://127.0.0.1:{self.http_port}/", headers={"Host": "existing.example"})
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(request, timeout=2) as response:
            self.assertEqual(response.read(), b"existing-site-ok")
        self.assertIsNone(self.process.poll())

    @staticmethod
    def password(_prompt):
        return "Deployment-test-password-2026"

    def assert_untouched(self):
        self.assertEqual(self.config.read_text(), self.original)
        self.assertFalse(self.setup.snippet.exists())
        self.assert_existing_site()

    def test_install_keeps_existing_site_and_is_idempotent(self):
        self.setup.apply(self.password)
        self.assertTrue(self.config.read_text().startswith(self.original))
        self.assert_existing_site()
        config = self.setup.adapt()
        self.assertEqual(config, self.setup.runtime(config))
        self.assertTrue(module.DOMAINS <= self.setup.hosts(config))
        serialized = json.dumps(config)
        for expected in ("127.0.0.1:8081", "127.0.0.1:8082", "authentication", "reviewer", "noindex, nofollow"):
            self.assertIn(expected, serialized)
        self.assertNotIn(self.password(""), self.setup.snippet.read_text())
        backup = next((self.root / "backups").glob("caddy-*/Caddyfile"))
        self.assertEqual(backup.read_text(), self.original)
        installed = self.config.read_bytes()
        self.setup.apply(lambda _: self.fail("Repeated installation must not replace passwords"))
        self.assertEqual(self.config.read_bytes(), installed)

    def test_existing_wildcard_import_does_not_get_duplicate_import(self):
        self.original += "\nimport *.caddy\n"
        self.config.write_text(self.original)
        self.setup.reload()
        self.setup.apply(self.password)
        self.assertEqual(self.config.read_text(), self.original)
        self.assert_existing_site()

    def test_existing_media_domain_is_not_overwritten(self):
        self.original += f'\nhttp://media.keycloud.id:{self.http_port} {{\n respond "old-media"\n}}\n'
        self.config.write_text(self.original)
        self.setup.reload()
        with self.assertRaisesRegex(module.SetupError, "Domain media sudah"):
            self.setup.apply(self.password)
        self.assert_untouched()

    def test_runtime_file_difference_blocks_install(self):
        changed = self.original.replace("existing-site-ok", "unapplied-file-change")
        self.config.write_text(changed)
        with self.assertRaisesRegex(module.SetupError, "aktif berbeda"):
            self.setup.apply(self.password)
        self.assertEqual(self.config.read_text(), changed)
        self.assertFalse(self.setup.snippet.exists())
        self.assert_existing_site()

    def test_invalid_new_config_restores_files_without_reload(self):
        render = self.setup.render
        with patch.object(self.setup, "render", side_effect=lambda hashed: render(hashed) + "\nmedia-broken.invalid {\n unknown_directive_here\n}\n"), patch.object(self.setup, "reload") as reload:
            with self.assertRaises(module.SetupError):
                self.setup.apply(self.password)
            reload.assert_not_called()
        self.assert_untouched()

    def test_failed_reload_restores_files_and_keeps_running_site(self):
        with patch.object(self.setup, "reload", side_effect=module.SetupError("reload rejected")):
            with self.assertRaisesRegex(module.SetupError, "reload rejected"):
                self.setup.apply(self.password)
        self.assert_untouched()


if __name__ == "__main__":
    unittest.main()
