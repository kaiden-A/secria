from pathlib import Path

from typer.testing import CliRunner

from secria_cli import config, discovery, main
from secria_cli.main import app

runner = CliRunner()


def test_version() -> None:
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.stdout


def test_version_flag() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.stdout


def test_help() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Secria" in result.stdout


def test_config_set_and_show(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("SECRIA_CONFIG_DIR", str(tmp_path))
    monkeypatch.setenv("SECRIA_API_URL", "https://api.example.com")
    monkeypatch.setenv("SECRIA_DISABLE_KEYRING", "1")
    for key in (
        "SECRIA_ZITADEL_ISSUER",
        "SECRIA_ZITADEL_CLIENT_ID",
        "ZITADEL_ISSUER",
        "ZITADEL_CLIENT_ID",
    ):
        monkeypatch.delenv(key, raising=False)

    result = runner.invoke(
        app, ["config", "set", "zitadel-client-id", "cli-client"]
    )
    assert result.exit_code == 0, result.output
    assert config.load_settings()["zitadel_client_id"] == "cli-client"

    result = runner.invoke(app, ["config", "show"])
    assert result.exit_code == 0, result.output
    assert "https://api.example.com" in result.output
    assert "cli-client" in result.output


def test_login_discovers_and_saves_server(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("SECRIA_CONFIG_DIR", str(tmp_path))
    monkeypatch.setenv("SECRIA_DISABLE_KEYRING", "1")
    monkeypatch.delenv("SECRIA_API_URL", raising=False)
    monkeypatch.setattr(
        main.discovery,
        "fetch",
        lambda server: discovery.ServerConfig(
            api_url=server,
            issuer="https://idp.example.com",
            client_id="cli-client",
        ),
    )
    captured: dict[str, object] = {}

    def fake_device_login(**kwargs) -> None:
        captured.update(kwargs)

    monkeypatch.setattr(main.auth, "device_login", fake_device_login)

    result = runner.invoke(
        app,
        ["login", "--server", "https://api.example.com", "--no-browser"],
    )

    assert result.exit_code == 0, result.output
    assert "https://api.example.com" in result.output
    assert "https://idp.example.com" in result.output
    settings = config.load_settings()
    assert settings["api_url"] == "https://api.example.com"
    assert settings["zitadel_issuer"] == "https://idp.example.com"
    assert settings["zitadel_client_id"] == "cli-client"
    assert captured["issuer"] == "https://idp.example.com"
    assert captured["client_id"] == "cli-client"
    assert captured["server"] == "https://api.example.com"


def test_doctor_offline(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("SECRIA_CONFIG_DIR", str(tmp_path))
    monkeypatch.setenv("SECRIA_DISABLE_KEYRING", "1")
    monkeypatch.delenv("SECRIA_API_URL", raising=False)
    for key in (
        "SECRIA_ZITADEL_ISSUER",
        "SECRIA_ZITADEL_CLIENT_ID",
        "ZITADEL_ISSUER",
        "ZITADEL_CLIENT_ID",
    ):
        monkeypatch.delenv(key, raising=False)
    config.save_server_config(
        "https://api.example.com",
        "https://idp.example.com",
        "cli-client",
    )

    result = runner.invoke(app, ["doctor", "--offline"])

    assert result.exit_code == 0, result.output
    assert "skipped (--offline)" in result.output
    assert "cli-client" in result.output
