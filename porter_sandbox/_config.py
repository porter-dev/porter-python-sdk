from __future__ import annotations

import base64
import binascii
import json
import os
from dataclasses import dataclass

IN_CLUSTER_BASE_URL = "http://sandbox-api.porter-sandbox-system.svc.cluster.local:8080"
EXTERNAL_BASE_URL_FORMAT = (
    "https://dashboard.porter.run/api/v2/alpha/projects/{project_id}/clusters/{cluster_id}"
)
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
        resolved_api_key = api_key or os.environ.get("PORTER_SANDBOX_API_KEY") or None
        return cls(
            api_key=resolved_api_key,
            base_url=_resolve_base_url(base_url, resolved_api_key).rstrip("/"),
            timeout=timeout if timeout is not None else DEFAULT_TIMEOUT_SECONDS,
        )


def _resolve_base_url(base_url: str | None, api_key: str | None) -> str:
    explicit = base_url or os.environ.get("PORTER_SANDBOX_BASE_URL")
    if explicit:
        return explicit

    cluster_id = os.environ.get("PORTER_CLUSTER_ID")
    if cluster_id:
        if not api_key:
            raise ValueError(
                "PORTER_CLUSTER_ID is set, so the SDK will call the Porter API from outside "
                "the cluster, which requires an API token. Set PORTER_SANDBOX_API_KEY or pass "
                "api_key. You can create an API token from Settings > API tokens in the Porter "
                "Dashboard (requires admin permissions)."
            )
        return EXTERNAL_BASE_URL_FORMAT.format(
            project_id=_project_id_from_api_key(api_key), cluster_id=cluster_id
        )

    # Kubernetes sets KUBERNETES_SERVICE_HOST in every pod, so its presence means the
    # in-cluster sandbox API service address is at least reachable in principle.
    if os.environ.get("KUBERNETES_SERVICE_HOST"):
        return IN_CLUSTER_BASE_URL

    if api_key:
        raise ValueError(
            "An API key is set but PORTER_CLUSTER_ID is not. Set PORTER_CLUSTER_ID to the "
            "cluster where sandboxes are enabled so the SDK can call the Porter API from "
            "outside the cluster."
        )

    raise ValueError(
        "Could not determine the sandbox API base URL. Either run inside a sandbox-enabled "
        "Porter cluster, or set PORTER_CLUSTER_ID and PORTER_SANDBOX_API_KEY to call the "
        "Porter API from outside the cluster. You can also set PORTER_SANDBOX_BASE_URL or "
        "pass base_url to target a specific URL."
    )


def _project_id_from_api_key(api_key: str) -> int:
    """Read the project_id claim from a Porter API token without verifying the signature.

    Signature verification is the server's job; the SDK only needs the claim to build
    the URL, and a tampered claim just produces a URL the server will reject.
    """
    error = ValueError(
        "PORTER_SANDBOX_API_KEY does not look like a Porter API token (expected a JWT with "
        "a project_id claim). Create one from Settings > API tokens in the Porter Dashboard."
    )

    segments = api_key.split(".")
    if len(segments) != 3:
        raise error
    payload_segment = segments[1]
    try:
        payload = json.loads(
            base64.urlsafe_b64decode(payload_segment + "=" * (-len(payload_segment) % 4))
        )
    except (binascii.Error, ValueError, UnicodeDecodeError):
        raise error from None

    project_id = payload.get("project_id") if isinstance(payload, dict) else None
    if not isinstance(project_id, int) or isinstance(project_id, bool) or project_id <= 0:
        raise error
    return project_id
