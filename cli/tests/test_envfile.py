from pathlib import Path

import pytest

from secria_cli import envfile
from secria_cli.errors import CliError


def test_parse_env_supports_export_quotes_multiline_and_references(tmp_path: Path) -> None:
    path = tmp_path / ".env"
    path.write_text(
        "export A=one\n"
        'B="hello world"\n'
        'C="line1\nline2"\n'
        "D=${HOME}\n"
        "# comment\n"
        "E=\n",
        encoding="utf-8",
    )
    values = envfile.parse_env(path)
    assert values["A"] == "one"
    assert values["B"] == "hello world"
    assert values["C"] == "line1\nline2"
    assert values["D"] == "${HOME}"
    assert values["E"] == ""


def test_parse_env_missing_file(tmp_path: Path) -> None:
    with pytest.raises(CliError):
        envfile.parse_env(tmp_path / "missing.env")


def test_format_env_quotes_and_round_trips(tmp_path: Path) -> None:
    values = {
        "PLAIN": "abc",
        "SPACED": "hello world",
        "MULTI": "line1\nline2",
        "QUOTED": 'say "hi"',
        "REF": "${HOME}",
        "EMPTY": "",
        "BACKSLASH": "back\\slash",
    }
    text = envfile.format_env(values)
    assert "PLAIN=abc" in text
    assert 'SPACED="hello world"' in text
    assert 'MULTI="line1\\nline2"' in text
    assert 'QUOTED="say \\"hi\\""' in text
    assert 'REF="${HOME}"' in text
    assert 'EMPTY=""' in text
    assert 'BACKSLASH="back\\\\slash"' in text

    path = tmp_path / ".env"
    path.write_text(text, encoding="utf-8")
    assert envfile.parse_env(path) == values


def test_hashes_and_payload_are_value_based() -> None:
    values = {"A": "one", "B": "two"}
    digests = envfile.hashes(values)
    assert set(digests) == {"A", "B"}
    assert digests["A"] != digests["B"]
    assert envfile.payload(values) == [
        {"key": "A", "value": "one"},
        {"key": "B", "value": "two"},
    ]


def test_gitignore_detection(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".gitignore").write_text(".env\n*.env\n", encoding="utf-8")
    assert envfile.is_gitignored(repo / ".env") is True
    assert envfile.is_gitignored(repo / "secrets.env") is True
    assert envfile.is_gitignored(repo / ".env.local") is True

    clean = tmp_path / "clean"
    clean.mkdir()
    assert envfile.is_gitignored(clean / ".env") is False


def test_write_env_is_secure_and_round_trips(tmp_path: Path) -> None:
    path = tmp_path / "nested" / ".env"
    envfile.write_env(path, "A=one\n")
    assert path.read_text(encoding="utf-8") == "A=one\n"
    assert envfile.parse_env(path) == {"A": "one"}
