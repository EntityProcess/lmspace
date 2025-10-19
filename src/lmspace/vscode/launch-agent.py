"""Launch an agent in an isolated subagent environment."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional, Sequence

DEFAULT_LOCK_NAME = "subagent.lock"


def get_subagent_root() -> Path:
    """Get the root directory for subagents."""
    return Path.home() / ".ai-prompts" / "agents"


def find_unlocked_subagent(subagent_root: Path) -> Optional[Path]:
    """Find the first unlocked subagent directory.
    
    Returns the path to the first subagent-* directory that does not contain
    a subagent.lock file. Returns None if no unlocked subagents are found.
    """
    if not subagent_root.exists():
        return None
    
    subagents = sorted(
        (d for d in subagent_root.iterdir() if d.is_dir() and d.name.startswith("subagent-")),
        key=lambda d: int(d.name.split("-")[1])
    )
    
    for subagent_dir in subagents:
        lock_file = subagent_dir / DEFAULT_LOCK_NAME
        if not lock_file.exists():
            return subagent_dir
    
    return None


def copy_agent_config(
    agent_template_dir: Path,
    subagent_dir: Path,
) -> dict:
    """Copy agent configuration to subagent.
    
    Copies subagent.chatmode.md and subagent.code-workspace from the template
    to the subagent directory. Returns a dict with copied file paths.
    
    Raises FileNotFoundError if template files are missing.
    """
    chatmode_src = agent_template_dir / "subagent.chatmode.md"
    workspace_src = agent_template_dir / "subagent.code-workspace"
    
    if not chatmode_src.exists():
        raise FileNotFoundError(f"Template chatmode not found: {chatmode_src}")
    if not workspace_src.exists():
        raise FileNotFoundError(f"Template workspace not found: {workspace_src}")
    
    chatmode_dst = subagent_dir / "subagent.chatmode.md"
    workspace_dst = subagent_dir / "subagent.code-workspace"
    
    shutil.copy2(chatmode_src, chatmode_dst)
    shutil.copy2(workspace_src, workspace_dst)
    
    return {
        "chatmode": str(chatmode_dst.resolve()),
        "workspace": str(workspace_dst.resolve()),
    }


def create_subagent_lock(subagent_dir: Path) -> Path:
    """Create a lock file to mark the subagent as in-use.
    
    Returns the path to the created lock file.
    """
    lock_file = subagent_dir / DEFAULT_LOCK_NAME
    lock_file.touch()
    return lock_file


def launch_agent(
    user_query: str,
    agent_template_dir: Path,
    *,
    extra_attachments: Optional[Sequence[Path]] = None,
    dry_run: bool = False,
) -> int:
    """Launch an agent in an isolated subagent.
    
    Args:
        user_query: The user's input query for the agent.
        agent_template_dir: Path to the agent configuration directory that
            contains the chatmode and workspace files.
        extra_attachments: Additional attachment paths that should be forwarded
            to the launched chat.
        dry_run: When True, report planned actions without launching VS Code.
    
    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    try:
        # Validate template directory
        agent_template_dir = agent_template_dir.resolve()
        if not agent_template_dir.is_dir():
            raise FileNotFoundError(
                f"Agent template not found: {agent_template_dir}"
            )

        # Get subagent root
        subagent_root = get_subagent_root()
        
        # Find unlocked subagent
        subagent_dir = find_unlocked_subagent(subagent_root)
        if subagent_dir is None:
            print(
                "error: No unlocked subagents available. Please provision more subagents with:\n"
                "  uv run provision.py --subagents <count>",
                file=sys.stderr,
            )
            return 1
        
        # Copy agent configuration
        if not dry_run:
            try:
                copy_agent_config(agent_template_dir, subagent_dir)
            except FileNotFoundError as e:
                print(f"error: {e}", file=sys.stderr)
                return 1
        
        # Create subagent lock
        if not dry_run:
            try:
                create_subagent_lock(subagent_dir)
            except OSError as e:
                print(f"error: Failed to create subagent lock: {e}", file=sys.stderr)
                return 1
        
        resolved_extra: list[str] = []
        if extra_attachments:
            for attachment in extra_attachments:
                resolved_attachment = attachment.expanduser().resolve()
                if not resolved_attachment.exists():
                    raise FileNotFoundError(
                        f"Attachment not found: {resolved_attachment}"
                    )
                resolved_extra.append(str(resolved_attachment))

        attachment_paths: list[str] = resolved_extra
        
        # Report the launched subagent in a minimal JSON payload
        print(
            json.dumps(
                {
                    "success": True,
                    "subagent_name": subagent_dir.name,
                }
            )
        )
        
        # Launch VS Code with the workspace and chat
        if not dry_run:
            try:
                workspace_path = str(
                    (subagent_dir / "subagent.code-workspace").resolve()
                )
                attachment_args = " ".join(
                    f'-a "{attachment}"' for attachment in attachment_paths
                )
                chat_command = "code -r chat -m subagent"
                if attachment_args:
                    chat_command += f" {attachment_args}"
                chat_command += f' "{user_query}"'

                # Use PowerShell to launch code commands
                ps_cmd = (
                    f'code "{workspace_path}"; '
                    f'Start-Sleep -Seconds 1; '
                    f'code "{workspace_path}"; '
                    f"{chat_command}"
                )
                subprocess.Popen(["pwsh", "-Command", ps_cmd])
            except Exception as e:
                print(f"warning: Failed to launch VS Code: {e}", file=sys.stderr)
        
        return 0
    
    except Exception as e:
        print(
            json.dumps({"success": False, "error": str(e)}),
            file=sys.stdout,
        )
        return 1


def main() -> int:
    """Entry point for the launch script."""
    parser = argparse.ArgumentParser(
        description="Launch an agent in an isolated subagent environment."
    )
    parser.add_argument(
        "agent_config_path",
        type=Path,
        help=(
            "Path to the agent configuration directory (e.g., "
            "'domains/glow/agents/glow-ctf')"
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
    args = parser.parse_args()
    return launch_agent(
        args.query,
        args.agent_config_path,
        extra_attachments=args.attachment,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    sys.exit(main())
