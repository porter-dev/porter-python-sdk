from __future__ import annotations

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

    project_id = os.environ.get("PORTER_PROJECT_ID")
    cluster_id = os.environ.get("PORTER_CLUSTER_ID")
    if project_id and cluster_id:
        if not api_key:
            raise ValueError(
                "PORTER_PROJECT_ID and PORTER_CLUSTER_ID are set, so the SDK will call the "
                "Porter API from outside the cluster, which requires an API token. Set "
                "PORTER_SANDBOX_API_KEY or pass api_key. You can create an API token from "
                "Settings > API tokens in the Porter Dashboard (requires admin permissions)."
            )
        return EXTERNAL_BASE_URL_FORMAT.format(project_id=project_id, cluster_id=cluster_id)
    if project_id or cluster_id:
        set_var, missing_var = (
            ("PORTER_PROJECT_ID", "PORTER_CLUSTER_ID")
            if project_id
            else ("PORTER_CLUSTER_ID", "PORTER_PROJECT_ID")
        )
        raise ValueError(
            f"{set_var} is set but {missing_var} is not. Set both to call the Porter API "
            "from outside the cluster."
        )

    # Kubernetes sets KUBERNETES_SERVICE_HOST in every pod, so its presence means the
    # in-cluster sandbox API service address is at least reachable in principle.
    if os.environ.get("KUBERNETES_SERVICE_HOST"):
        return IN_CLUSTER_BASE_URL

    raise ValueError(
        "Could not determine the sandbox API base URL. Either run inside a sandbox-enabled "
        "Porter cluster, or set PORTER_PROJECT_ID and PORTER_CLUSTER_ID (plus "
        "PORTER_SANDBOX_API_KEY) to call the Porter API from outside the cluster. You can "
        "also set PORTER_SANDBOX_BASE_URL or pass base_url to target a specific URL."
    )
