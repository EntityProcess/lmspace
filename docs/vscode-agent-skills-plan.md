## Implementation Plan: Composable Skills for Subagent Chat Modes

### Overview
Transpile `SUBAGENT.md` files into subagent.chatmode.md files by composing referenced skills from `.skill.md` files. The chatmode file is always generated during launch and never committed to git.

---

### Current State Analysis
- **User-defined file**: `SUBAGENT.md` with frontmatter containing `skills: ['research']`
- **Skill definitions**: research.skill.md containing reusable function definitions
- **Generated file**: subagent.chatmode.md (gitignored, auto-generated)
- **Copy mechanism**: `copy_agent_config()` in launch_agent.py will transpile and copy to subagents

---

### Architecture Components

#### 1. **Transpiler Module** (`src/lmspace/vscode/transpiler.py`)

**Key Functions:**

**`parse_frontmatter(content: str) -> tuple[dict, str]`**
- Extract YAML frontmatter between `---` delimiters
- Parse using PyYAML
- Return (metadata_dict, body_content)
- Handle missing or malformed frontmatter gracefully

**`resolve_skill_path(skill_name: str, agent_dir: Path, workspace_root: Path | None) -> Path`**
- Search for `{skill_name}.skill.md` in order:
  1. `{agent_dir}/contexts/{skill_name}.skill.md`
  2. `{workspace_root}/contexts/{skill_name}.skill.md` (if workspace_root provided)
- Raise `FileNotFoundError` with clear message if not found

**`find_workspace_root(start_dir: Path) -> Path | None`**
- Walk up directory tree from start_dir
- Look for `*.code-workspace` files
- Return parent directory of workspace file
- Return None if not found

**`load_skill_content(skill_path: Path) -> str`**
- Read skill file
- Strip frontmatter (only return body)
- Return skill content ready for composition

**`transpile_subagent(subagent_md_path: Path, output_path: Path | None = None) -> Path`**
- Main entry point
- Parse `SUBAGENT.md` frontmatter
- Extract `skills: [...]` list
- For each skill, resolve and load content
- Compose final chatmode: frontmatter + body + skill contents
- Write to output_path (default: same dir as input, named subagent.chatmode.md)
- Return path to generated file

**Composition Algorithm:**
```python
def transpile_subagent(subagent_md_path: Path, output_path: Path | None = None) -> Path:
    # Read source
    content = subagent_md_path.read_text(encoding='utf-8')
    frontmatter, body = parse_frontmatter(content)
    
    # Determine paths
    agent_dir = subagent_md_path.parent
    workspace_root = find_workspace_root(agent_dir)
    
    if output_path is None:
        output_path = agent_dir / "subagent.chatmode.md"
    
    # Start with agent definition
    chatmode_parts = []
    
    # Reconstruct frontmatter
    if frontmatter:
        chatmode_parts.append("---")
        chatmode_parts.append(yaml.dump(frontmatter, default_flow_style=False).strip())
        chatmode_parts.append("---")
    
    # Add body
    chatmode_parts.append(body.strip())
    
    # Append skills
    skills = frontmatter.get('skills', [])
    for skill_name in skills:
        skill_path = resolve_skill_path(skill_name, agent_dir, workspace_root)
        skill_content = load_skill_content(skill_path)
        chatmode_parts.append("")  # Blank line separator
        chatmode_parts.append(skill_content.strip())
    
    # Write output
    final_content = "\n".join(chatmode_parts) + "\n"
    output_path.write_text(final_content, encoding='utf-8')
    
    return output_path
```

---

#### 2. **CLI Integration** (Update cli.py)

**New Subcommand: `transpile`**
```bash
lmspace vscode transpile agents/vscode-expert [--output path/to/output.md]
```

**Add to cli.py:**
```python
def add_transpile_parser(subparsers: Any) -> None:
    """Add the 'transpile' subcommand parser."""
    parser = subparsers.add_parser(
        "transpile",
        help="Transpile SUBAGENT.md into subagent.chatmode.md with composed skills",
        description=(
            "Generate a chatmode file by composing SUBAGENT.md with referenced "
            "skill files from the skills frontmatter field."
        ),
    )
    parser.add_argument(
        "agent_dir",
        type=Path,
        help="Path to agent directory containing SUBAGENT.md",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help=(
            "Output path for generated chatmode file. "
            "Defaults to subagent.chatmode.md in agent directory."
        ),
    )

def handle_transpile_command(args: argparse.Namespace) -> int:
    """Handle the transpile command."""
    from .transpiler import transpile_subagent
    
    agent_dir = args.agent_dir.resolve()
    subagent_md = agent_dir / "SUBAGENT.md"
    
    if not subagent_md.exists():
        print(f"Error: SUBAGENT.md not found in {agent_dir}", file=sys.stderr)
        return 1
    
    try:
        output_path = transpile_subagent(subagent_md, args.output)
        print(f"Successfully transpiled to: {output_path}")
        return 0
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error transpiling: {e}", file=sys.stderr)
        return 1
```

