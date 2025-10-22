"""Launch an agent in an isolated subagent environment."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Sequence

from .transpiler import (
    SkillResolutionError,
    SkillDefinitionError,
    transpile_skill,
)

DEFAULT_LOCK_NAME = "subagent.lock"


def get_subagent_root() -> Path:
    """Get the root directory for subagents."""
    return Path.home() / ".lmspace" / "vscode-agents"


def get_all_subagent_workspaces(subagent_root: Path) -> list[Path]:
    """Get all subagent workspace files.
    
    Returns a list of paths to all subagent.code-workspace files in the
    subagent root directory, sorted by subagent number.
    """
    if not subagent_root.exists():
        return []
    
    subagents = sorted(
        (d for d in subagent_root.iterdir() if d.is_dir() and d.name.startswith("subagent-")),
        key=lambda d: int(d.name.split("-")[1])
    )
    
    workspaces = []
    for subagent_dir in subagents:
        workspace_file = subagent_dir / "subagent.code-workspace"
        if workspace_file.exists():
            workspaces.append(workspace_file)
    
    return workspaces


def get_default_template_dir() -> Path:
    """Get the default subagent template directory."""
    return Path(__file__).parent / "subagent_template"


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
    *,
    workspace_root: Optional[Path] = None,
) -> dict:
    """Transpile chatmode and copy workspace assets into the subagent directory."""
    workspace_src = agent_template_dir / "subagent.code-workspace"

    if not workspace_src.exists():
        default_template_dir = get_default_template_dir()
        workspace_src = default_template_dir / "subagent.code-workspace"
        if not workspace_src.exists():
            raise FileNotFoundError(f"Default workspace template not found: {workspace_src}")

    chatmode_dst = subagent_dir / "subagent.chatmode.md"
    workspace_dst = subagent_dir / "subagent.code-workspace"

    transpile_skill(
        agent_template_dir,
        output_path=chatmode_dst,
        workspace_root=workspace_root,
    )
    shutil.copy2(workspace_src, workspace_dst)

    messages_dir = subagent_dir / "messages"
    messages_dir.mkdir(exist_ok=True)

    return {
        "chatmode": str(chatmode_dst.resolve()),
        "workspace": str(workspace_dst.resolve()),
        "messages_dir": str(messages_dir.resolve()),
    }


def create_subagent_lock(subagent_dir: Path) -> Path:
    """Create a lock file to mark the subagent as in-use.
    
    Also clears any existing messages from previous runs.
    
    Returns the path to the created lock file.
    """
    # Clear existing messages
    messages_dir = subagent_dir / "messages"
    if messages_dir.exists():
        for msg_file in messages_dir.iterdir():
            if msg_file.is_file():
                msg_file.unlink()
    
    lock_file = subagent_dir / DEFAULT_LOCK_NAME
    lock_file.touch()
    return lock_file


def remove_subagent_lock(subagent_dir: Path) -> None:
    """Remove the lock file to mark the subagent as available.
    
    Silently succeeds if the lock file doesn't exist.
    """
    lock_file = subagent_dir / DEFAULT_LOCK_NAME
    lock_file.unlink(missing_ok=True)


def wait_for_response_output(
    response_file_tmp: Path,
    response_file_final: Path,
    *,
    poll_interval: float = 1.0,
) -> bool:
    """Wait for the agent to finalize the response and print it."""
    print(
        f"waiting for agent to finish: {response_file_final}",
        file=sys.stderr,
        flush=True,
    )

    try:
        while not response_file_final.exists():
            time.sleep(poll_interval)
    except KeyboardInterrupt:
        print(
            "\ninfo: interrupted while waiting for agent response.",
            file=sys.stderr,
        )
        return False

    read_attempts = 0
    max_attempts = 10
    while True:
        try:
            content = response_file_final.read_text(encoding="utf-8")
            break
        except OSError as exc:  # Handles sharing violations on Windows
            read_attempts += 1
            if read_attempts >= max_attempts:
                print(
                    f"error: failed to read agent response: {exc}",
                    file=sys.stderr,
                )
                return False
            time.sleep(poll_interval)

    print(content)
    return True


def launch_agent(
    user_query: str,
    agent_template_dir: Path,
    *,
    extra_attachments: Optional[Sequence[Path]] = None,
    dry_run: bool = False,
    wait: bool = False,
    workspace_root: Optional[Path] = None,
) -> int:
    """Launch an agent in an isolated subagent.
    
    Args:
        user_query: The user's input query for the agent.
        agent_template_dir: Path to the agent configuration directory that
            contains the chatmode and workspace files.
        extra_attachments: Additional attachment paths that should be forwarded
            to the launched chat.
        dry_run: When True, report planned actions without launching VS Code.
        wait: When True, wait for response and print to stdout (sync mode).
              When False (default), return immediately after launch (async mode).
        workspace_root: Optional workspace root whose contexts/ directory supplements agent-scoped skills.
    
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
                "error: No unlocked subagents available. Provision additional subagents with:\n"
                "  lmspace code provision --subagents <desired_total>",
                file=sys.stderr,
            )
            return 1
        
        # Copy agent configuration
        if not dry_run:
            try:
                copy_agent_config(
                    agent_template_dir,
                    subagent_dir,
                    workspace_root=workspace_root,
                )
            except (FileNotFoundError, SkillDefinitionError, SkillResolutionError) as error:
                print(f"error: {error}", file=sys.stderr)
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

        # Add the transpiled chatmode as an attachment
        chatmode_path = subagent_dir / "subagent.chatmode.md"
        attachment_paths: list[str] = [str(chatmode_path)] + resolved_extra
        
        # Generate timestamp for response file
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        messages_dir = subagent_dir / "messages"
        response_file_tmp = messages_dir / f"{timestamp}_res.tmp.md"
        response_file_final = messages_dir / f"{timestamp}_res.md"
        
        # Create SudoLang prompt with user query and save instructions
        lock_file = subagent_dir / DEFAULT_LOCK_NAME
        sudolang_prompt = f"""[[ ## task ## ]]
{user_query}

[[ ## system_instructions ## ]]

**IMPORTANT**: Follow these exact steps:
1. Create and write your complete response to: {response_file_tmp}
2. When completely finished, run these PowerShell commands to signal completion:
   Move-Item -LiteralPath '{response_file_tmp}' -Destination '{response_file_final}'
   Remove-Item -LiteralPath '{lock_file}' -Force

Do not proceed to step 2 until your response is completely written to the temporary file.
"""
        
        # Report the launched subagent in a minimal JSON payload
        print(
            json.dumps(
                {
                    "success": True,
                    "subagent_name": subagent_dir.name,
                    "response_file": str(response_file_final),
                }
            )
        )
        sys.stdout.flush()
        
        # Launch VS Code with the workspace and chat
        if dry_run:
            return 0

        launch_success = True
        if not dry_run:
            try:
                workspace_path = str(
                    (subagent_dir / "subagent.code-workspace").resolve()
                )
                
                # Use shell=True on all platforms to find 'code' in PATH
                # This handles code.cmd on Windows and code script on Unix
                
                # Open the workspace first
                subprocess.Popen(f'code "{workspace_path}"', shell=True)
                
                # Small delay to let workspace open
                time.sleep(1)
                
                # Open workspace again to ensure it's focused
                subprocess.Popen(f'code "{workspace_path}"', shell=True)
                
                # Write SudoLang prompt to a req.md file in the messages directory
                req_file = messages_dir / f"{timestamp}_req.md"
                req_file.write_text(sudolang_prompt, encoding='utf-8')
                
                # Build chat command with req.md file as attachment
                chat_cmd = f'code -r chat -m subagent'
                
                # Add attachments
                for attachment in attachment_paths:
                    chat_cmd += f' -a "{attachment}"'
                
                # Add the req.md file as an attachment
                chat_cmd += f' -a "{req_file}"'
                
                # Add a simple prompt that references the req.md file
                chat_cmd += f' "Follow the instructions in {req_file.name}"'
                
                subprocess.Popen(chat_cmd, shell=True)
                    
            except Exception as e:
                print(f"warning: Failed to launch VS Code: {e}", file=sys.stderr)
                launch_success = False
        
        if not launch_success:
            return 1

        # Async mode (default): return immediately with file paths
        if not wait:
            print(
                json.dumps(
                    {
                        "subagent": subagent_dir.name,
                        "status": "launched",
                        "response_file": str(response_file_final),
                        "temp_file": str(response_file_tmp),
                    }
                ),
                file=sys.stdout,
            )
            print(
                f"\nAgent launched. Response will be written to:\n  {response_file_final}\n"
                f"Monitor: check if {response_file_tmp} has been renamed to {response_file_final.name}",
                file=sys.stderr,
            )
            return 0

        # Sync mode (--wait): wait for response and print it
        response_received = wait_for_response_output(response_file_tmp, response_file_final)
        
        # Remove the lock file after sync completion
        if not dry_run:
            try:
                remove_subagent_lock(subagent_dir)
            except Exception as e:
                print(f"warning: Failed to remove subagent lock: {e}", file=sys.stderr)
        
        if not response_received:
            return 1

        return 0
    
    except Exception as e:
        print(
            json.dumps({"success": False, "error": str(e)}),
            file=sys.stdout,
        )
        return 1


