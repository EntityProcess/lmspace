import httpx
import pytest
import respx

from lmspace.fetcher import ContentFetcher


@respx.mock
def test_fetcher_downloads_and_names_files() -> None:
    url = "https://example.com/path/doc.txt"
    respx.get(url).respond(200, content=b"hello", headers={"Content-Type": "text/plain"})

    fetcher = ContentFetcher()
    try:
        files = fetcher.fetch_many([url])
    finally:
        fetcher.close()

    assert len(files) == 1
    file = files[0]
    assert file.url == url
    assert file.filename == "doc.txt"
    assert file.data == b"hello"


@respx.mock
def test_fetcher_uses_github_token_header() -> None:
    url = "https://raw.githubusercontent.com/owner/repo/main/file.txt"
    route = respx.get(url)
    route.respond(200, content=b"data")

    fetcher = ContentFetcher(github_token="secret-token")
    try:
        fetcher.fetch_many([url])
    finally:
        fetcher.close()

    sent_request = route.calls.last.request
    assert sent_request.headers["Authorization"] == "token secret-token"


@respx.mock
def test_fetcher_raises_for_http_error() -> None:
    url = "https://example.com/missing.txt"
    respx.get(url).respond(404)

    fetcher = ContentFetcher()
    try:
        with pytest.raises(httpx.HTTPStatusError):
            fetcher.fetch_many([url])
    finally:
        fetcher.close()
