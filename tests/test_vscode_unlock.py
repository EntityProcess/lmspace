"""Tests for unlock functionality in vscode.provision."""

from __future__ import annotations

from pathlib import Path

import pytest

from lmspace.vscode.provision import unlock_subagents, DEFAULT_LOCK_NAME


@pytest.fixture
def target_root_with_locks(tmp_path: Path) -> Path:
    """Create a target root with some locked and unlocked subagents."""
    root = tmp_path / "agents"
    root.mkdir()
    
    # Create three subagents: 1 and 3 locked, 2 unlocked
    for i in [1, 2, 3]:
        subagent_dir = root / f"subagent-{i}"
        subagent_dir.mkdir()
        
        if i in [1, 3]:
            lock_file = subagent_dir / DEFAULT_LOCK_NAME
            lock_file.touch()
    
    return root


def test_unlock_specific_subagent(target_root_with_locks: Path) -> None:
    """Test unlocking a specific locked subagent."""
    unlocked = unlock_subagents(
        target_root=target_root_with_locks,
        lock_name=DEFAULT_LOCK_NAME,
        subagent_number=1,
        unlock_all=False,
        dry_run=False,
    )
    
    assert len(unlocked) == 1
    assert unlocked[0].name == "subagent-1"
    
    # Verify lock file was removed
    lock_file = target_root_with_locks / "subagent-1" / DEFAULT_LOCK_NAME
    assert not lock_file.exists()
    
    # Verify other locks are still in place
    lock_file_3 = target_root_with_locks / "subagent-3" / DEFAULT_LOCK_NAME
    assert lock_file_3.exists()


def test_unlock_specific_subagent_not_locked(target_root_with_locks: Path) -> None:
    """Test unlocking a subagent that's not locked returns empty list."""
    unlocked = unlock_subagents(
        target_root=target_root_with_locks,
        lock_name=DEFAULT_LOCK_NAME,
        subagent_number=2,
        unlock_all=False,
        dry_run=False,
    )
    
    assert len(unlocked) == 0


def test_unlock_all_subagents(target_root_with_locks: Path) -> None:
    """Test unlocking all locked subagents."""
    unlocked = unlock_subagents(
        target_root=target_root_with_locks,
        lock_name=DEFAULT_LOCK_NAME,
        subagent_number=None,
        unlock_all=True,
        dry_run=False,
    )
    
    assert len(unlocked) == 2
    assert unlocked[0].name == "subagent-1"
    assert unlocked[1].name == "subagent-3"
    
    # Verify all lock files were removed
    for i in [1, 3]:
        lock_file = target_root_with_locks / f"subagent-{i}" / DEFAULT_LOCK_NAME
        assert not lock_file.exists()


def test_unlock_dry_run_specific(target_root_with_locks: Path) -> None:
    """Test that dry run doesn't remove lock files for specific subagent."""
    unlocked = unlock_subagents(
        target_root=target_root_with_locks,
        lock_name=DEFAULT_LOCK_NAME,
        subagent_number=1,
        unlock_all=False,
        dry_run=True,
    )
    
    assert len(unlocked) == 1
    assert unlocked[0].name == "subagent-1"
    
    # Verify lock file still exists
    lock_file = target_root_with_locks / "subagent-1" / DEFAULT_LOCK_NAME
    assert lock_file.exists()


def test_unlock_dry_run_all(target_root_with_locks: Path) -> None:
    """Test that dry run doesn't remove lock files when unlocking all."""
    unlocked = unlock_subagents(
        target_root=target_root_with_locks,
        lock_name=DEFAULT_LOCK_NAME,
        subagent_number=None,
        unlock_all=True,
        dry_run=True,
    )
    
    assert len(unlocked) == 2
    
    # Verify lock files still exist
    for i in [1, 3]:
        lock_file = target_root_with_locks / f"subagent-{i}" / DEFAULT_LOCK_NAME
        assert lock_file.exists()


def test_unlock_nonexistent_subagent(tmp_path: Path) -> None:
    """Test that unlocking a nonexistent subagent raises ValueError."""
    root = tmp_path / "agents"
    root.mkdir()
    
    with pytest.raises(ValueError, match="does not exist"):
        unlock_subagents(
            target_root=root,
            lock_name=DEFAULT_LOCK_NAME,
            subagent_number=99,
            unlock_all=False,
            dry_run=False,
        )


def test_unlock_nonexistent_root(tmp_path: Path) -> None:
    """Test that unlocking from a nonexistent root raises ValueError."""
    root = tmp_path / "nonexistent"
    
    with pytest.raises(ValueError, match="does not exist"):
        unlock_subagents(
            target_root=root,
            lock_name=DEFAULT_LOCK_NAME,
            subagent_number=1,
            unlock_all=False,
            dry_run=False,
        )


def test_unlock_missing_both_flags(target_root_with_locks: Path) -> None:
    """Test that not specifying --subagent or --all raises ValueError."""
    with pytest.raises(ValueError, match="must specify either"):
        unlock_subagents(
            target_root=target_root_with_locks,
            lock_name=DEFAULT_LOCK_NAME,
            subagent_number=None,
            unlock_all=False,
            dry_run=False,
        )


def test_unlock_both_flags_specified(target_root_with_locks: Path) -> None:
    """Test that specifying both --subagent and --all raises ValueError."""
    with pytest.raises(ValueError, match="must specify either"):
        unlock_subagents(
            target_root=target_root_with_locks,
            lock_name=DEFAULT_LOCK_NAME,
            subagent_number=1,
            unlock_all=True,
            dry_run=False,
        )


def test_unlock_all_when_none_locked(tmp_path: Path) -> None:
    """Test that unlocking all when no subagents are locked returns empty list."""
    root = tmp_path / "agents"
    root.mkdir()
    
    # Create unlocked subagents
    for i in [1, 2]:
        subagent_dir = root / f"subagent-{i}"
        subagent_dir.mkdir()
    
    unlocked = unlock_subagents(
        target_root=root,
        lock_name=DEFAULT_LOCK_NAME,
        subagent_number=None,
        unlock_all=True,
        dry_run=False,
    )
    
    assert len(unlocked) == 0
