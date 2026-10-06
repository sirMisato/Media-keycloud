"""Offline regressions for real installer behavior; all credentials are fixtures."""
import contextlib
import errno
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
import yaml

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

    def installed_team(self):
        root = self.profiles()
        data_dir = Path(self.state["data_dir"])
        Path(self.state["workspace"]).mkdir()
        team.write_json(data_dir / "team.json", self.state)
        team.write_private(data_dir / "control.py", "# previous controller\n")
        unit = self.base / "units/media-hermes.service"
        team.write_private(unit, team.unit_text(data_dir))
        return root, unit

    def local_diagnosis(self, unit):
        with mock.patch.object(team.Path, "home", return_value=self.base), \
             mock.patch.object(team, "unit_path", return_value=unit), \
             mock.patch.object(team, "run", side_effect=AssertionError("No subprocess")), \
             mock.patch.object(team, "control", side_effect=AssertionError("No service changes")), \
             mock.patch.object(team, "api_json", side_effect=AssertionError("No network")), \
             mock.patch.object(team, "write_private", side_effect=AssertionError("No writes")), \
             contextlib.redirect_stdout(io.StringIO()) as output:
            code = team.diagnose(Path(self.state["data_dir"]))
        return code, output.getvalue()

    def test_diagnose_preserves_files_and_does_not_create_missing_lock(self):
        _root, unit = self.installed_team()
        def snapshot():
            return {str(p): (p.read_bytes() if p.is_file() else None,
                             p.stat().st_mode, p.stat().st_mtime_ns) for p in self.base.rglob("*")}
        before = snapshot()
        code, output = self.local_diagnosis(unit)
        self.assertEqual(code, 0, output)
        self.assertEqual(before, snapshot())
        self.assertIn("pemeriksaan lokal lolos", output)
        self.assertFalse((self.base / ".cache").exists())
        for secret in CREDS.values():
            self.assertNotIn(secret, output)
        self.assertNotIn(str(self.base), output)

    def test_diagnose_identifies_yaml_and_env_lines_without_leaking_values(self):
        root, unit = self.installed_team()
        (root / "profiles/media-uiux/config.yaml").write_text("model: [" + CREDS["gemini"] + "\n")
        (root / "profiles/media-qa/.env").write_text("# fixture\nGOOGLE_API_KEY=" + CREDS["gemini"] + "\n")
        code, output = self.local_diagnosis(unit)
        self.assertEqual(code, 1)
        self.assertIn("media-uiux/config.yaml: YAML tidak valid atau tag tidak didukung pada baris", output)
        self.assertIn("media-qa/.env: format env tidak valid pada baris 2", output)
        for secret in CREDS.values():
            self.assertNotIn(secret, output)

    def test_diagnose_reports_access_and_private_mode_failures(self):
        root, unit = self.installed_team()
        protected = root / "profiles/media-pm/.env"
        shared = root / "profiles/media-security/.env"
        shared.chmod(0o644)
        access = team.os.access
        with mock.patch.object(team.os, "access", side_effect=lambda p, mode: False if p == protected else access(p, mode)):
            code, output = self.local_diagnosis(unit)
        self.assertEqual(code, 1)
        self.assertRegex(output, r"\[GAGAL\] media-pm/\.env: .*baca=tidak")
        self.assertRegex(output, r"\[GAGAL\] media-security/\.env: .*mode=0644")
        self.assertEqual(shared.stat().st_mode & 0o777, 0o644)

    def test_diagnose_and_models_accept_yaml_without_rewriting_profiles(self):
        root, unit = self.installed_team()
        for role, flow in (("pm", True), ("backend", False)):
            path = root / "profiles" / ("media-" + role) / "config.yaml"
            path.write_text("# Native YAML fixture\n" + yaml.safe_dump(
                team.config_for(role, self.state), default_flow_style=flow, sort_keys=False, width=10000))
        before = {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}
        code, output = self.local_diagnosis(unit)
        self.assertEqual(code, 0, output)
        with contextlib.redirect_stdout(io.StringIO()) as models:
            team.show_models(self.state)
        self.assertIn("media-pm: provider=openai-api", models.getvalue())
        self.assertIn("media-backend: provider=openai-api", models.getvalue())
        for path, value in before.items():
            self.assertEqual(path.read_bytes(), value)

    def test_profile_reader_rejects_ambiguous_yaml_and_tags_without_leaks(self):
        path = self.base / "media-pm/config.yaml"
        secret = CREDS["openai"]
        cases = ('{"model": "' + secret + '", "model": {}}',
                 "model: " + secret + "\nmodel: {}\n",
                 "model: {provider: " + secret + ", provider: gemini}\n",
                 "model: !!python/object/apply:builtins.print ['" + secret + "']\n",
                 "model: [" + secret + "\n",
                 "model: &a [*a, '" + secret + "']\n",
                 "- " + secret + "\n", "", "null\n")
        for raw in cases:
            team.write_private(path, raw)
            with contextlib.redirect_stdout(io.StringIO()) as output:
                with self.assertRaises(team.TeamError) as caught:
                    team.read_profile_config(path)
            self.assertNotIn(secret, str(caught.exception))
            self.assertEqual(output.getvalue(), "")
            self.assertEqual(path.read_text(), raw)

    def test_yaml_drift_or_corruption_blocks_migration_before_stopping(self):
        root, unit = self.installed_team()
        path = root / "profiles/media-pm/config.yaml"
        edited = team.config_for("pm", self.state)
        edited["platforms"]["telegram"]["extra"]["dm_policy"] = "open"
        invalid = (yaml.safe_dump(edited), "model: [" + CREDS["telegram"] + "\n")
        with mock.patch.object(team, "unit_path", return_value=unit), \
             mock.patch.object(team, "control") as control, \
             mock.patch.object(team, "check_models") as models:
            for raw in invalid:
                path.write_text(raw)
                before = {p: p.read_bytes() for p in self.base.rglob("*") if p.is_file()}
                with self.assertRaises(team.TeamError) as caught:
                    team.use_codex(self.state)
                self.assertNotIn(CREDS["telegram"], str(caught.exception))
                control.assert_not_called()
                models.assert_not_called()
                for file, value in before.items():
                    self.assertEqual(file.read_bytes(), value)

    def test_missing_yaml_reader_has_actionable_error_and_json_still_works(self):
        path = self.base / "media-pm/config.yaml"
        with mock.patch.dict(team.sys.modules, {"yaml": None}):
            team.write_json(path, {"model": {"provider": "openai-api"}})
            self.assertEqual(team.read_profile_config(path)["model"]["provider"], "openai-api")
            path.write_text("model: " + CREDS["openai"] + "\n")
            with self.assertRaisesRegex(team.TeamError, "python3-yaml") as caught:
                team.read_profile_config(path)
            self.assertNotIn(CREDS["openai"], str(caught.exception))

    def test_diagnose_handles_missing_or_invalid_manifest_without_setup_advice(self):
        _root, unit = self.installed_team()
        manifest = Path(self.state["data_dir"]) / "team.json"
        cases = (None, "[]", '{"broken": ' + CREDS["openai"], json.dumps({**self.state, "owner": None}))
        for content in cases:
            with self.subTest(content=type(content).__name__):
                if content is None:
                    manifest.unlink()
                else:
                    team.write_private(manifest, content)
                code, output = self.local_diagnosis(unit)
                self.assertEqual(code, 1)
                self.assertIn("team.json", output)
                self.assertNotIn("Jalankan setup", output)
                self.assertNotIn(CREDS["openai"], output)

    def test_lock_diagnosis_and_migration_refuse_busy_lock_without_truncating(self):
        _root, unit = self.installed_team()
        lock = self.base / ".cache/media-keycloud/setup.lock"
        team.write_private(lock, "existing lock contents\n")
        with lock.open("r") as held:
            team.fcntl.flock(held, team.fcntl.LOCK_EX | team.fcntl.LOCK_NB)
            code, output = self.local_diagnosis(unit)
            self.assertEqual(code, 1)
            self.assertIn("lock pemasangan: sedang dipakai proses lain", output)
            with mock.patch.object(team.Path, "home", return_value=self.base):
                with self.assertRaisesRegex(team.TeamError, "Lock pemasangan sedang dipakai"):
                    with team.setup_lock():
                        self.fail("Lock must not be acquired")
        with mock.patch.object(team.Path, "home", return_value=self.base):
            with team.setup_lock():
                pass
        self.assertEqual(lock.read_text(), "existing lock contents\n")

    def test_error_details_do_not_include_exception_values_or_paths(self):
        secret = CREDS["telegram"]
        errors = (PermissionError(errno.EACCES, secret, "/secret/" + secret),
                  KeyError(secret), TypeError(secret),
                  json.JSONDecodeError(secret, secret, 0))
        for error in errors:
            self.assertNotIn(secret, team.safe_error(error))
        self.assertIn("EACCES", team.safe_error(errors[0]))
        with mock.patch.object(team.Path, "read_text", side_effect=errors[0]):
            with self.assertRaisesRegex(team.TeamError, "media-pm/.env: EACCES") as caught:
                team.read_env(Path("/secret/media-pm/.env"))
        self.assertNotIn(secret, str(caught.exception))

    def test_lock_access_error_is_labeled_and_symlink_is_not_followed(self):
        lock = self.base / ".cache/media-keycloud/setup.lock"
        team.write_private(lock.parent / "target", "preserve this\n")
        lock.symlink_to(lock.parent / "target")
        with mock.patch.object(team.Path, "home", return_value=self.base):
            with self.assertRaisesRegex(team.TeamError, "Lock pemasangan.*ELOOP"):
                with team.setup_lock():
                    self.fail("Must refuse symlink")
            with mock.patch.object(team.os, "open", side_effect=PermissionError(
                    errno.EACCES, CREDS["openai"], CREDS["telegram"])):
                with self.assertRaisesRegex(team.TeamError, "Lock pemasangan.*EACCES") as caught:
                    with team.setup_lock():
                        self.fail("Must refuse inaccessible lock")
        self.assertEqual((lock.parent / "target").read_text(), "preserve this\n")
        for secret in CREDS.values():
            self.assertNotIn(secret, str(caught.exception))

    def test_env_rejects_duplicate_or_non_string_secrets_without_echoing(self):
        path = self.base / "media-pm/.env"
        for value in ('OPENAI_API_KEY="one"\nOPENAI_API_KEY="two"\n',
                      'OPENAI_API_KEY=null\n', 'OPENAI_API_KEY=["private"]\n',
                      CREDS["openai"] + "\n"):
            team.write_private(path, value)
            with self.assertRaisesRegex(team.TeamError, "media-pm/.env: format env") as caught:
                team.read_env(path)
            self.assertNotIn(CREDS["openai"], str(caught.exception))

    def test_diagnose_cli_works_before_manifest_and_root_stays_blocked(self):
        argv = ["hermes-team.py", "--data-dir", self.state["data_dir"], "diagnose"]
        with mock.patch.object(team.sys, "argv", argv), \
             mock.patch.object(team.os, "geteuid", return_value=1000), \
             mock.patch.object(team, "diagnose", return_value=1) as diagnose, \
             mock.patch.object(team, "read_state", side_effect=AssertionError("diagnose inspects manifest itself")):
            self.assertEqual(team.main(), 1)
            diagnose.assert_called_once_with(Path(self.state["data_dir"]))
        with mock.patch.object(team.sys, "argv", argv), mock.patch.object(team.os, "geteuid", return_value=0):
            with self.assertRaisesRegex(team.TeamError, "tanpa sudo"):
                team.main()

    def test_use_codex_reports_non_json_kanban_without_leaking_or_changing_files(self):
        _root, unit = self.installed_team()
        before = {p: p.read_bytes() for p in self.base.rglob("*") if p.is_file()}
        with mock.patch.object(team, "unit_path", return_value=unit), \
             mock.patch.object(team, "control") as control, \
             mock.patch.object(team, "check_models"), \
             mock.patch.object(team, "run", return_value=CREDS["openai"]), \
             contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(team.TeamError, "Respons status worker bukan JSON") as caught:
                team.use_codex(self.state)
        control.assert_called_once_with("stop")
        self.assertNotIn(CREDS["openai"], str(caught.exception))
        for path, value in before.items():
            self.assertEqual(path.read_bytes(), value)

    def test_codex_metadata_check_never_contacts_gemini(self):
        with mock.patch.object(team, "api_json", return_value={"id": team.DEFAULT_CODEX}) as api, \
             contextlib.redirect_stdout(io.StringIO()):
            team.check_models(CREDS["openai"], "", team.DEFAULT_CODEX, "")
        api.assert_called_once()
        self.assertTrue(api.call_args.args[0].startswith("https://api.openai.com/"))

    def test_use_codex_preserves_bot_roles_history_and_selected_model(self):
        self.state["codex_model"] = "gpt-5.3-codex-fixture"
        root, unit = self.installed_team()
        data_dir = Path(self.state["data_dir"])
        pm_env = (root / "profiles/media-pm/.env").read_bytes()
        pm_config = root / "profiles/media-pm/config.yaml"
        legacy = json.loads(pm_config.read_text())
        legacy["gateway"].pop("standalone")
        team.write_private(pm_config, yaml.safe_dump(legacy, default_flow_style=True, width=10000))
        backend_config = root / "profiles/media-backend/config.yaml"
        team.write_private(backend_config, yaml.safe_dump(team.config_for("backend", self.state)))
        for role in team.ROLES:
            path = root / "profiles" / ("media-" + role) / "SOUL.md"
            path.write_text(path.read_text() + "\nInstruksi lokal pemilik tetap ada.\n")
        retained = root / "profiles/media-uiux/memories/keep"
        team.write_private(retained, "existing memory\n")
        tasks = root / "kanban/keep"
        team.write_private(tasks, "existing task history\n")
        def run(args, **kwargs):
            return "[]" if args[0] == self.state["hermes"] else ""
        with mock.patch.object(team, "unit_path", return_value=unit), \
             mock.patch.object(team, "control") as control, \
             mock.patch.object(team, "run", side_effect=run), \
             mock.patch.object(team, "check_models") as models, \
             contextlib.redirect_stdout(io.StringIO()) as output:
            for _ in range(2):
                team.use_codex(team.read_state(data_dir))
            migrated = team.read_state(data_dir)
            team.check_team(migrated, live=False)
        self.assertEqual(migrated["model_mode"], "codex")
        self.assertNotIn("gemini_model", migrated)
        self.assertEqual(control.call_args_list, [mock.call("stop"), mock.call("reset-failed")] * 2)
        models.assert_called_with(CREDS["openai"], "", "gpt-5.3-codex-fixture", "")
        self.assertEqual((root / "profiles/media-pm/.env").read_bytes(), pm_env)
        self.assertEqual(retained.read_text(), "existing memory\n")
        self.assertEqual(tasks.read_text(), "existing task history\n")
        for role in team.ROLES:
            profile = root / "profiles" / ("media-" + role)
            cfg = json.loads((profile / "config.yaml").read_text())
            self.assertEqual(cfg["model"]["provider"], "openai-api")
            self.assertEqual(cfg["model"]["default"], "gpt-5.3-codex-fixture")
            env = team.read_env(profile / ".env")
            self.assertNotIn("GOOGLE_API_KEY", env)
            self.assertEqual(env["OPENAI_API_KEY"], CREDS["openai"])
            self.assertEqual(bool(env["TELEGRAM_BOT_TOKEN"]), role == "pm")
            soul = (profile / "SOUL.md").read_text()
            self.assertIn("Instruksi lokal pemilik tetap ada.", soul)
            self.assertEqual(soul.count("Konfigurasi awal: provider "), 1)
            self.assertNotIn("provider gemini", soul)
            for name in ("config.yaml", ".env", "SOUL.md"):
                self.assertEqual((profile / name).stat().st_mode & 0o777, 0o600)
        for value in CREDS.values():
            self.assertNotIn(value, output.getvalue())
        self.assertEqual((data_dir / "control.py").read_bytes(), (REPO / "scripts/hermes-team.py").read_bytes())

    def test_codex_key_rotation_only_requests_openai_and_updates_all_roles(self):
        self.state["model_mode"] = "codex"
        self.state.pop("gemini_model")
        root, _unit = self.installed_team()
        replacement = "TEST_ONLY_REPLACEMENT_OPENAI_KEY_123456789"
        with mock.patch.object(team.os, "geteuid", return_value=1000), \
             mock.patch.object(team.sys, "argv", ["hermes-team.py", "--data-dir", self.state["data_dir"], "rotate-keys"]), \
             mock.patch.object(team.sys.stdin, "isatty", return_value=True), \
             mock.patch.object(team, "ask_secret", return_value=replacement) as ask, \
             mock.patch.object(team, "check_models") as models, \
             contextlib.redirect_stdout(io.StringIO()) as output:
            team.main()
            team.check_team(self.state, live=False)
        ask.assert_called_once_with("OpenAI API key baru")
        models.assert_called_once_with(replacement, "", team.DEFAULT_CODEX, "")
        for role in team.ROLES:
            env = team.read_env(root / "profiles" / ("media-" + role) / ".env")
            self.assertEqual(env["OPENAI_API_KEY"], replacement)
            self.assertNotIn("GOOGLE_API_KEY", env)
        self.assertNotIn(replacement, output.getvalue())

    def test_use_codex_blocks_running_tasks_without_changing_files(self):
        root, unit = self.installed_team()
        before = {p: p.read_bytes() for p in self.base.rglob("*") if p.is_file()}
        with mock.patch.object(team, "unit_path", return_value=unit), \
             mock.patch.object(team, "control") as control, \
             mock.patch.object(team, "check_models"), \
             mock.patch.object(team, "run", return_value='[{"id":"t_fixture","status":"running"}]'), \
             contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(team.TeamError, "Masih ada task running"):
                team.use_codex(self.state)
        control.assert_called_once_with("stop")
        for path, value in before.items():
            self.assertEqual(path.read_bytes(), value)

    def test_use_codex_rolls_back_partial_write_failure(self):
        root, unit = self.installed_team()
        before = {p: p.read_bytes() for p in self.base.rglob("*") if p.is_file()}
        original_write = team.write_private
        fail_once = [True]
        def write(path, value, **kwargs):
            if fail_once[0] and str(path).endswith("media-uiux/.env"):
                fail_once[0] = False
                raise OSError("fixture write failure")
            original_write(path, value, **kwargs)
        with mock.patch.object(team, "unit_path", return_value=unit), \
             mock.patch.object(team, "control") as control, \
             mock.patch.object(team, "check_models"), \
             mock.patch.object(team, "run", return_value="[]"), \
             mock.patch.object(team, "write_private", side_effect=write), \
             contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(team.TeamError, "Konfigurasi sebelumnya dipulihkan"):
                team.use_codex(self.state)
            team.check_team(team.read_state(Path(self.state["data_dir"])), live=False)
        control.assert_called_once_with("stop")
        for path, value in before.items():
            self.assertEqual(path.read_bytes(), value, str(path))

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
             mock.patch.object(team, "ask_secret", side_effect=[CREDS["openai"], CREDS["telegram"]]) as secrets, \
             mock.patch("builtins.input", return_value=""), \
             mock.patch.dict(os.environ, {"HOME": str(self.base / "home")}), \
             contextlib.redirect_stdout(io.StringIO()):
            team.setup(type("Args", (), {"no_start": True})(), Path(self.state["data_dir"]))
        state = team.read_state(Path(self.state["data_dir"]))
        self.assertEqual(state["model_mode"], "codex")
        self.assertNotIn("gemini_model", state)
        self.assertEqual(secrets.call_count, 2)
        for role in team.ROLES:
            profile = Path(state["root"]) / "profiles" / ("media-" + role)
            self.assertEqual(json.loads((profile / "config.yaml").read_text())["model"]["provider"], "openai-api")
            self.assertNotIn("GOOGLE_API_KEY", team.read_env(profile / ".env"))
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
        self.exercise_native(migrate=False)

    def test_native_all_codex_migration_and_runtime(self):
        self.exercise_native(migrate=True)

    def exercise_native(self, *, migrate):
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
            if migrate:
                # Exercise Hermes' real writer, not only PyYAML fixture serialization.
                paths = [root / "profiles" / ("media-" + role) / "config.yaml" for role in ("pm", "backend")]
                rewrite = """import json, sys
from pathlib import Path
from hermes_cli.config import atomic_config_write
for name in sys.argv[1:]:
    path = Path(name)
    config = json.loads(path.read_text())
    path.write_text('# Native YAML fixture\\n{}\\n')
    atomic_config_write(path, config)
print('NATIVE_YAML_OK')
"""
                result = team.run([os.environ["MEDIA_HERMES_PYTHON"], "-c", rewrite, *paths],
                                  env=env, cwd=state["workspace"], timeout=120)
                self.assertIn("NATIVE_YAML_OK", result)
                for role, path in zip(("pm", "backend"), paths):
                    with self.assertRaises(json.JSONDecodeError):
                        json.loads(path.read_text())
                    self.assertEqual(team.read_profile_config(path), team.config_for(role, state))
                team.write_json(base / "team.json", state)
                team.write_private(base / "control.py", "# old controller\n")
                unit = base / "units/media-hermes.service"
                team.write_private(unit, team.unit_text(base))
                native_run = team.run
                def run(args, **kwargs):
                    return "" if args[0] == "systemctl" else native_run(args, **kwargs)
                with mock.patch.object(team, "unit_path", return_value=unit), \
                     mock.patch.object(team, "control"), \
                     mock.patch.object(team, "check_models"), \
                     mock.patch.object(team, "run", side_effect=run), \
                     contextlib.redirect_stdout(io.StringIO()):
                    team.use_codex(state)
                state = team.read_state(base)
                self.assertEqual(state["model_mode"], "codex")
            probe = REPO / "tests/hermes/native_probe.py"
            for role in team.ROLES:
                env["HERMES_HOME"] = str(root / "profiles" / ("media-" + role))
                result = team.run([os.environ["MEDIA_HERMES_PYTHON"], probe, role, state["workspace"], team.model_mode(state)],
                                  env=env, cwd=state["workspace"], timeout=120)
                self.assertIn("NATIVE_OK", result)


if __name__ == "__main__":
    unittest.main()
