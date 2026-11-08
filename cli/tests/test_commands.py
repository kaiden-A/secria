import json
import os
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

import pytest
from typer.testing import CliRunner

from secria_cli import main

runner = CliRunner()


@contextmanager
def workdir(path: Path):
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


class FakeAPI:
    def __init__(self) -> None:
        self.calls: list[dict] = []
        self.workspace = {
            "id": "w1",
            "slug": "acme",
            "name": "Acme",
            "role": "owner",
            "memberCount": 1,
            "projectCount": 1,
            "createdAt": 0,
        }
        self.project = {
            "id": "p1",
            "workspaceId": "w1",
            "name": "API",
            "slug": "api",
            "description": "",
            "role": "admin",
            "archivedAt": None,
            "environmentCount": 1,
            "memberCount": 1,
            "createdAt": 0,
            "updatedAt": 0,
            "environments": [
                {"id": "e1", "name": "Dev", "slug": "dev", "position": 0, "createdAt": 0}
            ],
        }
        self.diff = {
            "added": ["NEW"],
            "changed": ["CHANGED"],
            "removed": ["OLD"],
            "unchanged": ["SAME"],
        }
        self.values = {"SAME": "s3cr3t-one", "CHANGED": "s3cr3t-two", "NEW": "s3cr3t-three"}

    def request(self, method, path, *, json_body=None, params=None):
        self.calls.append(
            {"method": method, "path": path, "json": json_body, "params": params}
        )
        if method == "GET" and path == "/api/v1/service-tokens/current":
            return {
                "tokenId": "st1",
                "name": "ci",
                "access": "read",
                "workspaceId": "w1",
                "workspaceSlug": "acme",
                "workspaceName": "Acme",
                "projectId": "p1",
                "projectSlug": "api",
                "projectName": "API",
                "environmentId": "e1",
                "environmentSlug": "dev",
                "environmentName": "Dev",
            }
        if method == "GET" and path == "/api/v1/workspaces":
            return [self.workspace]
        if method == "GET" and path == "/api/v1/workspaces/w1/projects":
            summary = {
                key: self.project[key]
                for key in ("id", "slug", "name", "role", "environmentCount", "memberCount")
            }
            return [summary]
        if method == "POST" and path == "/api/v1/workspaces/w1/projects":
            return self.project
        if method == "GET" and path == "/api/v1/projects/p1":
            return self.project
        if method == "GET" and path == "/api/v1/projects/p1/environments":
            return self.project["environments"]
        if method == "POST" and path.endswith("/secrets/diff"):
            return self.diff
        if method == "GET" and path == "/api/v1/projects/p1/environments/e1/secrets":
            return [
                {"key": "SAME", "version": 1, "updatedAt": 0, "comment": ""}
            ]
        if method == "GET" and path.endswith("/secrets/SAME"):
            return {"key": "SAME", "value": "s3cr3t-value", "version": 1}
        if method == "GET" and path.endswith("/download"):
            if params and params.get("format") == "json":
                return {"A": "one", "SECRET": "value"}
            return "A=one\nSECRET=value\n"
        if method == "PUT" and path.endswith("/secrets"):
            return {"added": 1, "updated": 1, "removed": 0, "unchanged": 1}
        if method == "POST" and path.endswith("/service-tokens"):
            return {"token": "st_test_token", "name": json_body.get("name") if json_body else "ci"}
        if method == "DELETE":
            return None
        return {}

    def request_text(self, method, path, *, params=None):
        self.calls.append({"method": method, "path": path, "params": params, "text": True})
        return "A=one\nSECRET=value\n"


@pytest.fixture(autouse=True)
def _config(tmp_path, monkeypatch):
    monkeypatch.setenv("SECRIA_CONFIG_DIR", str(tmp_path / "config"))
    monkeypatch.setenv("SECRIA_DISABLE_KEYRING", "1")


@pytest.fixture
def fake_api(monkeypatch):
    fake = FakeAPI()
    monkeypatch.setattr(main, "_api", lambda: fake)
    return fake


def _link_and_env():
    main.config.save_link(
        Path.cwd() / ".secria.yaml",
        workspace="acme",
        project="api",
        environment="dev",
    )
    Path(".env").write_text(
        "SAME=s3cr3t-one\nCHANGED=s3cr3t-two\nNEW=s3cr3t-three\n",
        encoding="utf-8",
    )


def test_push_dry_run_does_not_write(fake_api, tmp_path):
    with workdir(tmp_path):
        _link_and_env()
        result = runner.invoke(main.app, ["push", "--dry-run", "--yes"])
        assert result.exit_code == 0, result.output
        assert "NEW" in result.output
        assert "CHANGED" in result.output
        assert not any(call["method"] == "PUT" for call in fake_api.calls)
        assert "s3cr3t-one" not in result.output


