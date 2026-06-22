from __future__ import annotations

import json as json_lib
from collections.abc import Mapping
from typing import Any

import httpx

from ._config import Config
from ._errors import SandboxError, error_for_status
from ._retries import DEFAULT_MAX_RETRIES, should_retry, sleep_for_attempt

USER_AGENT = "porter-sandbox-python/0.0.1"


def _decode_body(response: httpx.Response) -> Any:
    if response.status_code == 204 or not response.content:
        return None
    content_type = response.headers.get("content-type", "")
    if "application/json" in content_type:
        try:
            return response.json()
        except json_lib.JSONDecodeError:
            return response.text
    return response.text


def _error_message(body: Any, status_code: int) -> str:
    if isinstance(body, dict):
        error = body.get("error")
        if isinstance(error, str):
            return error
    return f"HTTP {status_code}"


class _AsyncBaseClient:
    """Async HTTP transport shared by all generated async resource classes.

    Owns the httpx.AsyncClient, header injection, retry loop, and error mapping.
    Resource methods call `await self._client._request(...)`.
    """

    def __init__(
        self,
        *,
        config: Config,
        max_retries: int = DEFAULT_MAX_RETRIES,
        verify: bool | str = True,
    ) -> None:
        self._config = config
        self._max_retries = max_retries
        headers = {"User-Agent": USER_AGENT}
        if config.api_key:
            headers["Authorization"] = f"Bearer {config.api_key}"
        self._http = httpx.AsyncClient(
            base_url=config.base_url,
            timeout=config.timeout,
            verify=verify,
            headers=headers,
        )

    async def __aenter__(self) -> _AsyncBaseClient:
        return self

    async def __aexit__(self, *_exc: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._http.aclose()

    async def _request(
        self,
        *,
        method: str,
        path: str,
        params: Mapping[str, Any] | None = None,
        json: Any = None,
    ) -> Any:
        last_error: Exception | None = None

        for attempt in range(self._max_retries + 1):
            try:
                response = await self._http.request(
                    method=method,
                    url=path,
                    params=params,
                    json=json,
                )
            except httpx.HTTPError as exc:
                last_error = exc
                if attempt < self._max_retries:
                    await sleep_for_attempt(attempt)
                    continue
                raise SandboxError(f"Network error: {exc}") from exc

            if 200 <= response.status_code < 300:
                return _decode_body(response)

            if should_retry(response.status_code) and attempt < self._max_retries:
                await sleep_for_attempt(attempt)
                continue

            body = _decode_body(response)
            raise error_for_status(
                response.status_code,
                body,
                _error_message(body, response.status_code),
            )

        # Unreachable: loop either returns or raises on every path.
        raise SandboxError(f"Request failed after retries: {last_error}")
