"""Tests for VSCode subagent warmup functionality."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from lmspace.vscode.launch_agent import (
    get_all_subagent_workspaces,
    warmup_subagents,
)


def test_get_all_subagent_workspaces_empty_dir(tmp_path: Path) -> None:
    """Test that get_all_subagent_workspaces returns empty list for empty directory."""
    result = get_all_subagent_workspaces(tmp_path)
    assert result == []


def test_get_all_subagent_workspaces_nonexistent_dir(tmp_path: Path) -> None:
    """Test that get_all_subagent_workspaces returns empty list for nonexistent directory."""
    nonexistent = tmp_path / "does_not_exist"
    result = get_all_subagent_workspaces(nonexistent)
    assert result == []


def test_get_all_subagent_workspaces_with_workspaces(tmp_path: Path) -> None:
    """Test that get_all_subagent_workspaces finds workspace files."""
    # Create subagent directories with workspace files
    for i in [1, 3, 2]:  # Out of order to test sorting
        subagent_dir = tmp_path / f"subagent-{i}"
        subagent_dir.mkdir()
        workspace_file = subagent_dir / "subagent.code-workspace"
        workspace_file.write_text("{}", encoding="utf-8")
    
    # Create a directory that shouldn't be picked up
    other_dir = tmp_path / "other-dir"
    other_dir.mkdir()
    (other_dir / "subagent.code-workspace").write_text("{}", encoding="utf-8")
    
    result = get_all_subagent_workspaces(tmp_path)
    
    assert len(result) == 3
    # Should be sorted by number
    assert result[0].parent.name == "subagent-1"
    assert result[1].parent.name == "subagent-2"
    assert result[2].parent.name == "subagent-3"


def test_get_all_subagent_workspaces_missing_workspace_file(tmp_path: Path) -> None:
    """Test that subagents without workspace files are skipped."""
    # Create subagent directory without workspace file
    subagent_dir = tmp_path / "subagent-1"
    subagent_dir.mkdir()
    
    result = get_all_subagent_workspaces(tmp_path)
    assert result == []


def test_warmup_subagents_no_workspaces(tmp_path: Path) -> None:
    """Test that warmup_subagents returns error when no workspaces found."""
    result = warmup_subagents(subagent_root=tmp_path, dry_run=True)
    assert result == 1


@patch("subprocess.Popen")
def test_warmup_subagents_dry_run(mock_popen: MagicMock, tmp_path: Path) -> None:
    """Test that warmup_subagents in dry-run mode doesn't open workspaces."""
    # Create subagent with workspace
    subagent_dir = tmp_path / "subagent-1"
    subagent_dir.mkdir()
    workspace_file = subagent_dir / "subagent.code-workspace"
    workspace_file.write_text("{}", encoding="utf-8")
    
    result = warmup_subagents(subagent_root=tmp_path, dry_run=True)
    
    assert result == 0
    mock_popen.assert_not_called()


@patch("subprocess.Popen")
def test_warmup_subagents_opens_workspaces(
    mock_popen: MagicMock,
    tmp_path: Path,
) -> None:
    """Test that warmup_subagents opens all workspaces."""
    # Create multiple subagent directories
    for i in [1, 2, 3]:
        subagent_dir = tmp_path / f"subagent-{i}"
        subagent_dir.mkdir()
        workspace_file = subagent_dir / "subagent.code-workspace"
        workspace_file.write_text("{}", encoding="utf-8")
    
    result = warmup_subagents(subagent_root=tmp_path, subagents=3)
    
    assert result == 0
    assert mock_popen.call_count == 3


@patch("subprocess.Popen", side_effect=Exception("Failed to open"))
def test_warmup_subagents_handles_errors(
    mock_popen: MagicMock,
    tmp_path: Path,
) -> None:
    """Test that warmup_subagents handles errors gracefully."""
    # Create subagent with workspace
    subagent_dir = tmp_path / "subagent-1"
    subagent_dir.mkdir()
    workspace_file = subagent_dir / "subagent.code-workspace"
    workspace_file.write_text("{}", encoding="utf-8")
    
    # Should complete despite the error
    result = warmup_subagents(subagent_root=tmp_path)
    assert result == 0
    mock_popen.assert_called_once()


@patch("subprocess.Popen")
def test_warmup_subagents_respects_count_limit(
    mock_popen: MagicMock,
    tmp_path: Path,
) -> None:
    """Test that warmup_subagents only opens the specified number of workspaces."""
    # Create 5 subagent directories
    for i in [1, 2, 3, 4, 5]:
        subagent_dir = tmp_path / f"subagent-{i}"
        subagent_dir.mkdir()
        workspace_file = subagent_dir / "subagent.code-workspace"
        workspace_file.write_text("{}", encoding="utf-8")
    
    # Only open 2
    result = warmup_subagents(subagent_root=tmp_path, subagents=2)
    
    assert result == 0
    assert mock_popen.call_count == 2


@patch("subprocess.Popen")
def test_warmup_subagents_default_opens_one(
    mock_popen: MagicMock,
    tmp_path: Path,
) -> None:
    """Test that warmup_subagents defaults to opening 1 workspace."""
    # Create 3 subagent directories
    for i in [1, 2, 3]:
        subagent_dir = tmp_path / f"subagent-{i}"
        subagent_dir.mkdir()
        workspace_file = subagent_dir / "subagent.code-workspace"
        workspace_file.write_text("{}", encoding="utf-8")
    
    # Don't specify subagents parameter (should default to 1)
    result = warmup_subagents(subagent_root=tmp_path)
    
    assert result == 0
    assert mock_popen.call_count == 1
