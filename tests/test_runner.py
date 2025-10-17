from dataclasses import dataclass
from pathlib import Path

import pytest

from lmspace.config import AgentConfig, LoadedConfig
from lmspace.fetcher import RetrievedFile
from lmspace.runner import Runner


@dataclass
class StubAzureService:
    last_files: list[RetrievedFile] | None = None

    def provision(self, config: AgentConfig, files: list[RetrievedFile]):
        self.last_files = files
        return type("Result", (), {
            "assistant_id": "assistant-123",
            "vector_store_id": "vs-123",
            "file_ids": ["file-1"],
            "framework_agent_id": "agent-123",
        })()


def make_loaded_config(tmp_path: Path) -> LoadedConfig:
    config = AgentConfig(name="Test", instructions="Do it", urls=["https://example.com/file.txt"])
    return LoadedConfig(path=tmp_path / "config.yaml", config=config)


class DummyFetcher:
    def __init__(self, files: list[RetrievedFile]):
        self._files = files

    def fetch_many(self, urls):
        return self._files

    def close(self):
        pass


def test_runner_dry_run(tmp_path: Path) -> None:
    fetcher = DummyFetcher(files=[RetrievedFile(url="u", filename="f.txt", content_type=None, data=b"data")])
    runner = Runner(fetcher=fetcher, azure_service=None, dry_run=True)
    result = runner.run_single(make_loaded_config(tmp_path))

    assert result.assistant_id is None
    assert result.file_count == 1


def test_runner_invokes_azure_service(tmp_path: Path) -> None:
    files = [RetrievedFile(url="u", filename="f.txt", content_type=None, data=b"data")]
    fetcher = DummyFetcher(files=files)
    stub_service = StubAzureService()

    runner = Runner(fetcher=fetcher, azure_service=stub_service, dry_run=False)
    result = runner.run_single(make_loaded_config(tmp_path))

    assert result.assistant_id == "assistant-123"
    assert stub_service.last_files == files


def test_runner_requires_service_when_not_dry_run(tmp_path: Path) -> None:
    fetcher = DummyFetcher(files=[])
    runner = Runner(fetcher=fetcher, azure_service=None, dry_run=False)

    with pytest.raises(RuntimeError):
        runner.run_single(make_loaded_config(tmp_path))
