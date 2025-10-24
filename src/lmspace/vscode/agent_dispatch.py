"""Dispatch an agent to an isolated subagent environment."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, Sequence

DEFAULT_LOCK_NAME = "subagent.lock"


def get_subagent_root() -> Path:
    """Get the root directory for subagents."""
    return Path.home() / ".lmspace" / "vscode-agents"


def get_all_subagent_workspaces(subagent_root: Path) -> list[Path]:
    """Get all subagent workspace files.
    
    Returns a list of paths to all workspace files (e.g., subagent-1.code-workspace)
    in the subagent root directory, sorted by subagent number.
    """
    if not subagent_root.exists():
        return []
    
    subagents = sorted(
        (d for d in subagent_root.iterdir() if d.is_dir() and d.name.startswith("subagent-")),
        key=lambda d: int(d.name.split("-")[1])
    )
    
    workspaces = []
    for subagent_dir in subagents:
        workspace_file = subagent_dir / f"{subagent_dir.name}.code-workspace"
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


def check_workspace_opened(workspace_name: str) -> bool:
    """Check if a workspace is currently opened in VS Code.
    
    Args:
        workspace_name: Name to search for in workspace list (e.g., 'subagent-1')
    
    Returns:
        True if the workspace is currently open, False otherwise
    """
    try:
        result = subprocess.run(
            'code --status',
            shell=True,
            capture_output=True,
            text=True,
            timeout=10
        )
        # Look for the workspace name in the output
        # Format in output: "window [...] (workspace_name (Workspace) - Visual Studio Code)"
        return workspace_name in result.stdout
    except Exception:
        # If we can't determine, assume it's not open (safer to open)
        return False


def ensure_workspace_focused(workspace_path: Path, workspace_name: str, subagent_dir: Path, poll_interval: float = 1.0, timeout: float = 60.0) -> bool:
    """Ensure VS Code workspace is open and focused.
    
    Opens the workspace only if it's not already open, then waits for .alive file to signal readiness.
    
    Args:
        workspace_path: Path to the .code-workspace file
        workspace_name: Name of the workspace (e.g., 'subagent-1') for checking if open
        subagent_dir: Path to the subagent directory
        poll_interval: Time between checks for .alive file (default: 1.0 seconds)
        timeout: Maximum time to wait for .alive file (default: 60.0 seconds)
    
    Returns:
        True if workspace is ready, False if timeout occurred
    """
    workspace_already_open = check_workspace_opened(workspace_name)
    
    if workspace_already_open:
        # Workspace is already open, just focus it and return
        subprocess.Popen(f'code "{workspace_path}"', shell=True)
        return True
    
    # Workspace not open, need to open and wait for readiness
    # Delete any existing .alive file first
    alive_file = subagent_dir / ".alive"
    if alive_file.exists():
        alive_file.unlink()
    
    subprocess.Popen(f'code "{workspace_path}"', shell=True)
    time.sleep(0.1)  # Brief wait for VS Code to start
    
    # Use a unique chat_id for this readiness check
    readiness_chat_id = str(uuid.uuid4())[:8]
    chat_cmd = f'code -r chat -m {readiness_chat_id} "create a file named .alive"'
    subprocess.Popen(chat_cmd, shell=True)
    
    # Wait for .alive file to appear
    elapsed = 0.0
    while not alive_file.exists() and elapsed < timeout:
        time.sleep(poll_interval)
        elapsed += poll_interval
    
    if not alive_file.exists():
        print(f"warning: Workspace readiness timeout after {timeout}s", file=sys.stderr)
        return False
    
    return True


def copy_agent_config(
    subagent_dir: Path,
) -> dict:
    """Copy default workspace file into the subagent directory."""
    default_template_dir = get_default_template_dir()
    workspace_src = default_template_dir / "subagent.code-workspace"
    if not workspace_src.exists():
        raise FileNotFoundError(f"Default workspace template not found: {workspace_src}")

    workspace_dst = subagent_dir / f"{subagent_dir.name}.code-workspace"
    shutil.copy2(workspace_src, workspace_dst)

    messages_dir = subagent_dir / "messages"
    messages_dir.mkdir(exist_ok=True)

    return {
        "workspace": str(workspace_dst.resolve()),
        "messages_dir": str(messages_dir.resolve()),
    }


def create_subagent_lock(subagent_dir: Path) -> Path:
    """Create a lock file to mark the subagent as in-use.
    
    Also clears any existing messages and chatmodes from previous runs.
    
    Returns the path to the created lock file.
    """
    # Clear existing messages
    messages_dir = subagent_dir / "messages"
    if messages_dir.exists():
        for msg_file in messages_dir.iterdir():
            if msg_file.is_file():
                msg_file.unlink()
    
    # Clear existing chatmode files
    for chatmode_file in subagent_dir.glob("*.chatmode.md"):
        chatmode_file.unlink()
    
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


def _prepare_subagent_directory(
    subagent_dir: Path,
    prompt_file: Path,
    chat_id: str,
    dry_run: bool,
) -> int:
    """Prepare the subagent directory with config, lock, and chatmode.
    
    Returns 0 on success, 1 on failure.
    """
    if dry_run:
        return 0
    
    try:
        copy_agent_config(subagent_dir)
    except FileNotFoundError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    
    try:
        create_subagent_lock(subagent_dir)
    except OSError as e:
        print(f"error: Failed to create subagent lock: {e}", file=sys.stderr)
        return 1
    
    chatmode_file = subagent_dir / f"{chat_id}.chatmode.md"
    try:
        shutil.copy2(prompt_file, chatmode_file)
    except OSError as e:
        print(f"error: Failed to copy prompt file to chatmode: {e}", file=sys.stderr)
        return 1
    
    return 0


def _resolve_attachments(extra_attachments: Optional[Sequence[Path]]) -> list[str]:
    """Resolve and validate attachment paths.
    
    Returns list of resolved attachment path strings.
    Raises FileNotFoundError if any attachment doesn't exist.
    """
    resolved_extra: list[str] = []
    if extra_attachments:
        for attachment in extra_attachments:
            resolved_attachment = attachment.expanduser().resolve()
            if not resolved_attachment.exists():
                raise FileNotFoundError(
                    f"Attachment not found: {resolved_attachment}"
                )
            resolved_extra.append(str(resolved_attachment))
    return resolved_extra


def _create_request_prompt(
    user_query: str,
    response_file_tmp: Path,
    response_file_final: Path,
    lock_file: Path,
) -> str:
    """Create the SudoLang prompt with task and system instructions."""
    return f"""[[ ## task ## ]]
{user_query}

[[ ## system_instructions ## ]]

**IMPORTANT**: Follow these exact steps:
1. Create and write your complete response to: {response_file_tmp}
2. When completely finished, run these PowerShell commands to signal completion:
   Move-Item -LiteralPath '{response_file_tmp}' -Destination '{response_file_final}'
   Remove-Item -LiteralPath '{lock_file}' -Force

Do not proceed to step 2 until your response is completely written to the temporary file.
"""


def _launch_vscode_with_chat(
    subagent_dir: Path,
    chat_id: str,
    attachment_paths: list[str],
    sudolang_prompt: str,
    timestamp: str,
) -> bool:
    """Launch VS Code with the workspace and chat.
    
    Returns True on success, False on failure.
    """
    try:
        workspace_path = (subagent_dir / f"{subagent_dir.name}.code-workspace").resolve()
        messages_dir = subagent_dir / "messages"

        # Write SudoLang prompt to a req.md file in the messages directory
        req_file = messages_dir / f"{timestamp}_req.md"
        req_file.write_text(sudolang_prompt, encoding='utf-8')
        
        # Build chat command with the unique chat mode
        chat_cmd = f'code -r chat -m {chat_id}'
        
        # Add attachments
        for attachment in attachment_paths:
            chat_cmd += f' -a "{attachment}"'
        
        # Add the req.md file as an attachment
        chat_cmd += f' -a "{req_file}"'
        
        # Add a simple prompt that references the req.md file
        chat_cmd += f' "Follow instructions in {req_file.name}"'

        # Ensure workspace is open and focused (with .alive file check)
        workspace_ready = ensure_workspace_focused(workspace_path, subagent_dir.name, subagent_dir)
        if not workspace_ready:
            print("warning: Workspace may not be fully ready", file=sys.stderr)
        
        # Open the chat in VS Code
        subprocess.Popen(chat_cmd, shell=True)
        return True
            
    except Exception as e:
        print(f"warning: Failed to launch VS Code: {e}", file=sys.stderr)
        return False


def dispatch_agent(
    user_query: str,
    prompt_file: Path,
    *,
    extra_attachments: Optional[Sequence[Path]] = None,
    dry_run: bool = False,
    wait: bool = False,
) -> int:
    """Dispatch an agent to an isolated subagent.
    
    Args:
        user_query: The user's input query for the agent.
        prompt_file: Path to a prompt file to copy to subagent and attach (e.g., vscode-expert.prompt.md).
        extra_attachments: Additional attachment paths that should be forwarded
            to the dispatched chat.
        dry_run: When True, report planned actions without launching VS Code.
        wait: When True, wait for response and print to stdout (sync mode).
              When False (default), return immediately after dispatch (async mode).
    
    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    try:
        # Validate prompt file
        prompt_file = prompt_file.expanduser().resolve()
        if not prompt_file.exists():
            raise FileNotFoundError(f"Prompt file not found: {prompt_file}")
        if not prompt_file.is_file():
            raise ValueError(f"Prompt file must be a file, not a directory: {prompt_file}")

        # Find unlocked subagent
        subagent_root = get_subagent_root()
        subagent_dir = find_unlocked_subagent(subagent_root)
        if subagent_dir is None:
            print(
                "error: No unlocked subagents available. Provision additional subagents with:\n"
                "  lmspace code provision --subagents <desired_total>",
                file=sys.stderr,
            )
            return 1
        
        # Report which subagent will be used (before acquiring lock)
        print(
            f"info: Acquiring subagent: {subagent_dir.name}",
            file=sys.stderr,
        )
        
        # Generate unique ID and prepare directory
        chat_id = str(uuid.uuid4())[:8]
        result = _prepare_subagent_directory(subagent_dir, prompt_file, chat_id, dry_run)
        if result != 0:
            return result
        
        # Resolve attachments
        attachment_paths = _resolve_attachments(extra_attachments)
        
        # Prepare response files and prompt
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        messages_dir = subagent_dir / "messages"
        response_file_tmp = messages_dir / f"{timestamp}_res.tmp.md"
        response_file_final = messages_dir / f"{timestamp}_res.md"
        lock_file = subagent_dir / DEFAULT_LOCK_NAME
        
        sudolang_prompt = _create_request_prompt(
            user_query, response_file_tmp, response_file_final, lock_file
        )
        
        # Report the dispatched subagent
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
        
        # Launch VS Code
        if dry_run:
            return 0

        launch_success = _launch_vscode_with_chat(
            subagent_dir, chat_id, attachment_paths, sudolang_prompt, timestamp
        )
        
        if not launch_success:
            return 1

        # Async mode: return immediately
        if not wait:
            print(
                json.dumps(
                    {
                        "subagent": subagent_dir.name,
                        "status": "dispatched",
                        "response_file": str(response_file_final),
                        "temp_file": str(response_file_tmp),
                    }
                ),
                file=sys.stdout,
            )
            print(
                f"\nAgent dispatched. Response will be written to:\n  {response_file_final}\n"
                f"Monitor: check if {response_file_tmp} has been renamed to {response_file_final.name}",
                file=sys.stderr,
            )
            return 0

        # Sync mode: wait for response
        response_received = wait_for_response_output(response_file_final)
        
        if not dry_run:
            try:
                remove_subagent_lock(subagent_dir)
            except Exception as e:
                print(f"warning: Failed to remove subagent lock: {e}", file=sys.stderr)
        
        return 0 if response_received else 1
    
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
    """Entry point for the dispatch script."""
    parser = argparse.ArgumentParser(
        description="Dispatch an agent to an isolated subagent environment."
    )
    parser.add_argument(
        "prompt_file",
        type=Path,
        help="Path to a prompt file to copy and attach (e.g., vscode-expert.prompt.md)",
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
    return dispatch_agent(
        args.query,
        args.prompt_file,
        extra_attachments=args.attachment,
        dry_run=args.dry_run,
        wait=args.wait,
    )


if __name__ == "__main__":
    sys.exit(main())