def test_push_yes_writes_merge_payload(fake_api, tmp_path):
    with workdir(tmp_path):
        _link_and_env()
        result = runner.invoke(main.app, ["push", "--yes"])
        assert result.exit_code == 0, result.output
        puts = [call for call in fake_api.calls if call["method"] == "PUT"]
        assert len(puts) == 1
        assert puts[0]["json"]["mode"] == "merge"
        assert {item["key"] for item in puts[0]["json"]["secrets"]} == {
            "SAME",
            "CHANGED",
            "NEW",
        }
        assert "s3cr3t-one" not in result.output


def test_diff_prints_without_writing(fake_api, tmp_path):
    with workdir(tmp_path):
        _link_and_env()
        result = runner.invoke(main.app, ["diff"])
        assert result.exit_code == 0, result.output
        assert "NEW" in result.output
        assert "OLD" in result.output
        assert not any(call["method"] == "PUT" for call in fake_api.calls)


def test_pull_json_writes_a_file(fake_api, tmp_path):
    with workdir(tmp_path):
        _link_and_env()
        result = runner.invoke(
            main.app, ["pull", "--out", "out.json", "--format", "json", "--force"]
        )
        assert result.exit_code == 0, result.output
        assert json.loads(Path("out.json").read_text(encoding="utf-8")) == {
            "A": "one",
            "SECRET": "value",
        }


def test_secrets_get_prints_only_the_value(fake_api, tmp_path):
    with workdir(tmp_path):
        _link_and_env()
        result = runner.invoke(main.app, ["secrets", "get", "SAME"])
        assert result.exit_code == 0, result.output
        assert result.output.strip() == "s3cr3t-value"


def test_secrets_set_sends_assignment(fake_api, tmp_path):
    with workdir(tmp_path):
        _link_and_env()
        result = runner.invoke(main.app, ["secrets", "set", "TOKEN=abc"])
        assert result.exit_code == 0, result.output
        puts = [call for call in fake_api.calls if call["method"] == "PUT"]
        assert puts[0]["json"]["secrets"] == [{"key": "TOKEN", "value": "abc"}]
        assert "abc" not in result.output


def test_run_injects_secrets_and_strips_service_token(fake_api, monkeypatch, tmp_path):
    captured = {}

    def fake_run(command, env):
        captured["command"] = command
        captured["env"] = env
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(main.subprocess, "run", fake_run)
    monkeypatch.setenv("SECRIA_TOKEN", "secria_st_should_not_leak")
    with workdir(tmp_path):
        _link_and_env()
        result = runner.invoke(main.app, ["run", "--", "echo", "hello"])
        assert result.exit_code == 0, result.output
        assert captured["command"] == ["echo", "hello"]
        assert captured["env"]["SECRET"] == "value"
        assert "SECRIA_TOKEN" not in captured["env"]


def test_listing_commands_and_token_create(fake_api, tmp_path):
    with workdir(tmp_path):
        _link_and_env()
        for args in (
            ["workspace", "list"],
            ["project", "list"],
            ["env", "list"],
            ["secrets", "list"],
        ):
            result = runner.invoke(main.app, args)
            assert result.exit_code == 0, result.output
        result = runner.invoke(main.app, ["token", "create", "--name", "ci"])
        assert result.exit_code == 0, result.output
        assert "st_test_token" in result.output


def test_service_token_mode_uses_scope_and_blocks_management(
    fake_api, monkeypatch, tmp_path
):
    monkeypatch.setenv("SECRIA_TOKEN", "secria_st_ci")
    with workdir(tmp_path):
        _link_and_env()

        result = runner.invoke(main.app, ["secrets", "list"])
        assert result.exit_code == 0, result.output
        paths = [call["path"] for call in fake_api.calls]
        assert "/api/v1/service-tokens/current" in paths
        assert "/api/v1/workspaces" not in paths
        assert all("w1" not in path for path in paths)

        result = runner.invoke(main.app, ["whoami"])
        assert result.exit_code == 0, result.output
        assert "Service token" in result.output
        assert "acme/api/dev" in result.output

        result = runner.invoke(
            main.app, ["secrets", "list", "--env", "prod"]
        )
        assert result.exit_code == 1
        assert "scoped to environment 'dev'" in result.output

        result = runner.invoke(main.app, ["token", "create", "--name", "nested"])
        assert result.exit_code == 1
        assert "cannot create" in result.output
