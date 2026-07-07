from __future__ import annotations

import pytest
from pytest import MonkeyPatch

from porter_sandbox._config import Config

IN_CLUSTER_BASE_URL = "http://sandbox-api.porter-sandbox-system.svc.cluster.local:8080"

RESOLUTION_ENV_VARS = (
    "PORTER_SANDBOX_BASE_URL",
    "PORTER_SANDBOX_API_KEY",
    "PORTER_PROJECT_ID",
    "PORTER_CLUSTER_ID",
    "KUBERNETES_SERVICE_HOST",
)


@pytest.fixture(autouse=True)
def clean_env(monkeypatch: MonkeyPatch) -> None:
    for var in RESOLUTION_ENV_VARS:
        monkeypatch.delenv(var, raising=False)


def test_config_falls_back_to_in_cluster_sandbox_api_url(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("KUBERNETES_SERVICE_HOST", "10.0.0.1")

    assert Config.resolve().base_url == IN_CLUSTER_BASE_URL


def test_config_uses_environment_base_url_when_no_base_url_is_passed(
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setenv("PORTER_SANDBOX_BASE_URL", "https://sandbox.example/")

    assert Config.resolve().base_url == "https://sandbox.example"


def test_config_prefers_explicit_base_url_over_environment(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("PORTER_SANDBOX_BASE_URL", "https://sandbox.example")

    assert (
        Config.resolve(base_url="https://sandbox.override/").base_url == "https://sandbox.override"
    )


def test_config_builds_external_url_from_project_and_cluster_ids(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("PORTER_PROJECT_ID", "123")
    monkeypatch.setenv("PORTER_CLUSTER_ID", "456")
    monkeypatch.setenv("PORTER_SANDBOX_API_KEY", "token")

    assert (
        Config.resolve().base_url
        == "https://dashboard.porter.run/api/v2/alpha/projects/123/clusters/456"
    )


def test_config_prefers_project_and_cluster_ids_over_in_cluster_detection(
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setenv("PORTER_PROJECT_ID", "123")
    monkeypatch.setenv("PORTER_CLUSTER_ID", "456")
    monkeypatch.setenv("PORTER_SANDBOX_API_KEY", "token")
    monkeypatch.setenv("KUBERNETES_SERVICE_HOST", "10.0.0.1")

    assert (
        Config.resolve().base_url
        == "https://dashboard.porter.run/api/v2/alpha/projects/123/clusters/456"
    )


def test_config_prefers_environment_base_url_over_project_and_cluster_ids(
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setenv("PORTER_PROJECT_ID", "123")
    monkeypatch.setenv("PORTER_CLUSTER_ID", "456")
    monkeypatch.setenv("PORTER_SANDBOX_BASE_URL", "https://sandbox.example")

    assert Config.resolve().base_url == "https://sandbox.example"


def test_config_requires_api_key_for_external_url(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("PORTER_PROJECT_ID", "123")
    monkeypatch.setenv("PORTER_CLUSTER_ID", "456")

    with pytest.raises(ValueError, match="PORTER_SANDBOX_API_KEY"):
        Config.resolve()


def test_config_accepts_api_key_argument_for_external_url(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("PORTER_PROJECT_ID", "123")
    monkeypatch.setenv("PORTER_CLUSTER_ID", "456")

    config = Config.resolve(api_key="token")

    assert config.base_url == "https://dashboard.porter.run/api/v2/alpha/projects/123/clusters/456"


def test_config_rejects_project_id_without_cluster_id(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("PORTER_PROJECT_ID", "123")

    with pytest.raises(ValueError, match="PORTER_CLUSTER_ID is not"):
        Config.resolve()


def test_config_rejects_cluster_id_without_project_id(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("PORTER_CLUSTER_ID", "456")

    with pytest.raises(ValueError, match="PORTER_PROJECT_ID is not"):
        Config.resolve()


def test_config_raises_when_base_url_cannot_be_determined() -> None:
    with pytest.raises(ValueError, match="Could not determine the sandbox API base URL"):
        Config.resolve()
