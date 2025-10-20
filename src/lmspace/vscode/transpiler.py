"""Generate VS Code chatmode files from SUBAGENT definitions."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional, Sequence

import yaml

SUBAGENT_FILENAME = "SUBAGENT.md"
CHATMODE_FILENAME = "subagent.chatmode.md"
CONTEXTS_DIRNAME = "contexts"
SKILL_SUFFIX = ".skill.md"


class SubagentDefinitionError(ValueError):
    """Raised when a SUBAGENT.md file is malformed."""


class SkillResolutionError(FileNotFoundError):
    """Raised when a referenced skill cannot be located."""

    def __init__(self, skill: str, attempted_paths: Sequence[Path]) -> None:
        attempted = ", ".join(str(path) for path in attempted_paths)
        message = f"Skill '{skill}' not found. Looked in: {attempted}"
        super().__init__(message)
        self.skill = skill
        self.attempted_paths = list(attempted_paths)


def _split_frontmatter(
    text: str,
    *,
    path: Path,
    require: bool,
) -> tuple[Optional[str], str]:
    """Separate a Markdown document into frontmatter and body."""
    if text.startswith("---"):
        lines = text.splitlines(keepends=True)
        closing = None
        for index, line in enumerate(lines[1:], start=1):
            if line.strip() == "---":
                closing = index
                break
        if closing is None:
            raise SubagentDefinitionError(
                f"{path} is missing a closing '---' delimiter for its frontmatter."
            )
        frontmatter = "".join(lines[1:closing])
        body = "".join(lines[closing + 1 :])
        return frontmatter, body

    if require:
        raise SubagentDefinitionError(
            f"{path} must start with a YAML frontmatter block delimited by '---'."
        )

    return None, text


def _load_subagent_definition(agent_dir: Path) -> tuple[dict[str, Any], str, list[str], str]:
    """Load and validate SUBAGENT.md from an agent directory."""
    subagent_path = agent_dir / SUBAGENT_FILENAME
    if not subagent_path.exists():
        raise FileNotFoundError(f"SUBAGENT.md not found at {subagent_path}")

    text = subagent_path.read_text(encoding="utf-8")
    if not text.strip():
        raise SubagentDefinitionError(f"{subagent_path} is empty.")

    frontmatter_text, body = _split_frontmatter(
        text,
        path=subagent_path,
        require=True,
    )

    try:
        data = yaml.safe_load(frontmatter_text or "") or {}
    except yaml.YAMLError as error:
        raise SubagentDefinitionError(
            f"Failed to parse frontmatter in {subagent_path}: {error}"
        ) from error

    if not isinstance(data, dict):
        raise SubagentDefinitionError(
            f"Frontmatter in {subagent_path} must be a mapping."
        )

    skills_raw = data.get("skills", [])
    if skills_raw is None:
        skills: list[str] = []
    elif isinstance(skills_raw, Sequence) and not isinstance(skills_raw, (str, bytes)):
        skills = []
        for skill in skills_raw:
            if not isinstance(skill, str) or not skill.strip():
                raise SubagentDefinitionError(
                    f"'skills' entries in {subagent_path} must be non-empty strings."
                )
            skills.append(skill.strip())
    else:
        raise SubagentDefinitionError(
            f"'skills' frontmatter in {subagent_path} must be a sequence of strings."
        )

    return data, body, skills, frontmatter_text or ""


def _resolve_skill_body(
    skill: str,
    *,
    agent_dir: Path,
    workspace_root: Optional[Path],
) -> str:
    """Load a skill body from the agent or workspace contexts."""
    attempted_paths: list[Path] = []
    skill_filename = f"{skill}{SKILL_SUFFIX}"
    
    # Search order:
    # 1. Sibling to SUBAGENT.md (e.g., agents/vscode-expert/research.skill.md)
    # 2. In the agents folder itself (e.g., agents/research.skill.md)
    # 3. Sibling contexts folder (e.g., contexts/research.skill.md)
    # 4. Explicit workspace_root/contexts if provided
    
    locations_to_check: list[Path] = [
        agent_dir / skill_filename,  # Sibling to SUBAGENT.md
    ]
    
    # If agent is in an agents/ directory, check the agents/ folder and sibling contexts/
    if agent_dir.parent.name == "agents":
        agents_folder = agent_dir.parent
        locations_to_check.append(agents_folder / skill_filename)  # In agents/ folder
        
        workspace_contexts = agents_folder.parent / CONTEXTS_DIRNAME / skill_filename
        locations_to_check.append(workspace_contexts)  # Sibling contexts/
    
    # Also check explicit workspace_root if provided
    if workspace_root is not None:
        workspace_skill = workspace_root / CONTEXTS_DIRNAME / skill_filename
        if workspace_skill not in locations_to_check:
            locations_to_check.append(workspace_skill)

    for skill_path in locations_to_check:
        attempted_paths.append(skill_path)
        if skill_path.exists():
            text = skill_path.read_text(encoding="utf-8")
            _, body = _split_frontmatter(
                text,
                path=skill_path,
                require=False,
            )
            return body.strip("\n")

    raise SkillResolutionError(skill, attempted_paths)


def _compose_chatmode(
    frontmatter_text: str,
    body: str,
    skill_bodies: Sequence[str],
) -> str:
    """Compose the final chatmode document."""
    frontmatter_block = frontmatter_text.strip("\n")

    sections: list[str] = []
    body_section = body.strip("\n")
    if body_section:
        sections.append(body_section)

    for skill_body in skill_bodies:
        skill_section = skill_body.strip("\n")
        if skill_section:
            sections.append(skill_section)

    if sections:
        combined = "\n\n".join(sections)
        return f"---\n{frontmatter_block}\n---\n\n{combined}\n"

    return f"---\n{frontmatter_block}\n---\n"


def render_chatmode(
    agent_dir: Path,
    *,
    workspace_root: Optional[Path] = None,
) -> str:
    """Return the generated chatmode string without writing it to disk."""
    _, body, skills, frontmatter_text = _load_subagent_definition(agent_dir)
    skill_bodies = [
        _resolve_skill_body(
            skill,
            agent_dir=agent_dir,
            workspace_root=workspace_root,
        )
        for skill in skills
    ]
    return _compose_chatmode(frontmatter_text, body, skill_bodies)


def transpile_subagent(
    agent_dir: Path,
    *,
    output_path: Optional[Path] = None,
    workspace_root: Optional[Path] = None,
) -> Path:
    """Generate a chatmode file from a SUBAGENT definition."""
    chatmode_text = render_chatmode(agent_dir, workspace_root=workspace_root)

    target_path = output_path or agent_dir / CHATMODE_FILENAME
    target_path = target_path.resolve()
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(chatmode_text, encoding="utf-8")
    return target_path


__all__ = [
    "CHATMODE_FILENAME",
    "CONTEXTS_DIRNAME",
    "SKILL_SUFFIX",
    "SubagentDefinitionError",
    "SkillResolutionError",
    "render_chatmode",
    "transpile_subagent",
]
