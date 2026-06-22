from __future__ import annotations

import os
from dataclasses import dataclass

DEFAULT_BASE_URL = "http://sandbox-api.porter-sandbox-system.svc.cluster.local:8080"
DEFAULT_TIMEOUT_SECONDS = 30.0


@dataclass(frozen=True)
class Config:
    api_key: str | None
    base_url: str
    timeout: float

    @classmethod
    def resolve(
        cls,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: float | None = None,
    ) -> Config:
        return cls(
            api_key=api_key or os.environ.get("PORTER_SANDBOX_API_KEY") or None,
            base_url=(base_url or os.environ.get("PORTER_SANDBOX_BASE_URL") or DEFAULT_BASE_URL).rstrip("/"),
            timeout=timeout if timeout is not None else DEFAULT_TIMEOUT_SECONDS,
        )
