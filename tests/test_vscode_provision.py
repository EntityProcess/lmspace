"""Tests for VS Code workspace agent provisioning."""

from __future__ import annotations

from argparse import Namespace
from pathlib import Path

import pytest

from lmspace.vscode.provision import provision_subagents, DEFAULT_LOCK_NAME
from lmspace.vscode.cli import handle_provision


@pytest.fixture
def template_dir(tmp_path: Path) -> Path:
    """Create a minimal template directory."""
    template = tmp_path / "template"
    template.mkdir()
    (template / "subagent.chatmode.md").write_text("# Test chatmode\n")
    (template / "subagent.code-workspace").write_text("{}\n")
    return template


@pytest.fixture
def target_root(tmp_path: Path) -> Path:
    """Create a target root directory."""
    target = tmp_path / "agents"
    target.mkdir()
    return target


def test_provision_single_subagent(template_dir: Path, target_root: Path) -> None:
    """Test provisioning a single subagent."""
    created, skipped_existing, skipped_locked = provision_subagents(
        template=template_dir,
        target_root=target_root,
        subagents=1,
        lock_name=DEFAULT_LOCK_NAME,
        refresh=False,
        dry_run=False,
    )

    assert len(created) == 1
    assert len(skipped_existing) == 0
    assert len(skipped_locked) == 0

    subagent_dir = target_root / "subagent-1"
    assert subagent_dir.exists()
    assert (subagent_dir / "subagent.chatmode.md").exists()
    assert (subagent_dir / "subagent.code-workspace").exists()


def test_provision_multiple_subagents(template_dir: Path, target_root: Path) -> None:
    """Test provisioning multiple subagents."""
    created, skipped_existing, skipped_locked = provision_subagents(
        template=template_dir,
        target_root=target_root,
        subagents=3,
        lock_name=DEFAULT_LOCK_NAME,
        refresh=False,
        dry_run=False,
    )

    assert len(created) == 3
    assert len(skipped_existing) == 0
    assert len(skipped_locked) == 0

    for i in range(1, 4):
        subagent_dir = target_root / f"subagent-{i}"
        assert subagent_dir.exists()


def test_provision_skip_existing(template_dir: Path, target_root: Path) -> None:
    """Test that existing unlocked subagents are skipped without --refresh."""
    # Create initial subagent
    provision_subagents(
        template=template_dir,
        target_root=target_root,
        subagents=1,
        lock_name=DEFAULT_LOCK_NAME,
        refresh=False,
        dry_run=False,
    )

    # Provision again without refresh
    created, skipped_existing, skipped_locked = provision_subagents(
        template=template_dir,
        target_root=target_root,
        subagents=1,
        lock_name=DEFAULT_LOCK_NAME,
        refresh=False,
        dry_run=False,
    )

    assert len(created) == 0
    assert len(skipped_existing) == 1
    assert len(skipped_locked) == 0


def test_provision_skip_locked(template_dir: Path, target_root: Path) -> None:
    """Test that locked subagents are always skipped."""
    # Create initial subagent
    provision_subagents(
        template=template_dir,
        target_root=target_root,
        subagents=1,
        lock_name=DEFAULT_LOCK_NAME,
        refresh=False,
        dry_run=False,
    )

    # Create lock file
    lock_file = target_root / "subagent-1" / DEFAULT_LOCK_NAME
    lock_file.touch()

    # Try to provision with refresh
    created, skipped_existing, skipped_locked = provision_subagents(
        template=template_dir,
        target_root=target_root,
        subagents=1,
        lock_name=DEFAULT_LOCK_NAME,
        refresh=True,
        dry_run=False,
    )

    assert len(created) == 0
    assert len(skipped_existing) == 0
    assert len(skipped_locked) == 1


def test_provision_refresh_unlocked(template_dir: Path, target_root: Path) -> None:
    """Test that unlocked subagents are rebuilt with --refresh."""
    # Create initial subagent
    provision_subagents(
        template=template_dir,
        target_root=target_root,
        subagents=1,
        lock_name=DEFAULT_LOCK_NAME,
        refresh=False,
        dry_run=False,
    )

    # Add a marker file
    marker = target_root / "subagent-1" / "marker.txt"
    marker.write_text("should be deleted")

    # Provision with refresh
    created, skipped_existing, skipped_locked = provision_subagents(
        template=template_dir,
        target_root=target_root,
        subagents=1,
        lock_name=DEFAULT_LOCK_NAME,
        refresh=True,
        dry_run=False,
    )

    assert len(created) == 1
    assert len(skipped_existing) == 0
    assert len(skipped_locked) == 0

    # Marker should be gone
    assert not marker.exists()


def test_provision_dry_run(template_dir: Path, target_root: Path) -> None:
    """Test that dry run doesn't create files."""
    created, skipped_existing, skipped_locked = provision_subagents(
        template=template_dir,
        target_root=target_root,
        subagents=2,
        lock_name=DEFAULT_LOCK_NAME,
        refresh=False,
        dry_run=True,
    )

    assert len(created) == 2
    assert len(skipped_existing) == 0
    assert len(skipped_locked) == 0

    # Nothing should actually exist
    assert not (target_root / "subagent-1").exists()
    assert not (target_root / "subagent-2").exists()


def test_provision_invalid_template(target_root: Path) -> None:
    """Test that invalid template path raises an error."""
    with pytest.raises(ValueError, match="not a directory"):
        provision_subagents(
            template=Path("/nonexistent/path"),
            target_root=target_root,
            subagents=1,
            lock_name=DEFAULT_LOCK_NAME,
            refresh=False,
            dry_run=False,
        )


def test_provision_zero_subagents(template_dir: Path, target_root: Path) -> None:
    """Test that zero subagents raises an error."""
    with pytest.raises(ValueError, match="positive integer"):
        provision_subagents(
            template=template_dir,
            target_root=target_root,
            subagents=0,
            lock_name=DEFAULT_LOCK_NAME,
            refresh=False,
            dry_run=False,
        )


def test_handle_provision_runs_warmup(
    template_dir: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ensure handle_provision triggers warmup when requested."""

    target_root = tmp_path / "agents"
    args = Namespace(
        template=template_dir,
        target_root=target_root,
        subagents=1,
        lock_name=DEFAULT_LOCK_NAME,
        refresh=False,
        dry_run=False,
        warmup=True,
    )

    warmup_calls: dict[str, object] = {}

    def fake_warmup(*, subagent_root: Path, subagents: int, dry_run: bool) -> int:
        warmup_calls["root"] = subagent_root
        warmup_calls["count"] = subagents
        warmup_calls["dry_run"] = dry_run
        return 0

    monkeypatch.setattr("lmspace.vscode.cli.warmup_subagents", fake_warmup)

    result = handle_provision(args)

    assert result == 0
    assert warmup_calls == {
        "root": target_root,
        "count": 1,
        "dry_run": False,
    }


def test_handle_provision_skips_warmup_during_dry_run(
    template_dir: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ensure warmup is not triggered when provisioning is a dry run."""

    target_root = tmp_path / "agents"
    args = Namespace(
        template=template_dir,
        target_root=target_root,
        subagents=1,
        lock_name=DEFAULT_LOCK_NAME,
        refresh=False,
        dry_run=True,
        warmup=True,
    )

    def fake_warmup(*args: object, **kwargs: object) -> int:  # pragma: no cover
        raise AssertionError("warmup should not be called during dry run")

    monkeypatch.setattr("lmspace.vscode.cli.warmup_subagents", fake_warmup)

    result = handle_provision(args)

    assert result == 0
