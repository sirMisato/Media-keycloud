"""Exercise native Hermes contracts without network/LLMs or a live gateway."""
import json
import os
from pathlib import Path
import socket
import sys
from unittest.mock import patch


def offline(*args, **kwargs):
    raise OSError("Network disabled in Hermes integration fixture")


def verify():
    from hermes_cli.env_loader import load_hermes_dotenv
    load_hermes_dotenv()
    from hermes_cli.config import load_config
    from hermes_cli.runtime_provider import resolve_runtime_provider
    from hermes_cli.profiles import _get_profiles_root
    from gateway.config import load_gateway_config, Platform

    role, workspace = sys.argv[1:]
    cfg = load_config()
    runtime = resolve_runtime_provider(requested=cfg["model"]["provider"],
                                       target_model=cfg["model"]["default"])
    google = role in ("uiux", "qa")
    assert runtime["provider"] == ("gemini" if google else "openai-api"), runtime["provider"]
    assert runtime["api_key"] == os.environ["GOOGLE_API_KEY" if google else "OPENAI_API_KEY"]
    assert runtime["base_url"] == cfg["model"]["base_url"]
    if not google:
        assert runtime["api_mode"] == "codex_responses"
    assert str(_get_profiles_root()) == str(Path(os.environ["HERMES_KANBAN_HOME"]) / "profiles")
    assert cfg["terminal"]["cwd"] == "."
    gateway = load_gateway_config()
    tg = gateway.platforms[Platform.TELEGRAM]
    assert tg.enabled == (role == "pm")
    assert not gateway.multiplex_profiles
    assert tg.extra["group_policy"] == "disabled"
    if role == "pm":
        assert tg.extra["allow_from"] == ["7654321"]
        assert tg.extra["allow_admin_from"] == ["7654321"]
    assert not any(c.enabled for p, c in gateway.platforms.items() if p != Platform.TELEGRAM)
    if role == "pm":
        kanban(workspace, cfg)
    print("NATIVE_OK", role)


def kanban(workspace, cfg):
    from hermes_cli import kanban_db as kb, kanban_db_connect as kbc
    from hermes_cli import kanban_db_dispatch as dispatch
    from gateway.kanban_watchers_dispatcher import _resolve_dispatcher_settings
    settings = _resolve_dispatcher_settings(cfg["kanban"], kb)
    assert settings.max_in_progress == 2
    assert settings.max_in_progress_per_profile == 1
    assert settings.failure_limit == 2
    with kbc.connect_closing() as conn:
        first = kb.create_task(conn, title="Backend fixture", assignee="media-backend",
                               workspace_kind="worktree", workspace_path=workspace)
        second = kb.create_task(conn, title="Backend queued", assignee="media-backend",
                                workspace_kind="worktree", workspace_path=workspace)
        ui = kb.create_task(conn, title="UI fixture", assignee="media-uiux",
                            workspace_kind="worktree", workspace_path=workspace)
        qa = kb.create_task(conn, title="QA after backend", assignee="media-qa", parents=[first],
                            workspace_kind="worktree", workspace_path=workspace)
        assert kb.get_task(conn, qa).status == "todo"
        started = []
        def spawn(task, workdir, board):
            # A real worktree is materialized; only LLM process launch is stubbed.
            assert Path(workdir).joinpath(".git").is_file()
            assert Path(workdir).resolve() != Path(workspace).resolve()
            assert board == "media-keycloud"
            started.append(task.assignee)
            return None
        result = dispatch.dispatch_once(conn, spawn_fn=spawn, board="media-keycloud",
                                         max_in_progress=settings.max_in_progress,
                                         max_in_progress_per_profile=settings.max_in_progress_per_profile,
                                         failure_limit=settings.failure_limit)
        assert sorted(started) == ["media-backend", "media-uiux"], (started, result)
        assert kb.get_task(conn, second).status == "ready"
        assert kb.get_task(conn, qa).status == "todo"
        assert kb.complete_task(conn, first, summary="Fixture completed, no model called")
        kb.recompute_ready(conn)
        assert kb.get_task(conn, qa).status == "ready"


if __name__ == "__main__":
    with patch.object(socket.socket, "connect", offline), \
         patch.object(socket.socket, "connect_ex", offline), \
         patch.object(socket, "getaddrinfo", offline):
        verify()
