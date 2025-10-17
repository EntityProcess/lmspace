from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RetrievedFile:
    url: str
    filename: str
    content_type: str | None
    data: bytes


class ContentFetcher:
    def __init__(self, *, github_token: str | None = None, timeout: float = 30.0, client: httpx.Client | None = None) -> None:
        headers = {"User-Agent": "lmspace-mvp/0.1"}
        if client is None:
            client = httpx.Client(timeout=timeout, follow_redirects=True, headers=headers)
        else:
            for key, value in headers.items():
                client.headers.setdefault(key, value)
        self._client = client
        self._github_token = github_token

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "ContentFetcher":
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def fetch_many(self, urls: Iterable[str]) -> list[RetrievedFile]:
        results: list[RetrievedFile] = []
        seen: set[str] = set()
        for index, url in enumerate(urls, start=1):
            results.append(self._fetch_single(url, index, seen))
        return results

    def _fetch_single(self, url: str, index: int, seen: set[str]) -> RetrievedFile:
        request_headers = {}
        parsed = urlparse(url)
        hostname = parsed.hostname or ""
        if self._github_token and ("github.com" in hostname or "githubusercontent.com" in hostname):
            request_headers["Authorization"] = f"token {self._github_token}"

        logger.info("Downloading %s", url)
        response = self._client.get(url, headers=request_headers)
        response.raise_for_status()

        filename = self._derive_filename(url, response, index, seen)
        content_type = response.headers.get("Content-Type")
        data = response.content
        logger.debug("Fetched %s -> %s (%s bytes)", url, filename, len(data))
        return RetrievedFile(url=url, filename=filename, content_type=content_type, data=data)

    @staticmethod
    def _derive_filename(url: str, response: httpx.Response, index: int, seen: set[str]) -> str:
        from email.message import Message

        disposition = response.headers.get("Content-Disposition")
        name = None
        if disposition:
            message = Message()
            message["Content-Disposition"] = disposition
            params = dict(message.get_params())
            name = params.get("filename")

        if not name:
            path_name = Path(urlparse(url).path).name
            name = path_name or f"download-{index}"

        candidate = name
        counter = 1
        while candidate in seen:
            candidate = f"{Path(name).stem}-{counter}{Path(name).suffix}"
            counter += 1
        seen.add(candidate)
        return candidate


__all__ = ["ContentFetcher", "RetrievedFile"]
