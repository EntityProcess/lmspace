"""Provision copies of the subagent template for concurrent subagents."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path
from typing import List, Tuple

try:
    from .agent_dispatch import warmup_subagents  # type: ignore
except ImportError:  # pragma: no cover - fallback when executed as a script
    from lmspace.vscode.agent_dispatch import warmup_subagents

DEFAULT_LOCK_NAME = "subagent.lock"
DEFAULT_TEMPLATE_DIR = (
    Path(__file__).resolve().parent / "subagent_template"
)


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for provisioning subagent subagents."""
    parser = argparse.ArgumentParser(
        description=(
            "Copy the subagent template into %USERPROFILE%/.lmspace/vscode-agents "
            "so multiple VS Code instances can run isolated subagents."
        )
    )
    parser.add_argument(
        "--subagents",
        type=int,
        default=1,
        help="Number of subagent directories to provision.",
    )
    parser.add_argument(
        "--template",
        type=Path,
        default=DEFAULT_TEMPLATE_DIR,
        help=(
            "Path to the subagent subagent template. Defaults to the "
            "subagent_template directory that sits beside this script."
        ),
    )
    parser.add_argument(
        "--target-root",
        type=Path,
        default=Path.home() / ".lmspace" / "vscode-agents",
        help=(
            "Destination root for subagent directories. Defaults to "
            "%USERPROFILE%/.lmspace/vscode-agents."
        ),
    )
    parser.add_argument(
        "--lock-name",
        default=DEFAULT_LOCK_NAME,
        help=(
            "File name that marks a subagent as locked. Defaults to "
            f"{DEFAULT_LOCK_NAME}."
        ),
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Unlock and overwrite all subagent directories regardless of lock status.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show the planned operations without copying files.",
    )
    parser.add_argument(
        "--warmup",
        action="store_true",
        help=(
            "Warm up provisioned subagents after provisioning completes. "
            "Ignored during dry runs."
        ),
    )
    return parser.parse_args()


def provision_subagents(
    *,
    template: Path,
    target_root: Path,
    subagents: int,
    lock_name: str,
    force: bool,
    dry_run: bool,
) -> Tuple[List[Path], List[Path], List[Path]]:
    """Provision subagent directories and return summary lists.

    This function ensures there are at least `subagents` unlocked subagent directories.
    If there are fewer unlocked subagents than requested, it provisions additional ones
    with higher numbers.

    Returns three lists: created subagents, subagents skipped because they already
    existed, and subagents skipped because they were locked.
    """
    if subagents < 1:
        raise ValueError("subagents must be a positive integer")

    template_path = template.expanduser().resolve()
    target_path = target_root.expanduser().resolve()

    if not template_path.is_dir():
        raise ValueError(f"template path {template_path} is not a directory")

    if not dry_run:
        target_path.mkdir(parents=True, exist_ok=True)

    # First, scan existing subagents to count unlocked ones and find the highest number
    # Filter out directories that don't have a valid integer after "subagent-"
    existing_subagents = []
    if target_path.exists():
        for d in target_path.iterdir():
            if d.is_dir() and d.name.startswith("subagent-"):
                try:
                    int(d.name.split("-")[1])
                    existing_subagents.append(d)
                except (ValueError, IndexError):
                    # Skip directories that don't follow the subagent-N pattern
                    continue
        existing_subagents.sort(key=lambda d: int(d.name.split("-")[1]))

    unlocked_count = 0
    highest_number = 0
    locked_subagents = []

    for subagent_dir in existing_subagents:
        subagent_number = int(subagent_dir.name.split("-")[1])
        highest_number = max(highest_number, subagent_number)
        lock_file = subagent_dir / lock_name
        if not lock_file.exists():
            unlocked_count += 1
        else:
            locked_subagents.append(subagent_dir)

    created: List[Path] = []
    skipped_existing: List[Path] = []
    skipped_locked: List[Path] = locked_subagents

    # Provision subagents starting from 1 up to the number needed
    # When force is enabled, overwrite existing subagents up to the count needed
    # When force is disabled, only reuse unlocked subagents and skip locked ones
    subagents_provisioned = 0
    for index in range(1, highest_number + 1):
        if subagents_provisioned >= subagents:
            break
            
        subagent_dir = target_path / f"subagent-{index}"
        lock_file = subagent_dir / lock_name

        if subagent_dir.exists():
            # Skip locked subagents unless force is enabled
            if lock_file.exists() and not force:
                continue
            
            # When force is enabled, unlock and overwrite all existing subagents
            if force:
                if not dry_run:
                    # Remove lock file if it exists
                    if lock_file.exists():
                        lock_file.unlink()
                    # Copy only the workspace file
                    workspace_src = template_path / "subagent.code-workspace"
                    workspace_dst = subagent_dir / f"{subagent_dir.name}.code-workspace"
                    shutil.copy2(workspace_src, workspace_dst)
                    created.append(subagent_dir)
                else:
                    created.append(subagent_dir)
                # Remove from locked list since we're processing it
                if subagent_dir in locked_subagents:
                    locked_subagents.remove(subagent_dir)
                subagents_provisioned += 1
            elif not lock_file.exists():
                # Without force, unlocked subagent - skip it as it's already provisioned
                skipped_existing.append(subagent_dir)
                subagents_provisioned += 1
        else:
            # Subagent doesn't exist, create it
            if dry_run:
                created.append(subagent_dir)
            else:
                subagent_dir.mkdir(parents=True, exist_ok=True)
                # Copy only the workspace file
                workspace_src = template_path / "subagent.code-workspace"
                workspace_dst = subagent_dir / f"{subagent_dir.name}.code-workspace"
                shutil.copy2(workspace_src, workspace_dst)
                created.append(subagent_dir)
            subagents_provisioned += 1

    # Provision additional subagents beyond the highest existing number if needed
    while subagents_provisioned < subagents:
        index = highest_number + 1
        highest_number = index
        subagent_dir = target_path / f"subagent-{index}"

        if dry_run:
            created.append(subagent_dir)
        else:
            subagent_dir.mkdir(parents=True, exist_ok=True)
            # Copy only the workspace file
            workspace_src = template_path / "subagent.code-workspace"
            workspace_dst = subagent_dir / f"{subagent_dir.name}.code-workspace"
            shutil.copy2(workspace_src, workspace_dst)
            created.append(subagent_dir)
        subagents_provisioned += 1

    return created, skipped_existing, skipped_locked


