"""Offline regressions for real installer behavior; all credentials are fixtures."""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest import mock
import urllib.error

REPO = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("team", REPO / "scripts/hermes-team.py")
team = importlib.util.module_from_spec(spec)
spec.loader.exec_module(team)
CREDS = {"openai": "TEST_ONLY_OPENAI_VALUE_FOR_OFFLINE_TESTS_123",
         "gemini": "TEST_ONLY_GEMINI_VALUE_FOR_OFFLINE_TESTS_456",
         "telegram": "123456789:OFFLINE_FIXTURE_abcdefghijklmnopqrstuvwxyz"}


def make_state(base, hermes):
    return {"schema": 1, "data_dir": str(base), "root": str(base / "hermes"),
            "workspace": str(base / "workspace"), "deploy_repo": str(REPO),
            "hermes": str(hermes), "codex_model": team.DEFAULT_CODEX,
            "gemini_model": team.DEFAULT_GEMINI, "owner": "7654321",
            "bot_username": "offline_fixture_bot"}


def init_repo(path):
    path.mkdir(parents=True)
    team.run(["git", "init", "-b", "main", str(path)])
    (path / "README.md").write_text("Offline fixture repository\n")
    team.run(["git", "add", "README.md"], cwd=path)
    team.run(["git", "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
              "commit", "-m", "Fixture"], cwd=path)


class TeamTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.fake = self.base / "fake-hermes"
        self.fake.write_text("""#!/usr/bin/env python3
import os, pathlib, sys
args=sys.argv[1:]
if args[:2] == ['profile', 'create']:
    p=pathlib.Path(os.environ['HERMES_HOME'])/'profiles'/args[2]
    p.mkdir(parents=True)
elif 'boards' in args:
    p=pathlib.Path(os.environ['HERMES_HOME'])/'kanban/boards/media-keycloud'
    p.mkdir(parents=True)
else:
    print('--no-alias --description --default-workdir --workspace --max-runtime --external-supervisor')
""")
        self.fake.chmod(0o700)
        self.state = make_state(self.base / "data", self.fake)

    def profiles(self):
        root = Path(self.state["root"])
        root.mkdir(parents=True, mode=0o700)
        with contextlib.redirect_stdout(io.StringIO()):
            team.install_profiles(REPO, self.state, CREDS)
        return root

    def test_pairing_only_proves_matching_private_human(self):
        def update(chat_type="private", bot=False, text="MEDIA-random", chat_id=7654321):
            return {"message": {"text": text, "from": {"id": 7654321, "is_bot": bot},
                                "chat": {"id": chat_id, "type": chat_type}}}
        for bad in (update("group"), update(bot=True), update(text="wrong"), update(chat_id=8)):
            self.assertIsNone(team.paired_user([bad], "MEDIA-random"))
        self.assertEqual(team.paired_user([update()], "MEDIA-random"), 7654321)

    def test_active_webhook_is_not_removed(self):
        with mock.patch.object(team, "reject_reused_bot"), mock.patch.object(team, "telegram") as api:
            api.side_effect = [{"username": "fixture_bot", "is_bot": True}, {"url": "https://old.invalid"}]
            with self.assertRaisesRegex(team.TeamError, "webhook aktif"):
                team.pair_bot(CREDS["telegram"])
            self.assertEqual([c.args[1] for c in api.call_args_list], ["getMe", "getWebhookInfo"])

    def test_inherited_keys_bot_and_yolo_are_not_forwarded(self):
        with mock.patch.dict(os.environ, {"OPENAI_API_KEY": "old", "TELEGRAM_BOT_TOKEN": "old",
                         "GATEWAY_ALLOW_ALL_USERS": "true", "HERMES_YOLO": "1", "HERMES_HOME": "old"}):
            env = team.isolated_env(self.base / "new")
        for key in ("OPENAI_API_KEY", "TELEGRAM_BOT_TOKEN", "HERMES_YOLO"):
            self.assertNotIn(key, env)
        self.assertEqual(env["GATEWAY_ALLOW_ALL_USERS"], "false")
        self.assertEqual(env["HERMES_KANBAN_HOME"], str(self.base / "new"))

    def test_six_profiles_have_private_keys_and_only_pm_has_bot(self):
        root = self.profiles()
        self.assertEqual(len(list((root / "profiles").iterdir())), 6)
        with contextlib.redirect_stdout(io.StringIO()):
            team.check_team(self.state, live=False)
        for role in team.ROLES:
            profile = root / "profiles" / ("media-" + role)
            env = team.read_env(profile / ".env")
            self.assertEqual(bool(env["TELEGRAM_BOT_TOKEN"]), role == "pm")
            self.assertEqual((profile / ".env").stat().st_mode & 0o777, 0o600)
            self.assertEqual(profile.stat().st_mode & 0o777, 0o700)
            self.assertNotIn("@@WORKSPACE@@", (profile / "SOUL.md").read_text())
            self.assertEqual("GOOGLE_API_KEY" in env, role in ("uiux", "qa"))
            self.assertEqual("OPENAI_API_KEY" in env, role not in ("uiux", "qa"))
        pm = json.loads((root / "profiles/media-pm/config.yaml").read_text())
        self.assertNotIn("terminal", pm["platform_toolsets"]["telegram"])
        self.assertNotIn("media-pm", pm["kanban"]["dispatch_profiles"])
        self.assertFalse(pm["gateway"]["multiplex_profiles"])
        self.assertTrue(pm["gateway"]["standalone"])
        self.assertEqual(pm["platforms"]["telegram"]["extra"]["group_policy"], "disabled")

    def test_repair_migrates_legacy_service_and_preserves_team_data(self):
        root = self.profiles()
        data_dir = Path(self.state["data_dir"])
        config = root / "profiles/media-pm/config.yaml"
        old_config = json.loads(config.read_text())
        old_config["gateway"].pop("standalone")
        team.write_json(config, old_config)
        controller = data_dir / "control.py"
        team.write_private(controller, "# previous controller\n")
        unit = self.base / "units/media-hermes.service"
        team.write_private(unit, team.unit_text(data_dir).replace("RestartPreventExitStatus=78\n", ""))
        team.write_json(data_dir / "team.json", self.state)
        team.write_private(root / "profiles/media-pm/sessions/keep", "existing conversation\n")
        team.write_private(root / "kanban/keep", "existing tasks\n")
        old_hermes = self.base / "home/.hermes/config.yaml"
        team.write_private(old_hermes, "keep old Hermes\n")
        preserved = {p: p.read_bytes() for p in self.base.rglob("*")
                     if p.is_file() and p not in (config, controller, unit)}
        with self.assertRaisesRegex(team.TeamError, "Konfigurasi media-pm"):
            team.check_team(self.state, live=False)
        for _ in range(2):  # Safe to retry after a previous successful or partial repair.
            with mock.patch.object(team, "unit_path", return_value=unit), \
                 mock.patch.object(team, "control") as control, \
                 mock.patch.object(team, "run") as run, \
                 mock.patch.object(team, "api_json", side_effect=AssertionError("No API needed")), \
                 contextlib.redirect_stdout(io.StringIO()):
                team.repair_gateway(self.state)
                team.check_team(self.state, live=False)
            self.assertEqual(control.call_args_list, [mock.call("stop"), mock.call("reset-failed")])
            self.assertEqual(run.call_args.args[0], ["systemctl", "--user", "daemon-reload"])
        self.assertTrue(json.loads(config.read_text())["gateway"]["standalone"])
        self.assertEqual(controller.read_bytes(), (REPO / "scripts/hermes-team.py").read_bytes())
        self.assertIn("RestartPreventExitStatus=78\n", unit.read_text())
        for path, value in preserved.items():
            self.assertEqual(path.read_bytes(), value, str(path))
        for path in (config, controller, unit):
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_repair_refuses_unrelated_edits_before_stopping_or_writing(self):
        root = self.profiles()
        data_dir = Path(self.state["data_dir"])
        unit = self.base / "units/media-hermes.service"
        team.write_private(unit, team.unit_text(data_dir))
        team.write_private(data_dir / "control.py", "# old controller\n")
        config = root / "profiles/media-pm/config.yaml"
        original = json.loads(config.read_text())
        invalid = json.loads(config.read_text())
        invalid["platforms"]["telegram"]["extra"]["allow_from"] = ["wrong-owner"]
        team.write_json(config, invalid)
        with mock.patch.object(team, "unit_path", return_value=unit), \
             mock.patch.object(team, "control") as control:
            with self.assertRaisesRegex(team.TeamError, "Konfigurasi media-pm"):
                team.repair_gateway(self.state)
            control.assert_not_called()
            team.write_json(config, original)
            unit.write_text("[Service]\nExecStart=/bin/true\n")
            with self.assertRaisesRegex(team.TeamError, "bukan unit installer"):
                team.repair_gateway(self.state)
            control.assert_not_called()
        self.assertEqual((data_dir / "control.py").read_text(), "# old controller\n")

    def test_existing_profile_is_not_overwritten(self):
        root = self.profiles()
        before = (root / "profiles/media-pm/.env").read_bytes()
        with self.assertRaisesRegex(team.TeamError, "sudah ada"):
            team.install_profiles(REPO, self.state, {**CREDS, "openai": "changed"})
        self.assertEqual((root / "profiles/media-pm/.env").read_bytes(), before)

    def test_allow_all_and_permission_tampering_prevent_start(self):
        root = self.profiles()
        path = root / "profiles/media-qa/.env"
        original = path.read_text()
        path.write_text(original.replace('GATEWAY_ALLOW_ALL_USERS="false"', 'GATEWAY_ALLOW_ALL_USERS="true"'))
        with self.assertRaises(team.TeamError):
            team.check_team(self.state, live=False)
        path.write_text(original)
        path.chmod(0o644)
        with self.assertRaisesRegex(team.TeamError, "izin"):
            team.check_team(self.state, live=False)

    def test_secret_http_errors_are_redacted_and_redirects_blocked(self):
        leak = "TOKEN_MUST_NEVER_APPEAR"
        error = urllib.error.HTTPError("https://api.telegram.org/bot" + leak, 401, leak, {}, None)
        with mock.patch.object(team.urllib.request, "build_opener") as opener:
            opener.return_value.open.side_effect = error
            with self.assertRaises(team.TeamError) as caught:
                team.api_json("https://api.telegram.org/bot" + leak, "Telegram")
        self.assertNotIn(leak, str(caught.exception))
        self.assertIn("401", str(caught.exception))
        self.assertIsNone(team.NoRedirect().redirect_request(None, None, 302, "", {}, "https://evil.invalid"))

    def test_atomic_writer_refuses_symlink(self):
        original = self.base / "old"
        original.write_text("keep")
        link = self.base / "new"
        link.symlink_to(original)
        with self.assertRaises(team.TeamError):
            team.write_private(link, "replace")
        self.assertEqual(original.read_text(), "keep")

    @unittest.skipUnless(shutil.which("systemd-analyze"), "systemd analyzer unavailable")
    def test_systemd_unit_is_valid_with_spaces_and_percent(self):
        unit = self.base / "media-hermes.service"
        unit.write_text(team.unit_text(self.base / "path with % space"))
        result = subprocess.run(["systemd-analyze", "verify", str(unit)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        with self.assertRaises(team.TeamError):
            team.unit_text(self.base / "bad\npath")

    def test_full_setup_does_not_copy_private_data_or_touch_old_hermes(self):
        repo = self.base / "repo"
        init_repo(repo)
        team.run(["git", "remote", "add", "origin", team.REPO_URL], cwd=repo)
        (repo / ".env").write_text("old application private data")
        (repo / ".deploy").mkdir()
        (repo / ".deploy/prod.env").write_text("old production private data")
        shutil.copytree(REPO / "hermes", repo / "hermes")
        (repo / "scripts").mkdir()
        shutil.copy(REPO / "scripts/hermes-team.py", repo / "scripts/hermes-team.py")
        legacy = self.base / "home/.hermes"
        legacy.mkdir(parents=True)
        (legacy / "config.yaml").write_text("keep old Hermes config\n")
        unit = self.base / "units/media-hermes.service"
        with mock.patch.object(team, "__file__", str(repo / "scripts/hermes-team.py")), \
             mock.patch.object(team.sys.stdin, "isatty", return_value=True), \
             mock.patch.object(team.shutil, "which", return_value=str(self.fake)), \
             mock.patch.object(team, "unit_path", return_value=unit), \
             mock.patch.object(team, "capabilities"), \
             mock.patch.object(team, "check_models"), \
             mock.patch.object(team, "pair_bot", return_value=("7654321", "offline_fixture_bot")), \
             mock.patch.object(team, "ask_secret", side_effect=list(CREDS.values())), \
             mock.patch("builtins.input", return_value=""), \
             mock.patch.dict(os.environ, {"HOME": str(self.base / "home")}), \
             contextlib.redirect_stdout(io.StringIO()):
            team.setup(type("Args", (), {"no_start": True})(), Path(self.state["data_dir"]))
        state = team.read_state(Path(self.state["data_dir"]))
        self.assertFalse((Path(state["workspace"]) / ".env").exists())
        self.assertFalse((Path(state["workspace"]) / ".deploy").exists())
        self.assertEqual((legacy / "config.yaml").read_text(), "keep old Hermes config\n")
        self.assertIn("_gateway", unit.read_text())
        for value in CREDS.values():
            self.assertNotIn(value, unit.read_text())
            self.assertNotIn(value, json.dumps(state))
        self.assertEqual(team.run(["git", "status", "--porcelain"], cwd=state["workspace"]), "")


@unittest.skipUnless(os.environ.get("MEDIA_HERMES_BIN") and os.environ.get("MEDIA_HERMES_PYTHON"),
                     "Set MEDIA_HERMES_BIN and MEDIA_HERMES_PYTHON for native integration")
class NativeHermesTests(unittest.TestCase):
    def test_native_profiles_providers_gateway_and_kanban(self):
        with tempfile.TemporaryDirectory(prefix="media-native-") as tmp:
            base = Path(tmp)
            state = make_state(base, os.environ["MEDIA_HERMES_BIN"])
            root = Path(state["root"])
            root.mkdir(mode=0o700)
            init_repo(Path(state["workspace"]))
            team.write_json(root / "config.yaml", {"kanban": {"dispatch_in_gateway": False}})
            team.write_private(root / ".env", "HERMES_REDACT_SECRETS=true\n")
            team.capabilities(state["hermes"], root)
            with contextlib.redirect_stdout(io.StringIO()):
                team.install_profiles(REPO, state, CREDS)
                team.check_team(state, live=False)
            env = team.isolated_env(root)
            team.run([state["hermes"], "-p", "media-pm", "kanban", "boards", "create", team.BOARD,
                      "--default-workdir", state["workspace"]], env=env, cwd=state["workspace"])
            probe = REPO / "tests/hermes/native_probe.py"
            for role in team.ROLES:
                env["HERMES_HOME"] = str(root / "profiles" / ("media-" + role))
                result = team.run([os.environ["MEDIA_HERMES_PYTHON"], probe, role, state["workspace"]],
                                  env=env, cwd=state["workspace"], timeout=120)
                self.assertIn("NATIVE_OK", result)


if __name__ == "__main__":
    unittest.main()
