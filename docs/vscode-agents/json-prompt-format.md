# JSON Prompt Format for VS Code Agents

## Overview

When launching an agent via `lmspace code launch`, the launcher automatically wraps the user's query in a JSON structure that includes instructions for saving responses.

## JSON Structure

```json
{
  "user_query": "<the original user query>",
  "instructions": {
    "save_responses": true,
    "response_file_path": "<full path to response file>",
    "format": "markdown",
    "note": "Save all your responses to the specified file path as you work through the task."
  }
}
```

## Response File Naming

Response files are automatically named using the timestamp when the agent is launched:

- Format: `YYYYMMDDHHMMSS_res.md`
- Example: `20251019143022_res.md` (October 19, 2025 at 14:30:22)
- Location: `<subagent-dir>/messages/`

## Example Usage

### Command Line

```pwsh
lmspace code launch agents/glow-ctf "Help me debug the configuration parser"
```

### Generated JSON Prompt

```json
{
  "user_query": "Help me debug the configuration parser",
  "instructions": {
    "save_responses": true,
    "response_file_path": "C:\\Users\\...\\subagent-1\\messages\\20251019143022_res.md",
    "format": "markdown",
    "note": "Save all your responses to the specified file path as you work through the task."
  }
}
```

### Launch Output

```json
{
  "success": true,
  "subagent_name": "subagent-1",
  "response_file": "C:\\Users\\...\\subagent-1\\messages\\20251019143022_res.md"
}
```

## Benefits

1. **Automatic Response Tracking**: All agent responses are saved to a timestamped file for later review
2. **Conversation History**: The `messages` folder provides a chronological record of all agent sessions
3. **Easy Debugging**: Review saved responses to understand agent behavior and decisions
4. **Reproducibility**: Keep a record of what the agent produced for each query

## Directory Structure

After launching an agent, the subagent directory will contain:

```
subagent-1/
├── messages/
│   ├── 20251019143022_req.json  # The JSON instructions sent to the agent
│   ├── 20251019143022_res.md    # The agent's response
│   ├── 20251019150033_req.json
│   ├── 20251019150033_res.md
│   └── ...
├── subagent.chatmode.md
├── subagent.code-workspace
└── subagent.lock
```

Both the prompt and response files are saved with matching timestamps, making it easy to pair them together.

## Implementation Details

- The `messages` folder is created automatically when agent configuration is copied to the subagent
- Response file path is included in the JSON output for wrapper prompts to reference
- The JSON prompt is written to a file (e.g., `20251019145543_req.json`) in the messages directory and attached to the chat
- This approach avoids shell escaping issues and preserves the prompt for reference
- The agent receives a simple text prompt asking it to read the attached JSON file for task details
- Works on Windows, macOS, and Linux using `shell=True` to find the `code` command in PATH
