from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

import yaml
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, ValidationError


class ConfigError(ValueError):
    """Raised when a YAML configuration file is invalid."""


class AgentConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    name: str = Field(min_length=1)
    instructions: str = Field(min_length=1)
    urls: list[HttpUrl] = Field(default_factory=list)


@dataclass(frozen=True)
class LoadedConfig:
    path: Path
    config: AgentConfig


def load_config(path: Path) -> LoadedConfig:
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ConfigError(f"Config file not found: {path}") from exc

    try:
        payload = yaml.safe_load(raw) or {}
    except yaml.YAMLError as exc:
        raise ConfigError(f"Failed to parse YAML: {path}") from exc

    try:
        config = AgentConfig.model_validate(payload)
    except ValidationError as exc:
        raise ConfigError(f"Invalid configuration at {path}: {exc}") from exc

    return LoadedConfig(path=path, config=config)


def iter_config_paths(target: Path) -> Iterator[Path]:
    if target.is_file():
        yield target
        return

    if not target.exists():
        raise ConfigError(f"Config path does not exist: {target}")

    for candidate in sorted(target.rglob("*.yml")):
        if candidate.is_file():
            yield candidate
    for candidate in sorted(target.rglob("*.yaml")):
        if candidate.is_file():
            yield candidate


def load_configs(target: Path) -> list[LoadedConfig]:
    configs: list[LoadedConfig] = []
    for path in iter_config_paths(target):
        configs.append(load_config(path))
    if not configs:
        raise ConfigError(f"No configuration files found under {target}")
    return configs


__all__ = ["AgentConfig", "ConfigError", "LoadedConfig", "iter_config_paths", "load_config", "load_configs"]
