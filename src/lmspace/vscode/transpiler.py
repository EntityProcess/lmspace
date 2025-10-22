"""Generate VS Code chatmode files from SKILL definitions."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional, Sequence

import yaml

SKILL_FILENAME = "SKILL.md"
CHATMODE_FILENAME = "subagent.chatmode.md"
CONTEXTS_DIRNAME = "contexts"
SKILL_SUFFIX = ".skill.md"


class SkillDefinitionError(ValueError):
    """Raised when a SKILL.md file is malformed."""


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
            raise SkillDefinitionError(
                f"{path} is missing a closing '---' delimiter for its frontmatter."
            )
        frontmatter = "".join(lines[1:closing])
        body = "".join(lines[closing + 1 :])
        return frontmatter, body

    if require:
        raise SkillDefinitionError(
            f"{path} must start with a YAML frontmatter block delimited by '---'."
        )

    return None, text


def _load_skill_definition(skill_dir: Path) -> tuple[dict[str, Any], str, list[str], str]:
    """Load and validate SKILL.md from a skill directory."""
    skill_path = skill_dir / SKILL_FILENAME
    if not skill_path.exists():
        raise FileNotFoundError(f"SKILL.md not found at {skill_path}")

    text = skill_path.read_text(encoding="utf-8")
    if not text.strip():
        raise SkillDefinitionError(f"{skill_path} is empty.")

    frontmatter_text, body = _split_frontmatter(
        text,
        path=skill_path,
        require=True,
    )

    try:
        data = yaml.safe_load(frontmatter_text or "") or {}
    except yaml.YAMLError as error:
        raise SkillDefinitionError(
            f"Failed to parse frontmatter in {skill_path}: {error}"
        ) from error

    if not isinstance(data, dict):
        raise SkillDefinitionError(
            f"Frontmatter in {skill_path} must be a mapping."
        )

    skills_raw = data.get("skills", [])
    if skills_raw is None:
        skills: list[str] = []
    elif isinstance(skills_raw, Sequence) and not isinstance(skills_raw, (str, bytes)):
        skills = []
        for skill in skills_raw:
            if not isinstance(skill, str) or not skill.strip():
                raise SkillDefinitionError(
                    f"'skills' entries in {skill_path} must be non-empty strings."
                )
            skills.append(skill.strip())
    else:
        raise SkillDefinitionError(
            f"'skills' frontmatter in {skill_path} must be a sequence of strings."
        )

    return data, body, skills, frontmatter_text or ""


def _get_skill_search_locations(
    skill: str,
    *,
    skill_dir: Path,
    workspace_root: Optional[Path],
) -> list[Path]:
    """Build the search path list for a skill file.
    
    Search order:
    1. Sibling to SKILL.md (e.g., skills/vscode-expert/research.skill.md)
    2. In the skills folder itself (e.g., skills/research.skill.md)
    3. Sibling contexts folder (e.g., contexts/research.skill.md)
    4. Explicit workspace_root/contexts if provided
    """
    skill_filename = f"{skill}{SKILL_SUFFIX}"
    
    locations_to_check: list[Path] = [
        skill_dir / skill_filename,  # Sibling to SKILL.md
    ]
    
    # If skill is in a skills/ directory, check the skills/ folder and sibling contexts/
    if skill_dir.parent.name == "skills":
        skills_folder = skill_dir.parent
        locations_to_check.append(skills_folder / skill_filename)  # In skills/ folder
        
        workspace_contexts = skills_folder.parent / CONTEXTS_DIRNAME / skill_filename
        locations_to_check.append(workspace_contexts)  # Sibling contexts/
    
    # Also check explicit workspace_root if provided
    if workspace_root is not None:
        workspace_skill = workspace_root / CONTEXTS_DIRNAME / skill_filename
        if workspace_skill not in locations_to_check:
            locations_to_check.append(workspace_skill)
    
    return locations_to_check


def _resolve_skill_body(
    skill: str,
    *,
    skill_dir: Path,
    workspace_root: Optional[Path],
) -> str:
    """Load a skill body from the skill directory or workspace contexts."""
    locations_to_check = _get_skill_search_locations(
        skill,
        skill_dir=skill_dir,
        workspace_root=workspace_root,
    )
    
    for skill_path in locations_to_check:
        if skill_path.exists():
            text = skill_path.read_text(encoding="utf-8")
            _, body = _split_frontmatter(
                text,
                path=skill_path,
                require=False,
            )
            return body.strip("\n")

    raise SkillResolutionError(skill, locations_to_check)


def _compose_chatmode(
    frontmatter_text: str,
    body: str,
    skill_bodies: Sequence[str],
) -> str:
    """Compose the final chatmode document."""
    # Remove the 'skills' line from frontmatter while preserving formatting
    lines = frontmatter_text.splitlines(keepends=True)
    filtered_lines = []
    for line in lines:
        # Skip lines that define the skills property
        if not line.strip().startswith("skills:"):
            filtered_lines.append(line)
    
    frontmatter_block = "".join(filtered_lines).strip("\n")

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
    skill_dir: Path,
    *,
    workspace_root: Optional[Path] = None,
) -> str:
    """Return the generated chatmode string without writing it to disk."""
    _, body, skills, frontmatter_text = _load_skill_definition(skill_dir)
    skill_bodies = [
        _resolve_skill_body(
            skill,
            skill_dir=skill_dir,
            workspace_root=workspace_root,
        )
        for skill in skills
    ]
    return _compose_chatmode(frontmatter_text, body, skill_bodies)


def transpile_skill(
    skill_dir: Path,
    *,
    output_path: Optional[Path] = None,
    workspace_root: Optional[Path] = None,
) -> Path:
    """Generate a chatmode file from a SKILL definition."""
    chatmode_text = render_chatmode(skill_dir, workspace_root=workspace_root)

    target_path = output_path or skill_dir / CHATMODE_FILENAME
    target_path = target_path.resolve()
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(chatmode_text, encoding="utf-8")
    return target_path


__all__ = [
    "CHATMODE_FILENAME",
    "CONTEXTS_DIRNAME",
    "SKILL_SUFFIX",
    "SKILL_FILENAME",
    "SkillDefinitionError",
    "SkillResolutionError",
    "render_chatmode",
    "transpile_skill",
    "_load_skill_definition",
    "_get_skill_search_locations",
]
