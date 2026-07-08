from __future__ import annotations

import base64
import json

import pytest
from pytest import MonkeyPatch

from porter_sandbox._config import Config

IN_CLUSTER_BASE_URL = "http://sandbox-api.porter-sandbox-system.svc.cluster.local:8080"

RESOLUTION_ENV_VARS = (
    "PORTER_SANDBOX_BASE_URL",
    "PORTER_SANDBOX_API_KEY",
    "PORTER_CLUSTER_ID",
    "KUBERNETES_SERVICE_HOST",
)


def make_api_key(payload: object) -> str:
    encoded = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    return f"header.{encoded}.signature"


API_KEY = make_api_key({"project_id": 123, "sub": "api", "token_id": "abc"})


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


def test_config_parses_project_id_from_porter_minted_token(monkeypatch: MonkeyPatch) -> None:
    # Exact claim shape minted by the monolith's JWTForAPI: iat is a string,
    # project_id is a number, sub/sub_kind/token_id are always present.
    porter_token = make_api_key(
        {
            "iat": "1783537707",
            "project_id": 1,
            "sub": "api",
            "sub_kind": "api",
            "token_id": "7dc2a111-f851-4935-a414-b72945be0883",
        }
    )
    monkeypatch.setenv("PORTER_CLUSTER_ID", "651")
    monkeypatch.setenv("PORTER_SANDBOX_API_KEY", porter_token)

    assert (
        Config.resolve().base_url
        == "https://dashboard.porter.run/api/v2/alpha/projects/1/clusters/651"
    )


def test_config_builds_external_url_from_api_key_and_cluster_id(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("PORTER_CLUSTER_ID", "456")
    monkeypatch.setenv("PORTER_SANDBOX_API_KEY", API_KEY)

    assert (
        Config.resolve().base_url
        == "https://dashboard.porter.run/api/v2/alpha/projects/123/clusters/456"
    )


def test_config_prefers_cluster_id_over_in_cluster_detection(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("PORTER_CLUSTER_ID", "456")
    monkeypatch.setenv("PORTER_SANDBOX_API_KEY", API_KEY)
    monkeypatch.setenv("KUBERNETES_SERVICE_HOST", "10.0.0.1")

    assert (
        Config.resolve().base_url
        == "https://dashboard.porter.run/api/v2/alpha/projects/123/clusters/456"
    )


def test_config_prefers_environment_base_url_over_cluster_id(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("PORTER_CLUSTER_ID", "456")
    monkeypatch.setenv("PORTER_SANDBOX_BASE_URL", "https://sandbox.example")

    assert Config.resolve().base_url == "https://sandbox.example"


def test_config_requires_api_key_for_external_url(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("PORTER_CLUSTER_ID", "456")

    with pytest.raises(ValueError, match="PORTER_SANDBOX_API_KEY"):
        Config.resolve()


def test_config_accepts_api_key_argument_for_external_url(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("PORTER_CLUSTER_ID", "456")

    assert (
        Config.resolve(api_key=API_KEY).base_url
        == "https://dashboard.porter.run/api/v2/alpha/projects/123/clusters/456"
    )


@pytest.mark.parametrize(
    "api_key",
    [
        "not-a-jwt",
        "one.two",
        make_api_key({"sub": "api"}),
        make_api_key({"project_id": "123"}),
        make_api_key({"project_id": 0}),
        make_api_key(["not", "a", "dict"]),
        "header.!!!not-base64!!!.signature",
    ],
)
def test_config_rejects_api_key_without_project_id_claim(
    monkeypatch: MonkeyPatch, api_key: str
) -> None:
    monkeypatch.setenv("PORTER_CLUSTER_ID", "456")
    monkeypatch.setenv("PORTER_SANDBOX_API_KEY", api_key)

    with pytest.raises(ValueError, match="project_id claim"):
        Config.resolve()


def test_config_requires_cluster_id_when_api_key_is_set(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("PORTER_SANDBOX_API_KEY", API_KEY)

    with pytest.raises(ValueError, match="PORTER_CLUSTER_ID is not"):
        Config.resolve()


def test_config_ignores_missing_cluster_id_in_cluster(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("PORTER_SANDBOX_API_KEY", API_KEY)
    monkeypatch.setenv("KUBERNETES_SERVICE_HOST", "10.0.0.1")

    assert Config.resolve().base_url == IN_CLUSTER_BASE_URL


def test_config_errors_when_no_resolution_path_is_available() -> None:
    with pytest.raises(ValueError, match="Could not determine the sandbox API base URL"):
        Config.resolve()