def unlock_subagents(
    *,
    target_root: Path,
    lock_name: str,
    subagent_name: str | None = None,
    unlock_all: bool = False,
    dry_run: bool = False,
) -> List[Path]:
    """Unlock subagent(s) by removing their lock files.
    
    Args:
        target_root: Root directory containing subagent directories
        lock_name: Name of the lock file to remove
        subagent_name: Specific subagent folder name to unlock (e.g., subagent-1)
        unlock_all: If True, unlock all subagents
        dry_run: If True, show what would be done without making changes
    
    Returns:
        List of paths to subagent directories that were unlocked
    
    Raises:
        ValueError: If neither subagent_name nor unlock_all is specified,
                    or if both are specified, or if the subagent doesn't exist
    """
    if (subagent_name is None and not unlock_all) or (subagent_name is not None and unlock_all):
        raise ValueError("must specify either --subagent or --all (but not both)")
    
    target_path = target_root.expanduser().resolve()
    
    if not target_path.exists():
        raise ValueError(f"target root {target_path} does not exist")
    
    unlocked: List[Path] = []
    
    if unlock_all:
        # Find all subagent directories and unlock them
        subagents = sorted(
            (d for d in target_path.iterdir() if d.is_dir() and d.name.startswith("subagent-")),
            key=lambda d: int(d.name.split("-")[1])
        )
        
        for subagent_dir in subagents:
            lock_file = subagent_dir / lock_name
            if lock_file.exists():
                if not dry_run:
                    lock_file.unlink()
                unlocked.append(subagent_dir)
    else:
        # Unlock specific subagent
        subagent_dir = target_path / subagent_name
        
        if not subagent_dir.exists():
            raise ValueError(f"{subagent_name} does not exist in {target_path}")
        
        lock_file = subagent_dir / lock_name
        if lock_file.exists():
            if not dry_run:
                lock_file.unlink()
            unlocked.append(subagent_dir)
    
    return unlocked


def main() -> int:
    """Entry point for the provisioning script."""
    args = parse_args()

    try:
        created, skipped_existing, skipped_locked = provision_subagents(
            template=args.template,
            target_root=args.target_root,
            subagents=args.subagents,
            lock_name=args.lock_name,
            force=args.force,
            dry_run=args.dry_run,
        )
    except ValueError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    # Calculate total unlocked subagents
    total_unlocked = len(created) + len(skipped_existing)
    
    if created:
        print("created subagents:")
        for path in created:
            print(f"  {path}")

    if skipped_existing:
        print("skipped existing unlocked subagents:")
        for path in skipped_existing:
            print(f"  {path}")

    if skipped_locked:
        print("skipped locked subagents:")
        for path in skipped_locked:
            print(f"  {path}")

    if not any([created, skipped_existing, skipped_locked]):
        print("no operations were required")
    
    if total_unlocked > 0:
        print(f"\ntotal unlocked subagents available: {total_unlocked}")

    if args.dry_run:
        print("dry run complete; no changes were made")
        if args.warmup:
            print("warmup skipped because this was a dry run")
        return 0

    if args.warmup:
        warmup_exit = warmup_subagents(
            subagent_root=args.target_root,
            subagents=args.subagents,
            dry_run=False,
        )
        if warmup_exit != 0:
            return warmup_exit

    return 0


if __name__ == "__main__":
    sys.exit(main())
