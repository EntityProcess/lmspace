"""Tests for VS Code workspace agent launcher."""

from __future__ import annotations

import argparse
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from lmspace.vscode.launch_agent import (
    find_unlocked_subagent,
    copy_agent_config,
    create_subagent_lock,
    DEFAULT_LOCK_NAME,
)
from lmspace.vscode.cli import handle_chat


@pytest.fixture
def subagent_root(tmp_path: Path) -> Path:
    """Create a subagent root with some test subagents."""
    root = tmp_path / "agents"
    root.mkdir()

    # Create three subagents: one locked, two unlocked
    for i in range(1, 4):
        subagent = root / f"subagent-{i}"
        subagent.mkdir()

    # Lock subagent-1
    (root / "subagent-1" / DEFAULT_LOCK_NAME).touch()

    return root


@pytest.fixture
def agent_template(tmp_path: Path) -> Path:
    """Create a minimal skill template with SKILL definitions."""
    template = tmp_path / "skill-template"
    template.mkdir()
    (template / "SKILL.md").write_text(
        """---
description: Test Agent
model: test-model
tools: [one]
---

Primary body content.
"""
    )
    (template / "subagent.code-workspace").write_text('{"folders": []}\n')
    return template


def test_find_unlocked_subagent(subagent_root: Path) -> None:
    """Test finding the first unlocked subagent."""
    unlocked = find_unlocked_subagent(subagent_root)
    assert unlocked is not None
    assert unlocked.name == "subagent-2"


def test_find_unlocked_subagent_none_available(tmp_path: Path) -> None:
    """Test when no unlocked subagents are available."""
    root = tmp_path / "agents"
    root.mkdir()

    # Create one locked subagent
    subagent = root / "subagent-1"
    subagent.mkdir()
    (subagent / DEFAULT_LOCK_NAME).touch()

    unlocked = find_unlocked_subagent(root)
    assert unlocked is None


def test_find_unlocked_subagent_nonexistent_root(tmp_path: Path) -> None:
    """Test when the subagent root doesn't exist."""
    root = tmp_path / "nonexistent"
    unlocked = find_unlocked_subagent(root)
    assert unlocked is None


def test_copy_agent_config(agent_template: Path, tmp_path: Path) -> None:
    """Test copying default workspace configuration."""
    subagent = tmp_path / "subagent-1"
    subagent.mkdir()

    result = copy_agent_config(subagent)

    assert "workspace" in result
    assert "messages_dir" in result
    assert (subagent / "subagent.code-workspace").exists()
    assert (subagent / "messages").exists()
    assert (subagent / "messages").is_dir()


def test_copy_agent_config_uses_default_workspace(tmp_path: Path) -> None:
    """Test that copy_agent_config uses the default workspace template."""
    subagent = tmp_path / "subagent-1"
    subagent.mkdir()

    # Should succeed using default workspace template
    result = copy_agent_config(subagent)
    assert "workspace" in result
    assert (subagent / "subagent.code-workspace").exists()





def test_create_subagent_lock(tmp_path: Path) -> None:
    """Test creating a subagent lock file."""
    subagent = tmp_path / "subagent-1"
    subagent.mkdir()

    lock_file = create_subagent_lock(subagent)

    assert lock_file.exists()
    assert lock_file.name == DEFAULT_LOCK_NAME
    assert lock_file.parent == subagent





def test_handle_chat_passes_workspace_root(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Ensure workspace root flows through the chat handler."""
    captured: dict[str, Path | None] = {}

    def fake_launch(
        query: str,
        prompt_file: Path,
        *,
        extra_attachments=None,
        dry_run: bool = False,
        wait: bool = False,
        workspace_root: Path | None = None,
    ) -> int:
        captured['workspace_root'] = workspace_root
        return 0

    monkeypatch.setattr('lmspace.vscode.cli.launch_agent', fake_launch)

    prompt_file_path = tmp_path / 'test-prompt.md'
    prompt_file_path.write_text('Test prompt')
    
    args = argparse.Namespace(
        query='hello',
        prompt_file=prompt_file_path,
        attachment=None,
        dry_run=False,
        wait=False,
        workspace_root=tmp_path / 'shared-contexts',
    )

    exit_code = handle_chat(args)

    assert exit_code == 0
    assert captured['workspace_root'] == args.workspace_root
