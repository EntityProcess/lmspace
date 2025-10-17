# LMSpace MVP

The LMSpace MVP provisions Azure OpenAI assistants from YAML config files. Each config describes a custom GPT-style agent with instructions and knowledge-base sources. The runner downloads the referenced files, uploads them to Azure OpenAI using the Assistants API (file search), and optionally registers a Microsoft Agent Framework agent when the framework is available.

The project uses `uv` for dependency and environment management.

## Repository Layout

- `src/lmspace/` - Package sources
- `tests/` - Unit tests
- `configs/` - Example YAML configs
- `docs/` - Design and planning documents

## Prerequisites

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) installed locally (`pip install uv`)
- Azure OpenAI resource with Assistants API v2 enabled
- Optional: Microsoft Agent Framework preview packages

Before provisioning real assistants, set the following environment variables:

- `AZURE_OPENAI_ENDPOINT`
- `AZURE_OPENAI_API_VERSION`
- `AZURE_OPENAI_DEPLOYMENT_NAME`
- `AZURE_OPENAI_API_KEY` *(or rely on Azure AD with `DefaultAzureCredential`)*

Optional environment variables:

- `GITHUB_TOKEN` for private GitHub file downloads
- `LMSPACE_VECTOR_PREFIX` to customize vector store names
- `LMSPACE_LOG_LEVEL` for logging (default `info`)

## Getting Started

```powershell
# Create the environment using uv
uv venv

# Install the package in editable mode with development tools
uv pip install -e . --extra dev

# Provision assistants from a config file or directory (dry-run shown)
lmspace --dry-run configs/sample-agent.yaml
```

Run without `--dry-run` after configuring Azure credentials to perform real provisioning.

## YAML Config Format

```yaml
name: SampleAgent
instructions: |
  You are a helpful assistant that answers questions about the example files.
urls:
  - https://raw.githubusercontent.com/github/gitignore/main/Python.gitignore
```

Each `urls` entry should point to a text or binary document Azure OpenAI accepts for file search. The runner downloads the files, uploads them to Azure, creates a vector store, and wires it into a new assistant using your deployment.

## Development

```powershell
# Install deps (from repo root)
uv pip install -e . --extra dev

# Run tests
uv run --extra dev pytest
```

The code lives under `src/lmspace`. Key modules:

- `config.py` - Validates YAML configs
- `fetcher.py` - Downloads remote knowledge sources
- `azure.py` - Wraps Azure OpenAI assistant provisioning
- `runner.py` - Glues everything together
- `cli.py` - Command-line entry point

## Microsoft Agent Framework Integration

If the `agent_framework` preview package is installed, the runner attempts to create a matching Agent Framework agent via `AzureOpenAIResponsesClient`. When the package is absent, the MVP logs the omission and still provisions the Azure OpenAI assistant.

## Testing Notes

Unit tests cover YAML parsing, remote fetch behaviour, and runner orchestration. Azure calls are mocked by injecting stub services, so tests run without Azure credentials.

## Next Steps

1. Add richer error handling and telemetry around Azure operations.
2. Persist vector store and assistant identifiers for incremental updates.
3. Extend the runner to handle incremental syncs and deletions.
4. Package and publish to PyPI once the Agent Framework dependencies stabilise.