---

#### 3. **Integration with Launch Agent** (Update launch_agent.py)

**Modify `copy_agent_config()` to always transpile:**

```python
def copy_agent_config(
    agent_template_dir: Path,
    subagent_dir: Path,
) -> dict:
    """Copy agent configuration to subagent with automatic transpilation.
    
    Transpiles SUBAGENT.md to subagent.chatmode.md and copies both to the
    subagent directory.
    
    Raises FileNotFoundError if SUBAGENT.md is missing.
    """
    from .transpiler import transpile_subagent
    
    subagent_md = agent_template_dir / "SUBAGENT.md"
    
    if not subagent_md.exists():
        raise FileNotFoundError(
            f"SUBAGENT.md not found in {agent_template_dir}. "
            "Agent configuration must be defined in SUBAGENT.md."
        )
    
    # Transpile to temporary location in agent template dir
    chatmode_src = transpile_subagent(
        subagent_md, 
        output_path=agent_template_dir / "subagent.chatmode.md"
    )
    
    # Also check for workspace file
    workspace_src = agent_template_dir / "subagent.code-workspace"
    
    # Fall back to default workspace template if not found in agent directory
    if not workspace_src.exists():
        default_template_dir = get_default_template_dir()
        workspace_src = default_template_dir / "subagent.code-workspace"
        if not workspace_src.exists():
            raise FileNotFoundError(f"Default workspace template not found: {workspace_src}")
    
    # Copy files to subagent
    chatmode_dst = subagent_dir / "subagent.chatmode.md"
    workspace_dst = subagent_dir / "subagent.code-workspace"
    
    shutil.copy2(chatmode_src, chatmode_dst)
    shutil.copy2(workspace_src, workspace_dst)
    
    # Create messages folder for storing responses
    messages_dir = subagent_dir / "messages"
    messages_dir.mkdir(exist_ok=True)
    
    return {
        "chatmode": str(chatmode_dst.resolve()),
        "workspace": str(workspace_dst.resolve()),
        "messages_dir": str(messages_dir.resolve()),
    }
```

---

#### 4. **Skill Resolution Strategy**

**Search Order for `{skill}.skill.md`:**
1. `{agent_dir}/contexts/{skill}.skill.md` (agent-local skills)
2. `{workspace_root}/contexts/{skill}.skill.md` (shared workspace skills)

**Workspace Root Detection:**
- Start from agent directory
- Walk up parent directories
- Find first `*.code-workspace` file
- Return directory containing workspace file
- Return None if no workspace found (only check agent-local contexts)

**Error Messages:**
```python
# When skill not found
raise FileNotFoundError(
    f"Skill '{skill_name}' not found. Searched:\n"
    f"  - {agent_dir}/contexts/{skill_name}.skill.md\n"
    f"  - {workspace_root}/contexts/{skill_name}.skill.md"
)
```

---

#### 5. **Testing Strategy**

**`tests/test_vscode_transpile.py`:**

Test fixtures structure:
```
tests/fixtures/transpile/
  agent_simple/
    SUBAGENT.md
    contexts/
      local-skill.skill.md
  agent_multi_skills/
    SUBAGENT.md
  workspace_contexts/
    research.skill.md
    code-review.skill.md
  test.code-workspace
```

**Test cases:**
- `test_parse_frontmatter_valid()`: Parse YAML between ---
- `test_parse_frontmatter_no_frontmatter()`: Empty dict, full content as body
- `test_parse_frontmatter_malformed()`: Handle errors gracefully
- `test_find_workspace_root()`: Find .code-workspace file
- `test_find_workspace_root_not_found()`: Return None
- `test_resolve_skill_path_agent_local()`: Find skill in agent contexts
- `test_resolve_skill_path_workspace()`: Find skill in workspace contexts
- `test_resolve_skill_path_not_found()`: Raise FileNotFoundError
- `test_load_skill_content_strips_frontmatter()`: Only body returned
- `test_transpile_single_skill()`: Basic transpilation with one skill
- `test_transpile_multiple_skills()`: Compose multiple skills in order
- `test_transpile_no_skills()`: Passthrough when skills=[]
- `test_transpile_missing_subagent_md()`: Raise error

