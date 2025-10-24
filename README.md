# LMSpace

LMSpace is a CLI tool for managing workspace agents across different backends. It currently supports VS Code workspace agents with plans to add support for OpenAI Agents, Azure AI Agents, GitHub Copilot CLI and Codex CLI.

## Features

### VS Code Workspace Agents

Manage isolated VS Code workspaces for parallel agent development sessions:

- **Provision subagents**: Create a pool of isolated workspace directories
- **Chat with agents**: Automatically claim a workspace and start a VS Code chat session
- **Lock management**: Prevent conflicts when running multiple agents in parallel

The project uses `uv` for dependency and environment management.

## Prerequisites

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) installed locally (`pip install uv`)
- VS Code installed for workspace agent functionality

## Quick Start

### Installation

```powershell
# Install lmspace as a uv-managed tool (recommended for end users)
uv tool install lmspace

# Install via uv pip (useful when managing a virtualenv manually)
uv pip install lmspace

# Or for development
uv pip install -e .[dev]
```

### Using VS Code Workspace Agents

1. **Provision and optionally warm up subagent workspaces**:
   ```powershell
   lmspace code provision --subagents 5 [--warmup]
   ```
   This creates 5 isolated workspace directories in `~/.lmspace/vscode-agents/`. Add `--warmup` to open the newly provisioned workspaces immediately.

2. **Start a chat with an agent (async mode - default)**:
   ```powershell
   lmspace code chat <prompt_file> "Your query here"
   ```
   This claims an unlocked subagent, copies your prompt file and any attachments, opens VS Code with a wakeup chatmode, and returns immediately.
   The agent writes its response to a file that you can monitor or read later.

3. **Start a chat with an agent (sync mode - wait for response)**:
   ```powershell
   lmspace code chat <prompt_file> "Your query here" --wait
   ```
   This blocks until the agent completes and prints the response to stdout.

### Command Reference

**Provision subagents**:
```powershell
lmspace code provision --subagents <count> [--force] [--template <path>] [--target-root <path>] [--warmup]
```
- `--subagents <count>`: Number of workspaces to create
- `--force`: Unlock and overwrite all subagent directories regardless of lock status
- `--template <path>`: Custom template directory
- `--target-root <path>`: Custom destination (default: `~/.lmspace/vscode-agents`)
- `--dry-run`: Preview without making changes
- `--warmup`: Launch VS Code for the provisioned workspaces once provisioning finishes

**Warm up workspaces**:
```powershell
lmspace code warmup [--subagents <count>] [--target-root <path>] [--dry-run]
```
- `--subagents <count>`: Number of workspaces to open (default: 1)
- `--target-root <path>`: Custom subagent root directory
- `--dry-run`: Show which workspaces would be opened

**Start a chat with an agent**:
```powershell
lmspace code chat <prompt_file> <query> [--attachment <path>] [--wait] [--dry-run]
```
- `<prompt_file>`: Path to a prompt file to copy and attach (e.g., `vscode-expert.prompt.md`)
- `<query>`: User query to pass to the agent
- `--attachment <path>` / `-a`: Additional files to attach (repeatable)
- `--wait` / `-w`: Wait for response and print to stdout (sync mode). Default is async mode.
- `--dry-run`: Preview without launching VS Code

**Note**: By default, chat runs in **async mode** - it returns immediately after launching VS Code, and the agent writes its response to a timestamped file in the subagent's `messages/` directory. Use `--wait` for synchronous operation.

**List provisioned subagents**:
```powershell
lmspace code list [--target-root <path>] [--json]
```
- `--target-root <path>`: Custom subagent root directory
- `--json`: Output results as JSON

**Unlock subagents**:
```powershell
lmspace code unlock [--subagent <name>] [--all] [--target-root <path>] [--dry-run]
```
- `--subagent <name>`: Specific subagent to unlock (e.g., `subagent-1`)
- `--all`: Unlock all subagents
- `--target-root <path>`: Custom subagent root directory
- `--dry-run`: Show what would be unlocked without making changes

## Development

```powershell
# Install deps (from repo root)
uv pip install -e . --extra dev

# Run tests
uv run --extra dev pytest
```

