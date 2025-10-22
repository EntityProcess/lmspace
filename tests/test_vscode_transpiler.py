import textwrap
from pathlib import Path

import pytest

from lmspace.vscode.transpiler import (
    SkillResolutionError,
    SkillDefinitionError,
    render_chatmode,
    transpile_skill,
)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content).lstrip("\n"), encoding="utf-8")


def test_transpile_skill_writes_chatmode(tmp_path: Path) -> None:
    skill_dir = tmp_path / "skill"
    skill_dir.mkdir()

    _write(
        skill_dir / "SKILL.md",
        """
        ---
        description: Example Agent
        model: test-model
        tools: [one, two]
        ---

        interface Example {}
        """,
    )

    output_path = tmp_path / "build" / "subagent.chatmode.md"
    result_path = transpile_skill(skill_dir, output_path=output_path)

    assert result_path == output_path.resolve()
    content = output_path.read_text(encoding="utf-8")
    assert content.startswith("---\n")
    assert "description: Example Agent" in content
    assert "interface Example {}" in content
    assert content.rstrip().endswith("interface Example {}")


def test_transpile_excludes_skills_from_chatmode_frontmatter(tmp_path: Path) -> None:
    skill_dir = tmp_path / "skill"
    skill_dir.mkdir()

    _write(
        skill_dir / "SKILL.md",
        """
        ---
        description: Agent with skills
        model: test-model
        tools: [one, two]
        skills: [research, analysis]
        ---

        Agent body.
        """,
    )
    
    # Create the skill files so the transpiler can resolve them
    _write(
        skill_dir / "research.skill.md",
        """
        Research skill content.
        """,
    )
    
    _write(
        skill_dir / "analysis.skill.md",
        """
        Analysis skill content.
        """,
    )

    chatmode = render_chatmode(skill_dir)
    
    # The skills property should NOT appear in the chatmode frontmatter
    assert "skills:" not in chatmode
    # But other properties should still be there
    assert "description: Agent with skills" in chatmode
    assert "model: test-model" in chatmode
    assert "tools:" in chatmode
    # And the skill bodies should be included
    assert "Research skill content." in chatmode
    assert "Analysis skill content." in chatmode


def test_transpile_includes_skill_bodies_from_skill_and_workspace(tmp_path: Path) -> None:
    skill_dir = tmp_path / "skill"
    skill_dir.mkdir()

    _write(
        skill_dir / "SKILL.md",
        """
        ---
        description: Skilled Agent
        model: test-model
        tools: [alpha]
        skills: [skill-specific, shared-skill]
        ---

        Skill body section.
        """,
    )

    _write(
        skill_dir / "skill-specific.skill.md",
        """
        ---
        summary: skill-specific
        ---

        Skill-specific body line.
        """,
    )

    workspace_root = tmp_path / "workspace"
    _write(
        workspace_root / "contexts" / "shared-skill.skill.md",
        """
        ---
        note: shared
        ---

        Workspace shared skill body.
        """,
    )

    chatmode = render_chatmode(skill_dir, workspace_root=workspace_root)

    assert "Skill body section." in chatmode
    assert "Skill-specific body line." in chatmode
    assert "Workspace shared skill body." in chatmode
    # Skill frontmatter should not leak into the output
    assert "summary:" not in chatmode
    assert "note:" not in chatmode


def test_transpile_missing_skill(tmp_path: Path) -> None:
    skill_dir = tmp_path / "missing"
    skill_dir.mkdir()

    with pytest.raises(FileNotFoundError):
        render_chatmode(skill_dir)


def test_transpile_invalid_frontmatter(tmp_path: Path) -> None:
    skill_dir = tmp_path / "skill"
    skill_dir.mkdir()

    _write(
        skill_dir / "SKILL.md",
        """
        ---
        description: Missing terminator

        Body without closing delimiter.
        """,
    )

    with pytest.raises(SkillDefinitionError):
        render_chatmode(skill_dir)


def test_transpile_missing_skill_reports_all_attempts(tmp_path: Path) -> None:
    skill_dir = tmp_path / "skill"
    skill_dir.mkdir()

    _write(
        skill_dir / "SKILL.md",
        """
        ---
        description: Skill seeker
        model: test
        skills: [unknown]
        ---

        Body text.
        """,
    )

    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()

    with pytest.raises(SkillResolutionError) as exc:
        render_chatmode(skill_dir, workspace_root=workspace_root)

    message = str(exc.value)
    assert "unknown" in message
    assert str(skill_dir / "unknown.skill.md") in message
    assert str(workspace_root / "contexts" / "unknown.skill.md") in message
