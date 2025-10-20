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
    """Create a minimal agent template with SUBAGENT definitions."""
    template = tmp_path / "agent-template"
    template.mkdir()
    (template / "SUBAGENT.md").write_text(
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
    """Test copying agent configuration files."""
    subagent = tmp_path / "subagent-1"
    subagent.mkdir()

    result = copy_agent_config(agent_template, subagent)

    assert "chatmode" in result
    assert "workspace" in result
    assert "messages_dir" in result
    assert (subagent / "subagent.chatmode.md").exists()
    assert (subagent / "subagent.code-workspace").exists()
    assert (subagent / "messages").exists()
    assert (subagent / "messages").is_dir()

    # Check content was copied
    chatmode_content = (subagent / "subagent.chatmode.md").read_text()
    assert chatmode_content.splitlines()[0] == "---"
    assert "description: Test Agent" in chatmode_content
    assert "Primary body content." in chatmode_content


def test_copy_agent_config_missing_subagent(tmp_path: Path) -> None:
    """Test error when SUBAGENT.md is missing."""
    template = tmp_path / "template"
    template.mkdir()
    (template / "subagent.code-workspace").write_text("{}\n")

    subagent = tmp_path / "subagent-1"
    subagent.mkdir()

    with pytest.raises(FileNotFoundError, match="SUBAGENT.md not found"):
        copy_agent_config(template, subagent)


def test_copy_agent_config_missing_workspace(tmp_path: Path) -> None:
    """Test fallback to default workspace when template workspace is missing."""
    template = tmp_path / "template"
    template.mkdir()
    (template / "SUBAGENT.md").write_text(
        """---
description: Fallback Agent
model: fallback
tools: [one]
---

Fallback body.
"""
    )

    subagent = tmp_path / "subagent-1"
    subagent.mkdir()


    # Should succeed by falling back to default workspace template
    result = copy_agent_config(template, subagent)
    
    assert "chatmode" in result
    assert "workspace" in result
    assert "messages_dir" in result
    assert (subagent / "subagent.chatmode.md").exists()
    assert (subagent / "subagent.code-workspace").exists()
    assert (subagent / "messages").exists()


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
        agent_template_dir: Path,
        *,
        extra_attachments=None,
        dry_run: bool = False,
        keep_messages: bool = False,
        workspace_root: Path | None = None,
    ) -> int:
        captured['workspace_root'] = workspace_root
        return 0

    monkeypatch.setattr('lmspace.vscode.cli.launch_agent', fake_launch)

    args = argparse.Namespace(
        query='hello',
        agent_config_path=tmp_path,
        attachment=None,
        dry_run=False,
        workspace_root=tmp_path / 'shared-contexts',
    )

    exit_code = handle_chat(args)

    assert exit_code == 0
    assert captured['workspace_root'] == args.workspace_root
