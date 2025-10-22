"""CLI handlers for VS Code workspace agent commands."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .provision import provision_subagents, DEFAULT_TEMPLATE_DIR, DEFAULT_LOCK_NAME
from .launch_agent import launch_agent, warmup_subagents, get_subagent_root
from .transpiler import (
    SkillResolutionError,
    SubagentDefinitionError,
    transpile_subagent,
)

def add_provision_parser(subparsers: Any) -> None:
    """Add the 'provision' subcommand parser."""
    parser = subparsers.add_parser(
        "provision",
        help="Provision subagent workspace directories",
        description=(
            "Copy the subagent template into ~/.lmspace/vscode-agents "
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
        default=Path.home() / ".lmspace" / "vscode-agents",
        help=(
            "Destination root for subagent directories. Defaults to "
            "~/.lmspace/vscode-agents."
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
        help="Overwrite unlocked subagent directories even if they already exist.",
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
        "-a", "--attachment",
        action="append",
        type=Path,
        default=None,
        help=(
            "Additional attachment to forward to the chat. "
            "Repeat for multiple attachments."
        ),
    )
    parser.add_argument(
        "--workspace-root",
        type=Path,
        default=None,
        help=(
            "Optional workspace root whose contexts/ directory is checked after the agent's contexts."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be done without making changes",
    )
    parser.add_argument(
        "-w", "--wait",
        action="store_true",
        help="Wait for response and print to stdout (sync mode). Default is async mode.",
    )


def add_warmup_parser(subparsers: Any) -> None:
    """Add the 'warmup' subcommand parser."""
    parser = subparsers.add_parser(
        "warmup",
        help="Open all provisioned VSCode workspaces to warm them up",
        description=(
            "Open all provisioned subagent workspaces in VSCode. "
            "This preloads the workspaces so they're ready for agent launches."
        ),
    )
    parser.add_argument(
        "--subagents",
        type=int,
        default=1,
        help="Number of subagent workspaces to open. Defaults to 1.",
    )
    parser.add_argument(
        "--target-root",
        type=Path,
        default=None,
        help=(
            "Root directory containing subagents. Defaults to "
            "~/.lmspace/vscode-agents."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show which workspaces would be opened without opening them",
    )


def add_unlock_parser(subparsers: Any) -> None:
    """Add the 'unlock' subcommand parser."""
    parser = subparsers.add_parser(
        "unlock",
        help="Unlock subagent(s) by removing their lock files",
        description=(
            "Remove lock files from subagent directories to make them "
            "available for new agent launches. Use --subagent to unlock "
            "a specific subagent or --all to unlock all subagents."
        ),
    )
    parser.add_argument(
        "--subagent",
        type=int,
        default=None,
        help="Subagent number to unlock (e.g., 1 for subagent-1).",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        dest="unlock_all",
        help="Unlock all subagents.",
    )
    parser.add_argument(
        "--target-root",
        type=Path,
        default=Path.home() / ".lmspace" / "vscode-agents",
        help=(
            "Root directory containing subagents. Defaults to "
            "~/.lmspace/vscode-agents."
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
        "--dry-run",
        action="store_true",
        help="Show what would be unlocked without making changes.",
    )


def handle_provision(args: argparse.Namespace) -> int:
    """Handle the 'provision' subcommand."""
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


def handle_chat(args: argparse.Namespace) -> int:
    """Handle the 'chat' subcommand."""
    return launch_agent(
        args.query,
        args.agent_config_path,
        extra_attachments=args.attachment,
        dry_run=args.dry_run,
        wait=args.wait,
        workspace_root=args.workspace_root,
    )


def handle_warmup(args: argparse.Namespace) -> int:
    """Handle the 'warmup' subcommand."""
    subagent_root = args.target_root if args.target_root else get_subagent_root()
    return warmup_subagents(
        subagent_root=subagent_root,
        subagents=args.subagents,
        dry_run=args.dry_run,
    )


def handle_unlock(args: argparse.Namespace) -> int:
    """Handle the 'unlock' subcommand."""
    from .provision import unlock_subagents
    
    try:
        unlocked = unlock_subagents(
            target_root=args.target_root,
            lock_name=args.lock_name,
            subagent_number=args.subagent,
            unlock_all=args.unlock_all,
            dry_run=args.dry_run,
        )
    except ValueError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    
    if unlocked:
        print("unlocked subagents:")
        for path in unlocked:
            print(f"  {path}")
    else:
        if args.unlock_all:
            print("no locked subagents found")
        else:
            print(f"subagent-{args.subagent} was not locked")
    
    if args.dry_run:
        print("dry run complete; no changes were made")
    
    return 0


def add_transpile_parser(subparsers: Any) -> None:
    """Add the 'transpile' subcommand parser."""
    parser = subparsers.add_parser(
        "transpile",
        help="Generate a chatmode file from SUBAGENT.md",
        description=(
            "Compose subagent.chatmode.md from SUBAGENT.md and optional "
            "skill snippets."
        ),
    )
    parser.add_argument(
        "agent_config_path",
        type=Path,
        help="Path to the agent configuration directory containing SUBAGENT.md",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help=(
            "Optional path for the generated chatmode file. Defaults to "
            "<agent>/subagent.chatmode.md."
        ),
    )
    parser.add_argument(
        "--workspace-root",
        type=Path,
        default=None,
        help=(
            "Optional workspace root whose contexts/ directory is searched "
            "after the agent for skill snippets."
        ),
    )


def handle_transpile(args: argparse.Namespace) -> int:
    """Handle the 'transpile' subcommand."""
    try:
        output_path = transpile_subagent(
            args.agent_config_path,
            output_path=args.output,
            workspace_root=args.workspace_root,
        )
    except (FileNotFoundError, SubagentDefinitionError, SkillResolutionError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    print(f"generated chatmode: {output_path}")
    return 0


def add_skills_parser(subparsers: Any) -> None:
    """Add the 'skills' subcommand parser."""
    parser = subparsers.add_parser(
        "skills",
        help="Resolve skill file paths for an agent",
        description=(
            "Read SUBAGENT.md frontmatter and resolve skill file paths. "
            "Returns JSON array of absolute paths."
        ),
    )
    parser.add_argument(
        "agent_config_path",
        type=Path,
        help="Path to the agent configuration directory containing SUBAGENT.md",
    )
    parser.add_argument(
        "--workspace-root",
        type=Path,
        default=None,
        help=(
            "Optional workspace root whose contexts/ directory is searched "
            "for skill files."
        ),
    )


def handle_skills(args: argparse.Namespace) -> int:
    """Handle the 'skills' subcommand."""
    from .transpiler import (
        _load_subagent_definition,
        _resolve_skill_body,
        SKILL_SUFFIX,
    )
    
    try:
        agent_dir = args.agent_config_path.resolve()
        _, _, skills, _ = _load_subagent_definition(agent_dir)
        
        skill_paths = []
        for skill in skills:
            # Use the same resolution logic as transpiler
            skill_filename = f"{skill}{SKILL_SUFFIX}"
            
            # Search order matches _resolve_skill_body
            locations_to_check = [
                agent_dir / skill_filename,
            ]
            
            if agent_dir.parent.name == "agents":
                agents_folder = agent_dir.parent
                locations_to_check.append(agents_folder / skill_filename)
                workspace_contexts = agents_folder.parent / "contexts" / skill_filename
                locations_to_check.append(workspace_contexts)
            
            if args.workspace_root is not None:
                workspace_skill = args.workspace_root / "contexts" / skill_filename
                if workspace_skill not in locations_to_check:
                    locations_to_check.append(workspace_skill)
            
            # Find first existing path
            found = None
            for path in locations_to_check:
                if path.exists():
                    found = str(path.resolve())
                    break
            
            if found:
                skill_paths.append(found)
            else:
                print(
                    f"error: skill '{skill}' not found",
                    file=sys.stderr,
                )
                return 1
        
        # Output JSON array
        print(json.dumps(skill_paths))
        return 0
        
    except (FileNotFoundError, SubagentDefinitionError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


