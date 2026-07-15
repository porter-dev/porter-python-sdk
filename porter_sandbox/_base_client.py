from __future__ import annotations

import json as json_lib
from collections.abc import Mapping
from typing import Any

import httpx
from httpx._client import UseClientDefault

from ._config import Config
from ._errors import SandboxError, SandboxTimeoutError, error_for_status
from ._retries import DEFAULT_MAX_RETRIES, should_retry, sleep_for_attempt_sync

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


class _BaseClient:
    """Sync HTTP transport shared by all generated sync resource classes.

    Owns the httpx.Client, header injection, retry loop, and error mapping.
    Resource methods call `self._client._request(...)`.
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
        self._http = httpx.Client(
            base_url=config.base_url,
            timeout=config.timeout,
            verify=verify,
            headers=headers,
        )

    def __enter__(self) -> _BaseClient:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def close(self) -> None:
        self._http.close()

    def _request(
        self,
        *,
        method: str,
        path: str,
        params: Mapping[str, Any] | None = None,
        json: Any = None,
        timeout: float | None | UseClientDefault = httpx.USE_CLIENT_DEFAULT,
        retry: bool = True,
    ) -> Any:
        # `timeout=None` disables the timeout entirely, used for long-running
        # calls like exec, where the API works for the full duration of the
        # request. `retry=False` is for calls that must not be re-sent (exec):
        # a failed attempt may have executed server-side, so retrying could
        # run the command again.
        max_retries = self._max_retries if retry else 0
        last_error: Exception | None = None

        for attempt in range(max_retries + 1):
            try:
                response = self._http.request(
                    method=method,
                    url=path,
                    params=params,
                    json=json,
                    timeout=timeout,
                )
            except httpx.TimeoutException as exc:
                # A timed-out request may have executed server-side, so
                # retrying could run it again. Surface the timeout instead.
                effective = self._config.timeout if timeout is httpx.USE_CLIENT_DEFAULT else timeout
                raise SandboxTimeoutError(f"Request timed out after {effective}s") from exc
            except httpx.HTTPError as exc:
                last_error = exc
                if attempt < max_retries:
                    sleep_for_attempt_sync(attempt)
                    continue
                raise SandboxError(f"Network error: {exc}") from exc

            if 200 <= response.status_code < 300:
                return _decode_body(response)

            if should_retry(response.status_code) and attempt < max_retries:
                sleep_for_attempt_sync(attempt)
                continue

            body = _decode_body(response)
            raise error_for_status(
                response.status_code,
                body,
                _error_message(body, response.status_code),
            )

        # Unreachable: loop either returns or raises on every path.
        raise SandboxError(f"Request failed after retries: {last_error}")
