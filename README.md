# LMSpace

LMSpace is a CLI tool for managing workspace agents across different backends. It currently supports VS Code workspace agents with plans to add support for OpenAI Agents and Azure AI Agents.

## Features

### VS Code Workspace Agents ✅

Manage isolated VS Code workspaces for parallel agent development sessions:

- **Provision subagents**: Create a pool of isolated workspace directories
- **Chat with agents**: Automatically claim a workspace and start a VS Code chat session
- **Lock management**: Prevent conflicts when running multiple agents in parallel

The project uses `uv` for dependency and environment management.

## Repository Layout

- `src/lmspace/` - Package sources
- `tests/` - Unit tests
- `configs/` - Example YAML configs
- `docs/` - Design and planning documents

## Prerequisites

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) installed locally (`pip install uv`)
- VS Code installed for workspace agent functionality

## Quick Start

### Installation

```powershell
# Install lmspace
uv pip install lmspace

# Or for development
uv pip install -e .[dev]
```

### Using VS Code Workspace Agents

1. **Provision subagent workspaces**:
   ```powershell
   lmspace code provision --subagents 5
   ```
   This creates 5 isolated workspace directories in `~/.ai-prompts/agents/`.

2. **Start a chat with an agent**:
   ```powershell
   lmspace code chat <agent_config_path> "Your query here"
   ```
   This claims an unlocked subagent, copies your agent configuration, and opens VS Code.

3. **Example agent configuration** (`my-agent/` directory):
   - `subagent.chatmode.md` - Chat mode configuration and instructions
   - `subagent.code-workspace` - VS Code workspace settings

### Command Reference

**Provision subagents**:
```powershell
lmspace code provision --subagents <count> [--refresh] [--template <path>] [--target-root <path>]
```
- `--subagents <count>`: Number of workspaces to create
- `--refresh`: Rebuild unlocked workspaces
- `--template <path>`: Custom template directory
- `--target-root <path>`: Custom destination (default: `~/.ai-prompts/agents`)
- `--dry-run`: Preview without making changes

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
