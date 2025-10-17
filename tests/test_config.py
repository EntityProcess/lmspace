from pathlib import Path

import pytest

from lmspace.config import AgentConfig, ConfigError, load_config, load_configs


def test_load_config_success(tmp_path: Path) -> None:
    config_file = tmp_path / "agent.yaml"
    config_file.write_text(
        """
name: TestAgent
instructions: Answer clearly.
urls:
  - https://example.com/file.txt
""".strip(),
        encoding="utf-8",
    )

    loaded = load_config(config_file)
    assert loaded.path == config_file
    assert isinstance(loaded.config, AgentConfig)
    assert loaded.config.name == "TestAgent"
    assert [str(url) for url in loaded.config.urls] == ["https://example.com/file.txt"]


def test_load_configs_directory(tmp_path: Path) -> None:
    first = tmp_path / "first.yml"
    second = tmp_path / "nested" / "second.yaml"
    second.parent.mkdir(parents=True)

    first.write_text("name: One\ninstructions: hi\nurls: []", encoding="utf-8")
    second.write_text("name: Two\ninstructions: hi\nurls: []", encoding="utf-8")

    configs = load_configs(tmp_path)
    assert {item.config.name for item in configs} == {"One", "Two"}


def test_load_config_missing_file(tmp_path: Path) -> None:
    with pytest.raises(ConfigError):
        load_config(tmp_path / "missing.yaml")


def test_load_configs_empty_directory(tmp_path: Path) -> None:
    with pytest.raises(ConfigError):
        load_configs(tmp_path)
