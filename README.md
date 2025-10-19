# LMSpace

The LMSpace provisions OpenAI assistants and VS Code agents from config files. Each config describes a custom GPT-style agent with instructions and knowledge-base sources.

For OpenAI assistants: The runner downloads the referenced files, uploads them to Azure OpenAI using the Assistants API (file search).
For VS Code agents: The runner creates a workspace with the required context and launches a VS Code instance.

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
```

## Development

```powershell
# Install deps (from repo root)
uv pip install -e . --extra dev

# Run tests
uv run --extra dev pytest
```
