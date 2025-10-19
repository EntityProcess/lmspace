# VS Code Workspace Agents Technical Design

**Status**: Split between delivered behaviour and roadmap aspirations. This
document records what works today and highlights the features we still plan to
add before calling the VS Code workspace agent system stable.

## Overview

The `lmspace code` subcommand provides a standalone CLI tool for managing VS Code
workspace agents. This tool can be used across any prompts repository, enabling
isolated agent workspaces for parallel development sessions. The architecture is
designed to support future agent backends (e.g., `lmspace openai` for OpenAI Agents).

## Installation & Setup

Install `lmspace` as a standalone package:
```pwsh
uv pip install lmspace
# or for development
uv pip install -e .[dev]
```

The tool is now available globally via the `lmspace` command.

## Delivered Capabilities (Current Implementation)

### Provisioning Workflow ✅ Delivered

- Run `lmspace code provision --subagents <count>` to seed the subagent pool.
  The command copies the built-in `subagent_template` into
  `%USERPROFILE%\.ai-prompts\agents` by default (override with
  `--target-root <path>` if needed).
- Subagent directories follow the `subagent-<n>` naming pattern. Provisioning
  skips any directory that already exists with a `subagent.lock` file, which
  marks an in-flight conversation. Pass `--refresh` to rebuild unlocked entries
  after template changes.
- Subagents are disposable; delete or refresh them whenever the template,
  prompt attachments, or dependencies change.
- Custom templates can be specified with `--template <path>` to override the
  default built-in template.

### Runtime Lifecycle ✅ Delivered

- `lmspace code launch` creates `subagent.lock` when it claims a workspace. The
  lock is not released automatically; wrapper flows or clean-up scripts must
  remove it once the chat session finishes.
- Multiple VS Code instances can operate in parallel as long as they target
  different subagent directories. Keep transient files (logs, scratch data)
  inside the subagent folder to avoid polluting the template.

### Wrapper Entry Points ✅ Delivered

- Launch agents via the CLI:
  ```pwsh
  lmspace code launch <agent_config_path> "{user_query}"
  ```
- Example usage from any prompts repository:
  ```pwsh
  lmspace code launch agents/glow-ctf "Help me debug this issue"
  ```
- Launch parameters:
  - `agent_config_path` must point to an agent configuration directory in your
    prompts repository. The path can be absolute or relative to your current
    working directory.
  - The launcher copies `subagent.chatmode.md` and `subagent.code-workspace`
    from the agent config into the claimed subagent directory before starting
    VS Code, but it does not attach them to the chat session automatically.
  - Additional attachments can be passed with `--attachment <path>` (repeatable).
- The launcher emits a compact JSON payload that includes:
  - `success`: Boolean indicating launch success
  - `subagent_name`: Name of the claimed subagent directory (e.g., "subagent-1")
  - `response_file`: Path where the agent will save its responses
  
  Example success response:
  ```json
  {
    "success": true,
    "subagent_name": "subagent-1",
    "response_file": "C:\\Users\\...\\subagent-1\\messages\\20251019143022_res.md"
  }
  ```
  
  Wrapper prompts should read the JSON, report the assigned workspace and
  response file location, and stop there—the script opens VS Code on its own.

### Prompt Context

- Gather a free-form query string before launch so the chat title reflects the
  user's intent. The `launch-agent.py` CLI accepts the query as a positional
  argument and relays it as a JSON-formatted prompt to `code chat`.
- The launcher automatically generates a JSON prompt structure that includes:
  - The user's original query
  - Instructions to save all responses to a timestamped file in the subagent's
    `messages` folder (format: `YYYYMMDDHHMMSS_res.md`)
  - Response format specifications (markdown)
- Example JSON prompt structure:
  ```json
  {
    "user_query": "Help me debug this issue",
    "instructions": {
      "save_responses": true,
      "response_file_path": "/path/to/subagent/messages/20251019143022_res.md",
      "format": "markdown",
      "note": "Save all your responses to the specified file path as you work through the task."
    }
  }
  ```
- The `messages` folder is automatically created when the agent configuration
  is copied to the subagent directory, providing a dedicated location for
  conversation history and agent responses.
- Combine the wrapper prompt's description with any important notes from the
  associated `subagent.chatmode.md` when reporting launch status back to users.

### Cross-Repository Usage

- `lmspace` is a standalone tool that can be installed once and used across
  multiple prompts repositories. Agent configurations live in your prompts
  repository, while the `lmspace` tool and subagent infrastructure are managed
  separately.
- The tool operates on agent configuration directories that contain at minimum:
  - `subagent.chatmode.md`: Instructions and context for the chat session
  - `subagent.code-workspace`: VS Code workspace configuration
- Agent configurations are independent of the `lmspace` installation, allowing
  each prompts repository to define its own agent templates and workflows.

### Validation and Extensibility

- Provisioning validates the template path and (optionally) rebuilds unlocked
  directories. It excludes `__pycache__` and compiled Python artifacts to keep
  clones clean.
- The launcher validates that the agent template directory, prompt path, and
  attachments exist before proceeding. Any failure surfaces as `success: false`
  with a descriptive error string.
- The modular architecture allows future expansion with additional subcommands
  (e.g., `lmspace openai` for OpenAI Agents, `lmspace azure` for Azure AI
  Agents) without affecting the existing VS Code workspace agent functionality.

## Roadmap (Not Yet Implemented)

### Short-term (VS Code Agents)
- Promote wrapper entry points to SudoLang programs that enforce
  `subagent.chatmode.md` validation and orchestrate attachments automatically.
- Expand the launcher JSON response with resolved workspace paths,
  chatmode locations, and the final attachment list so wrappers can confirm the
  launch details without shell parsing.
- Automatically attach `subagent.chatmode.md`, the subagent directory, and
  agent-level documentation when calling `code chat`, reducing manual
  duplication across wrappers.
- Provide helper tooling to release locks when a chat session ends, or bake the
  unlock flow into the launcher (e.g., `lmspace code unlock <subagent-name>`).
- Document and automate metadata hand-off between wrapper prompts and the
  subagent chat (e.g. launch summaries, reference links).

### Long-term (Multi-Backend Support)
- Add `lmspace openai` subcommand for OpenAI Agents SDK integration, enabling
  agent provisioning and execution against OpenAI's hosted agent runtime.
- Add `lmspace azure` subcommand for Azure AI Agents support, with similar
  provisioning and lifecycle management capabilities.
- Explore unified configuration format that allows agent definitions to specify
  their preferred backend (VS Code, OpenAI, Azure) while sharing common
  metadata and prompt templates.
- Consider agent migration tooling to convert between backends (e.g., moving a
  VS Code workspace agent configuration to run as an OpenAI agent).

Revisit the roadmap after each substantial iteration to capture newly delivered
behaviour and retire items that are no longer needed.