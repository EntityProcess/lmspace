import textwrap
from pathlib import Path

import pytest

from lmspace import cli
from lmspace.vscode.transpiler import CHATMODE_FILENAME


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content).lstrip("\n"), encoding="utf-8")


def test_cli_transpile_generates_chatmode_with_workspace(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    skill_dir = tmp_path / "skill"
    skill_dir.mkdir()
    workspace_root = tmp_path / "workspace"

    _write(
        skill_dir / "SKILL.md",
        """
        ---
        description: CLI Agent
        model: test
        tools: [alpha]
        skills: [workspace-skill]
        ---

        CLI body section.
        """,
    )

    _write(
        workspace_root / "contexts" / "workspace-skill.skill.md",
        """
        ---
        note: workspace
        ---

        Workspace skill body line.
        """,
    )

    output_path = tmp_path / "output" / CHATMODE_FILENAME
    exit_code = cli.main(
        [
            "code",
            "transpile",
            str(skill_dir),
            "--workspace-root",
            str(workspace_root),
            "--output",
            str(output_path),
        ]
    )

    assert exit_code == 0
    captured = capsys.readouterr()
    assert "generated chatmode" in captured.out
    assert str(output_path.resolve()) in captured.out
    content = output_path.read_text(encoding="utf-8")
    assert "CLI body section." in content
    assert "Workspace skill body line." in content
    assert "note:" not in content


def test_cli_transpile_failure_is_reported(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    skill_dir = tmp_path / "skill"
    skill_dir.mkdir()

    _write(
        skill_dir / "SKILL.md",
        """
        ---
        description: Missing Skill Agent
        model: test
        skills: [missing]
        ---

        Body text.
        """,
    )

    exit_code = cli.main([
        "code",
        "transpile",
        str(skill_dir),
    ])

    assert exit_code == 1
    captured = capsys.readouterr()
    assert "error:" in captured.err
    assert "missing.skill.md" in captured.err
    assert not (skill_dir / CHATMODE_FILENAME).exists()
