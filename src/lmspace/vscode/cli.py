"""CLI handlers for VS Code workspace agent commands."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from .provision import provision_subagents, DEFAULT_TEMPLATE_DIR, DEFAULT_LOCK_NAME
from .launch_agent import launch_agent


def add_provision_parser(subparsers: Any) -> None:
    """Add the 'provision' subcommand parser."""
    parser = subparsers.add_parser(
        "provision",
        help="Provision subagent workspace directories",
        description=(
            "Copy the subagent template into ~/.ai-prompts/agents "
            "so multiple VS Code instances can run isolated subagents."
        ),
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
            "Path to the subagent template. Defaults to the "
            "built-in subagent_template directory."
        ),
    )
    parser.add_argument(
        "--target-root",
        type=Path,
        default=Path.home() / ".ai-prompts" / "agents",
        help=(
            "Destination root for subagent directories. Defaults to "
            "~/.ai-prompts/agents."
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


def add_chat_parser(subparsers: Any) -> None:
    """Add the 'chat' subcommand parser."""
    parser = subparsers.add_parser(
        "chat",
        help="Start a chat with an agent in an isolated subagent workspace",
        description="Start a chat with an agent in an isolated subagent environment.",
    )
    parser.add_argument(
        "agent_config_path",
        type=Path,
        help=(
            "Path to the agent configuration directory (e.g., "
            "'agents/glow-ctf')"
        ),
    )
    parser.add_argument(
        "query",
        help="User query to pass to the agent",
    )
    parser.add_argument(
        "--attachment",
        action="append",
        type=Path,
        default=None,
        help=(
            "Additional attachment to forward to the chat. "
            "Repeat for multiple attachments."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be done without making changes",
    )


def handle_provision(args: argparse.Namespace) -> int:
    """Handle the 'provision' subcommand."""
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


def handle_chat(args: argparse.Namespace) -> int:
    """Handle the 'chat' subcommand."""
    return launch_agent(
        args.query,
        args.agent_config_path,
        extra_attachments=args.attachment,
        dry_run=args.dry_run,
    )
