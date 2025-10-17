from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

from .azure import AzureAssistantsService, ProvisionedResources
from .config import LoadedConfig
from .fetcher import ContentFetcher, RetrievedFile

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RunnerResult:
    config_path: Path
    assistant_id: str | None
    vector_store_id: str | None
    framework_agent_id: str | None
    file_count: int


class Runner:
    def __init__(self, *, fetcher: ContentFetcher, azure_service: AzureAssistantsService | None, dry_run: bool = False) -> None:
        self._fetcher = fetcher
        self._azure = azure_service
        self._dry_run = dry_run

    def run_all(self, configs: Sequence[LoadedConfig]) -> list[RunnerResult]:
        results: list[RunnerResult] = []
        for loaded in configs:
            results.append(self.run_single(loaded))
        return results

    def run_single(self, loaded: LoadedConfig) -> RunnerResult:
        logger.info("Processing config %s", loaded.path)
        files = self._download_files(loaded.config.urls)
        if self._dry_run:
            logger.info("Dry-run enabled; skipping Azure provisioning")
            return RunnerResult(
                config_path=loaded.path,
                assistant_id=None,
                vector_store_id=None,
                framework_agent_id=None,
                file_count=len(files),
            )

        if self._azure is None:
            raise RuntimeError("AzureAssistantsService is required unless dry_run is enabled")

        resources = self._azure.provision(loaded.config, files)
        return RunnerResult(
            config_path=loaded.path,
            assistant_id=resources.assistant_id,
            vector_store_id=resources.vector_store_id,
            framework_agent_id=resources.framework_agent_id,
            file_count=len(resources.file_ids),
        )

    def _download_files(self, urls: Iterable[object]) -> list[RetrievedFile]:
        normalized = [str(url) for url in urls]
        if not normalized:
            logger.warning("Config does not specify any URLs")
            return []
        return self._fetcher.fetch_many(normalized)


__all__ = ["Runner", "RunnerResult"]
