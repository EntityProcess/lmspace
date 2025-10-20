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

2. **Start a chat with an agent**:
   ```powershell
   lmspace code chat <agent_config_path> "Your query here"
   ```
   This claims an unlocked subagent, copies your agent configuration, and opens VS Code.

3. **Example agent configuration** (`my-agent/` directory):
   - `SUBAGENT.md` - Authoritative chat mode definition; runtime launches transpile to `subagent.chatmode.md`
   - `subagent.code-workspace` - VS Code workspace settings

### Command Reference

**Provision subagents**:
```powershell
lmspace code provision --subagents <count> [--refresh] [--template <path>] [--target-root <path>] [--warmup]
```
- `--subagents <count>`: Number of workspaces to create
- `--refresh`: Rebuild unlocked workspaces
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
lmspace code chat <agent_config_path> <query> [--attachment <path>] [--dry-run]
```
- `<agent_config_path>`: Path to agent configuration directory
- `<query>`: User query to pass to the agent
- `--attachment <path>`: Additional files to attach (repeatable)
- `--dry-run`: Preview without launching VS Code

## Development

```powershell
# Install deps (from repo root)
uv pip install -e . --extra dev

# Run tests
uv run --extra dev pytest
```

