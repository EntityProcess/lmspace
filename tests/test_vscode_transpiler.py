import textwrap
from pathlib import Path

import pytest

from lmspace.vscode.transpiler import (
    SkillResolutionError,
    SubagentDefinitionError,
    render_chatmode,
    transpile_subagent,
)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content).lstrip("\n"), encoding="utf-8")


def test_transpile_subagent_writes_chatmode(tmp_path: Path) -> None:
    agent_dir = tmp_path / "agent"
    agent_dir.mkdir()

    _write(
        agent_dir / "SUBAGENT.md",
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
    result_path = transpile_subagent(agent_dir, output_path=output_path)

    assert result_path == output_path.resolve()
    content = output_path.read_text(encoding="utf-8")
    assert content.startswith("---\n")
    assert "description: Example Agent" in content
    assert "interface Example {}" in content
    assert content.rstrip().endswith("interface Example {}")


def test_transpile_includes_skill_bodies_from_agent_and_workspace(tmp_path: Path) -> None:
    agent_dir = tmp_path / "agent"
    agent_dir.mkdir()

    _write(
        agent_dir / "SUBAGENT.md",
        """
        ---
        description: Skilled Agent
        model: test-model
        tools: [alpha]
        skills: [agent-skill, shared-skill]
        ---

        Agent body section.
        """,
    )

    _write(
        agent_dir / "contexts" / "agent-skill.skill.md",
        """
        ---
        summary: agent skill
        ---

        Agent skill body line.
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

    chatmode = render_chatmode(agent_dir, workspace_root=workspace_root)

    assert "Agent body section." in chatmode
    assert "Agent skill body line." in chatmode
    assert "Workspace shared skill body." in chatmode
    # Skill frontmatter should not leak into the output
    assert "summary:" not in chatmode
    assert "note:" not in chatmode


def test_transpile_missing_subagent(tmp_path: Path) -> None:
    agent_dir = tmp_path / "missing"
    agent_dir.mkdir()

    with pytest.raises(FileNotFoundError):
        render_chatmode(agent_dir)


def test_transpile_invalid_frontmatter(tmp_path: Path) -> None:
    agent_dir = tmp_path / "agent"
    agent_dir.mkdir()

    _write(
        agent_dir / "SUBAGENT.md",
        """
        ---
        description: Missing terminator

        Body without closing delimiter.
        """,
    )

    with pytest.raises(SubagentDefinitionError):
        render_chatmode(agent_dir)


def test_transpile_missing_skill_reports_all_attempts(tmp_path: Path) -> None:
    agent_dir = tmp_path / "agent"
    agent_dir.mkdir()

    _write(
        agent_dir / "SUBAGENT.md",
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
        render_chatmode(agent_dir, workspace_root=workspace_root)

    message = str(exc.value)
    assert "unknown" in message
    assert str(agent_dir / "contexts" / "unknown.skill.md") in message
    assert str(workspace_root / "contexts" / "unknown.skill.md") in message
