"""Tests for lmspace code skills command."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from lmspace.vscode.cli import handle_skills


def test_skills_resolves_paths(tmp_path: Path, capsys) -> None:
    """Test that skills command resolves and outputs skill paths as JSON."""
    # Create agent directory structure
    agent_dir = tmp_path / "agents" / "test-agent"
    agent_dir.mkdir(parents=True)
    
    contexts_dir = tmp_path / "contexts"
    contexts_dir.mkdir()
    
    # Create SUBAGENT.md with skills
    subagent_content = """---
skills: ['research', 'analysis']
---

Test agent description.
"""
    (agent_dir / "SUBAGENT.md").write_text(subagent_content)
    
    # Create skill files
    (agent_dir / "research.skill.md").write_text("# Research skill")
    (contexts_dir / "analysis.skill.md").write_text("# Analysis skill")
    
    # Create args namespace
    class Args:
        agent_config_path = agent_dir
        workspace_root = tmp_path
    
    # Execute command
    exit_code = handle_skills(Args())
    
    assert exit_code == 0
    
    # Check JSON output
    captured = capsys.readouterr()
    paths = json.loads(captured.out.strip())
    
    assert len(paths) == 2
    assert paths[0].endswith("research.skill.md")
    assert paths[1].endswith("analysis.skill.md")


def test_skills_missing_skill_file(tmp_path: Path, capsys) -> None:
    """Test that missing skill file returns error."""
    agent_dir = tmp_path / "agents" / "test-agent"
    agent_dir.mkdir(parents=True)
    
    subagent_content = """---
skills: ['missing']
---

Test agent.
"""
    (agent_dir / "SUBAGENT.md").write_text(subagent_content)
    
    class Args:
        agent_config_path = agent_dir
        workspace_root = None
    
    exit_code = handle_skills(Args())
    
    assert exit_code == 1
    captured = capsys.readouterr()
    assert "Skill 'missing' not found" in captured.err


def test_skills_no_skills(tmp_path: Path, capsys) -> None:
    """Test agent with no skills returns empty array."""
    agent_dir = tmp_path / "agents" / "test-agent"
    agent_dir.mkdir(parents=True)
    
    subagent_content = """---
skills: []
---

Test agent with no skills.
"""
    (agent_dir / "SUBAGENT.md").write_text(subagent_content)
    
    class Args:
        agent_config_path = agent_dir
        workspace_root = None
    
    exit_code = handle_skills(Args())
    
    assert exit_code == 0
    captured = capsys.readouterr()
    paths = json.loads(captured.out.strip())
    assert paths == []
