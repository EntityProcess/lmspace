# Repository Guidelines

## Project Structure & Module Organization
- `src/lmspace/`: CLI, agent provisioning logic, config/fetch utilities.
- `tests/`: Pytest suites covering config parsing, fetchers, and the runner.
- `configs/`: Sample YAML agents (duplicated URLs allowed for experiments).
- `.python-version`, `pyproject.toml`, and `env.template`: runtime pinning, packaging metadata, and environment variables.

## Build, Test, and Development Commands
- `uv venv`: Create the local virtual environment pinned to Python 3.12.
- `uv pip install -e .[dev]`: Editable install with dev extras (pytest, respx).
- `uv run --extra dev pytest`: Run the full test suite using the dev extra dependencies.

## Coding Style & Naming Conventions
- Follow PEP 8 with 4-space indentation; prefer explicit imports and type hints on public functions.
- Keep modules cohesive (`config.py` for validation, `fetcher.py` for I/O, etc.).
- When adding scripts or commands, expose them via `pyproject.toml` entry points.

## Testing Guidelines
- Use `pytest` with `respx` for HTTP mocking and simple stub classes for Azure interactions.
- Name files `test_*.py`; structure new tests alongside the modules they cover.
- Ensure tests pass via `uv run --extra dev pytest` before opening a PR.

## Commit & Pull Request Guidelines
- Write commits in the imperative mood (e.g., `Add Azure retry helper`).
- Reference related issues in commit bodies or PR descriptions when applicable.
- PRs should summarize behaviour changes, note testing performed, and include screenshots/log excerpts only when they clarify the impact.

## Configuration & Secrets
- Copy `env.template` to `.env` or export variables manually (never commit secrets).
- Use Azure Key Vault or environment variables for production credentials; API keys must not appear in config files or Git history.
