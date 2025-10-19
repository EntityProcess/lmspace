"""Provision copies of the subagent template for concurrent subagents."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path
from typing import List, Tuple

DEFAULT_LOCK_NAME = "subagent.lock"
DEFAULT_TEMPLATE_DIR = (
    Path(__file__).resolve().parent / "subagent_template"
)


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for provisioning subagent subagents."""
    parser = argparse.ArgumentParser(
        description=(
            "Copy the subagent template into %USERPROFILE%/.ai-prompts/agents "
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
        default=Path.home() / ".ai-prompts" / "agents",
        help=(
            "Destination root for subagent directories. Defaults to "
            "%USERPROFILE%/.ai-prompts/agents."
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
        "--refresh",
        action="store_true",
        help="Rebuild unlocked subagents even if they already exist.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show the planned operations without copying files.",
    )
    return parser.parse_args()


def provision_subagents(
    *,
    template: Path,
    target_root: Path,
    subagents: int,
    lock_name: str,
    refresh: bool,
    dry_run: bool,
) -> Tuple[List[Path], List[Path], List[Path]]:
    """Provision subagent directories and return summary lists.

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

    created: List[Path] = []
    skipped_existing: List[Path] = []
    skipped_locked: List[Path] = []

    for index in range(1, subagents + 1):
        subagent_dir = target_path / f"subagent-{index}"
        lock_file = subagent_dir / lock_name

        if subagent_dir.exists():
            if lock_file.exists():
                skipped_locked.append(subagent_dir)
                continue
            if refresh:
                if dry_run:
                    skipped_existing.append(subagent_dir)
                else:
                    shutil.rmtree(subagent_dir)
            else:
                skipped_existing.append(subagent_dir)
                continue

        if dry_run:
            created.append(subagent_dir)
            continue

        shutil.copytree(
            template_path,
            subagent_dir,
            ignore=shutil.ignore_patterns(
                "__pycache__",
                "*.pyc",
                "*.pyo",
                DEFAULT_LOCK_NAME,
            ),
        )
        created.append(subagent_dir)

    return created, skipped_existing, skipped_locked


def main() -> int:
    """Entry point for the provisioning script."""
    args = parse_args()

    try:
        created, skipped_existing, skipped_locked = provision_subagents(
            template=args.template,
            target_root=args.target_root,
            subagents=args.subagents,
            lock_name=args.lock_name,
            refresh=args.refresh,
            dry_run=args.dry_run,
        )
    except ValueError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    if created:
        print("created subagents:")
        for path in created:
            print(f"  {path}")

    if skipped_existing:
        print("skipped existing subagents:")
        for path in skipped_existing:
            print(f"  {path}")

    if skipped_locked:
        print("skipped locked subagents:")
        for path in skipped_locked:
            print(f"  {path}")

    if not any([created, skipped_existing, skipped_locked]):
        print("no operations were required")

    if args.dry_run:
        print("dry run complete; no changes were made")

    return 0


if __name__ == "__main__":
    sys.exit(main())
