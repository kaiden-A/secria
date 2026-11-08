import os
from pathlib import Path

from secria_cli import config


def test_settings_round_trip(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("SECRIA_CONFIG_DIR", str(tmp_path))
    config.save_settings({"default_workspace": "acme"})
    assert config.load_settings() == {"default_workspace": "acme"}
    assert (tmp_path / "config.json").is_file()


def test_link_file_round_trip_and_parent_search(tmp_path: Path, monkeypatch) -> None:
    child = tmp_path / "apps" / "api"
    child.mkdir(parents=True)
    monkeypatch.chdir(child)
    path = tmp_path / config.LINK_NAME
    config.save_link(path, workspace="acme", project="api", environment="dev")

    found_path, data = config.find_link()
    assert found_path == path
    assert data == {"workspace": "acme", "project": "api", "environment": "dev"}
    assert "no secrets" in path.read_text(encoding="utf-8").lower()


def test_load_environment_only_reads_allowed_keys(tmp_path: Path, monkeypatch) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "ZITADEL_ISSUER=https://idp.test\n"
        "ZITADEL_CLIENT_ID=client-1\n"
        "DATABASE_URL=postgres://should-not-load\n"
        "SECRIA_MASTER_KEY=should-not-load\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("ZITADEL_ISSUER", raising=False)
    monkeypatch.delenv("ZITADEL_CLIENT_ID", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("SECRIA_MASTER_KEY", raising=False)
    config.load_environment()
    assert os.environ["ZITADEL_ISSUER"] == "https://idp.test"
    assert os.environ["ZITADEL_CLIENT_ID"] == "client-1"
    assert "DATABASE_URL" not in os.environ
    assert "SECRIA_MASTER_KEY" not in os.environ


def test_api_url_and_zitadel_overrides(monkeypatch) -> None:
    monkeypatch.setenv("SECRIA_API_URL", "https://api.example.com/")
    assert config.api_url() == "https://api.example.com"
    monkeypatch.setenv("SECRIA_ZITADEL_ISSUER", "https://idp.example.com")
    monkeypatch.setenv("SECRIA_ZITADEL_CLIENT_ID", "cli-client")
    assert config.zitadel_issuer() == "https://idp.example.com"
    assert config.zitadel_client_id() == "cli-client"
