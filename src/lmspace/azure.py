from __future__ import annotations

import io
import logging
import os
import re
from dataclasses import dataclass
from typing import Iterable

from azure.identity import DefaultAzureCredential
from openai import AzureOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

try:
    from agent_framework.azure import AzureOpenAIResponsesClient
except ImportError:  # pragma: no cover
    AzureOpenAIResponsesClient = None  # type: ignore[assignment]

from .config import AgentConfig
from .fetcher import RetrievedFile

logger = logging.getLogger(__name__)

_DEFAULT_SCOPE = "https://cognitiveservices.azure.com/.default"


class AzureConfigurationError(RuntimeError):
    pass


@dataclass(frozen=True)
class ProvisionedResources:
    assistant_id: str
    vector_store_id: str
    file_ids: list[str]
    framework_agent_id: str | None


class AzureAssistantsService:
    def __init__(
        self,
        *,
        client: AzureOpenAI,
        deployment: str,
        framework_client: AzureOpenAIResponsesClient | None = None,
        vector_store_prefix: str = "lmspace"
    ) -> None:
        self._client = client
        self._deployment = deployment
        self._framework_client = framework_client
        self._vector_store_prefix = vector_store_prefix

    @classmethod
    def from_env(cls, *, vector_store_prefix: str = "lmspace") -> "AzureAssistantsService":
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        if not endpoint:
            raise AzureConfigurationError("AZURE_OPENAI_ENDPOINT is not set")

        api_version = os.getenv("AZURE_OPENAI_API_VERSION")
        if not api_version:
            raise AzureConfigurationError("AZURE_OPENAI_API_VERSION is not set")

        deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
        if not deployment:
            raise AzureConfigurationError("AZURE_OPENAI_DEPLOYMENT_NAME is not set")

        api_key = os.getenv("AZURE_OPENAI_API_KEY")
        if api_key:
            client = AzureOpenAI(azure_endpoint=endpoint, api_version=api_version, api_key=api_key)
        else:
            credential = DefaultAzureCredential(exclude_shared_token_cache_credential=True)

            def _token_provider() -> str:
                token = credential.get_token(_DEFAULT_SCOPE)
                return token.token

            client = AzureOpenAI(azure_endpoint=endpoint, api_version=api_version, azure_ad_token_provider=_token_provider)

        framework_client = None
        if AzureOpenAIResponsesClient is not None:
            try:
                framework_client = AzureOpenAIResponsesClient.from_env()
            except Exception as exc:  # pragma: no cover - defensive logging
                logger.warning("Failed to create Agent Framework client: %s", exc)

        return cls(client=client, deployment=deployment, framework_client=framework_client, vector_store_prefix=vector_store_prefix)

    @retry(wait=wait_exponential(min=1, max=8), stop=stop_after_attempt(3))
    def upload_files(self, files: Iterable[RetrievedFile]) -> list[str]:
        file_ids: list[str] = []
        for file in files:
            logger.info("Uploading %s to Azure OpenAI", file.filename)
            file_ids.append(
                self._client.files.create(
                    file=(file.filename, io.BytesIO(file.data), file.content_type or "application/octet-stream"),
                    purpose="assistants",
                ).id
            )
        return file_ids

    def create_vector_store(self, config: AgentConfig) -> str:
        name = f"{self._vector_store_prefix}-{_slugify(config.name)}"
        logger.info("Creating vector store %s", name)
        vector_store = self._client.beta.vector_stores.create(name=name)
        return vector_store.id

    def attach_files_to_vector_store(self, vector_store_id: str, file_ids: Iterable[str]) -> None:
        ids = list(file_ids)
        if not ids:
            return
        logger.info("Attaching %d file(s) to vector store %s", len(ids), vector_store_id)
        self._client.beta.vector_stores.file_batches.upload_and_poll(vector_store_id=vector_store_id, file_ids=ids)

    def create_assistant(self, config: AgentConfig, vector_store_id: str) -> str:
        logger.info("Creating assistant %s", config.name)
        assistant = self._client.beta.assistants.create(
            name=config.name,
            instructions=config.instructions,
            model=self._deployment,
            tools=[{"type": "file_search"}],
            tool_resources={"file_search": {"vector_store_ids": [vector_store_id]}},
        )
        return assistant.id

    def ensure_framework_agent(self, config: AgentConfig) -> str | None:
        if self._framework_client is None:
            logger.info("Microsoft Agent Framework not available; skipping framework agent creation")
            return None
        logger.info("Provisioning Agent Framework agent for %s", config.name)
        agent = self._framework_client.create_agent(name=config.name, instructions=config.instructions)
        return getattr(agent, "id", None)

    def provision(self, config: AgentConfig, files: Iterable[RetrievedFile]) -> ProvisionedResources:
        file_ids = self.upload_files(files)
        vector_store_id = self.create_vector_store(config)
        self.attach_files_to_vector_store(vector_store_id, file_ids)
        assistant_id = self.create_assistant(config, vector_store_id)
        framework_agent_id = self.ensure_framework_agent(config)
        return ProvisionedResources(
            assistant_id=assistant_id,
            vector_store_id=vector_store_id,
            file_ids=file_ids,
            framework_agent_id=framework_agent_id,
        )


def _slugify(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "assistant"


__all__ = [
    "AzureAssistantsService",
    "AzureConfigurationError",
    "ProvisionedResources",
]