**`tests/test_integration_transpile.py`:**
- `test_launch_agent_transpiles_on_copy()`: Verify `copy_agent_config()` calls transpiler
- `test_cli_transpile_command()`: Test CLI end-to-end

---

#### 6. **Frontmatter Schema**

**SUBAGENT.md:**
```yaml
---
description: 'VS Code prompt & instruction system expert'
skills: ['research']
model: GPT-5 mini (copilot)
tools: ['edit', 'search', 'fetch', ...]
---

interface VSCodeExpert {
  domain: "prompt files, instructions, chat modes, CLI"
  
  sources = [...]
  
  research(domain, sources)
}
```

**Skill File (research.skill.md):**
```yaml
---
description: Research Skill with grounded answers
tools: ['fetch', 'githubRepo']
model: Grok Code Fast 1 (copilot)
---

function research(domain, sources) {
  constraints { ... }
  workflow { ... }
}
```

**Frontmatter Handling:**
- Agent frontmatter is preserved as-is in chatmode
- Skill frontmatter is stripped (not included in output)
- Future: Could merge tools/model if needed, but not in Phase 1-4

---

### Implementation Phases

#### **Phase 1: Core Transpiler**
- [ ] Create `src/lmspace/vscode/transpiler.py`
- [ ] Implement `parse_frontmatter()`
- [ ] Implement `load_skill_content()` with frontmatter stripping
- [ ] Implement `transpile_subagent()` basic composition (no skill resolution yet)
- [ ] Add unit tests for parsing and composition
- [ ] Manual test with simple SUBAGENT.md (no skills)

#### **Phase 2: CLI Command**
- [ ] Add `add_transpile_parser()` to cli.py
- [ ] Implement `handle_transpile_command()`
- [ ] Wire up command in main CLI router
- [ ] Test CLI: `lmspace vscode transpile agents/vscode-expert`

#### **Phase 3: Launch Agent Integration**
- [ ] Update `copy_agent_config()` to call transpiler
- [ ] Remove old chatmode fallback logic
- [ ] Update error messages for missing SUBAGENT.md
- [ ] Test `lmspace vscode chat` end-to-end
- [ ] Add integration tests

#### **Phase 4: Skill Resolution**
- [ ] Implement `find_workspace_root()`
- [ ] Implement `resolve_skill_path()` with multi-path search
- [ ] Update `transpile_subagent()` to resolve and load skills
- [ ] Add tests for skill resolution
- [ ] Test with vscode-expert agent using research skill
- [ ] Comprehensive error messages for missing skills

---

### File Structure After Implementation

```
src/lmspace/vscode/
  transpiler.py          # NEW: Core transpilation logic
  cli.py                 # UPDATED: Add transpile command
  launch_agent.py        # UPDATED: Always transpile in copy_agent_config
  
tests/
  test_vscode_transpile.py       # NEW: Unit tests
  test_integration_transpile.py  # NEW: Integration tests
  fixtures/
    transpile/
      agent_simple/
      agent_multi_skills/
      workspace_contexts/
      test.code-workspace

docs/examples/vscode-simple/
  agents/
    vscode-expert/
      SUBAGENT.md                 # Source (committed)
      subagent.chatmode.md        # Generated (gitignored)
  contexts/
    research.skill.md             # Shared skill
```

**Add to .gitignore:**
```
**/subagent.chatmode.md
```

---

### Dependencies

**Existing:**
- `pyyaml>=6.0.3` (already in dependencies)

**No new dependencies required**

---

### Success Criteria

1. ✅ `SUBAGENT.md` is the single source of truth
2. ✅ `lmspace vscode transpile agents/vscode-expert` generates valid chatmode
3. ✅ Generated chatmode includes frontmatter + body + all skill contents
4. ✅ `lmspace vscode chat` auto-transpiles during launch
5. ✅ Skills resolve from agent-local or workspace contexts
6. ✅ Clear error messages for missing SUBAGENT.md or skills
7. ✅ All tests pass with >85% coverage

---

### Migration Notes

**For existing agents:**
1. Keep `SUBAGENT.md` as source
2. Delete subagent.chatmode.md (will be auto-generated)
3. Add subagent.chatmode.md to .gitignore
4. Extract reusable functions to `contexts/*.skill.md`
5. Reference skills in `skills: [...]` frontmatter

**No backward compatibility needed** - all agents must use SUBAGENT.md going forward.