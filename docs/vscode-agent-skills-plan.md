## Implementation Plan: Composable Skills for Subagent Chat Modes

### Objective
Make `SUBAGENT.md` the authoritative definition for VS Code subagents and generate `subagent.chatmode.md` on demand by composing reusable `.skill.md` snippets.

### Desired End State
- `lmspace vscode chat` always transpiles before launching a subagent; nothing checks in the generated chatmode file.
- Skills referenced in `SUBAGENT.md` resolve from agent-local `contexts/` directories or a configured workspace-level `contexts/` directory.
- CLI users can materialise the chatmode file manually for inspection or debugging.

### Architecture Outline
- **Transpiler (`src/lmspace/vscode/transpiler.py`)**: parse frontmatter, rebuild the chatmode body, append the resolved skill bodies, and write to disk. Error messaging must highlight missing `SUBAGENT.md` files or unresolved skills.
- **CLI (`lmspace vscode transpile`)**: thin wrapper that validates inputs, calls the transpiler, and reports the output path.
- **Launch integration (`copy_agent_config`)**: call the transpiler, copy the generated chatmode into the runtime directory (alongside any optional workspace template), and ensure the messages folder exists. The previous fallback logic for pre-committed chatmodes is removed.

### Skill Resolution
- Search order: `{agent}/contexts/{skill}.skill.md`, then `{workspace_root}/contexts/{skill}.skill.md` when a workspace root is explicitly provided by the caller.
- Skill files contribute only their body; their frontmatter is intentionally stripped.
- Missing skills surface a `FileNotFoundError` that lists all attempted locations.

### Implementation Phases
1. **Core Transpiler**: scaffold module, implement frontmatter parsing/composition, and cover the happy path plus malformed frontmatter cases.
2. **CLI Command**: register the `transpile` subcommand, reuse the transpiler entry point, and document the flag in CLI help.
3. **Launch Hook**: wire the transpiler into `copy_agent_config`, clean up legacy chatmode handling, and confirm end-to-end chat launch.
4. **Skill Resolution Enhancements**: add configurable workspace root support and multi-location skill lookup, with error messaging and regression tests.

### Testing & Acceptance
- Pytest coverage for frontmatter parsing, skill resolution paths, transpiler assembly, launch integration, and CLI invocation.
- Acceptance checks: on-demand CLI generation, automatic transpilation during `lmspace vscode chat`, and graceful failure when required files are absent.
- No new third-party dependencies; existing `pyyaml` is sufficient.

### Migration Notes
- Delete any committed `subagent.chatmode.md` files; generated copies live only in subagent runtime directories.
- Move reusable behaviours into `contexts/*.skill.md` and list them under the `skills` frontmatter key of `SUBAGENT.md`.
- Configure local environments via the existing `.env` template; no further configuration changes required.