def warmup_subagents(
    *,
    subagent_root: Optional[Path] = None,
    subagents: int = 1,
    dry_run: bool = False,
) -> int:
    """Open all provisioned VSCode workspaces to warm them up.
    
    Args:
        subagent_root: Root directory containing subagents. Defaults to standard location.
        subagents: Number of subagent workspaces to open. Defaults to 1.
        dry_run: When True, report what would be done without opening workspaces.
    
    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    if subagent_root is None:
        subagent_root = get_subagent_root()
    
    workspaces = get_all_subagent_workspaces(subagent_root)
    
    if not workspaces:
        print(
            f"info: No provisioned subagents found in {subagent_root}",
            file=sys.stderr,
        )
        print(
            "hint: Provision subagents first with:\n"
            "  lmspace code provision --subagents <count>",
            file=sys.stderr,
        )
        return 1
    
    # Limit to the requested number of subagents
    workspaces_to_open = workspaces[:subagents]
    
    print(f"Found {len(workspaces)} subagent workspace(s), opening {len(workspaces_to_open)}", file=sys.stderr)
    
    if dry_run:
        print("Workspaces that would be opened:", file=sys.stderr)
        for workspace in workspaces_to_open:
            print(f"  {workspace}", file=sys.stderr)
        return 0
    
    print("Opening workspaces...", file=sys.stderr)
    for i, workspace in enumerate(workspaces_to_open, 1):
        try:
            print(f"  [{i}/{len(workspaces_to_open)}] {workspace.parent.name}", file=sys.stderr)
            subprocess.Popen(f'code "{workspace}"', shell=True)
        except Exception as e:
            print(f"warning: Failed to open {workspace}: {e}", file=sys.stderr)
    
    print("✓ All workspaces opened", file=sys.stderr)
    return 0


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
        "--dry-run",
        action="store_true",
        help="Print what would be done without making changes",
    )
    parser.add_argument(
        "-w", "--wait",
        action="store_true",
        help="Wait for response and print to stdout (sync mode). Default is async mode.",
    )
    args = parser.parse_args()
    return launch_agent(
        args.query,
        args.agent_config_path,
        extra_attachments=args.attachment,
        dry_run=args.dry_run,
        wait=args.wait,
    )


if __name__ == "__main__":
    sys.exit(main())
