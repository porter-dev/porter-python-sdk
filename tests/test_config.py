from __future__ import annotations

from pytest import MonkeyPatch

from porter_sandbox._config import Config

DEFAULT_BASE_URL = "http://sandbox-api.porter-sandbox-system.svc.cluster.local:8080"


def test_config_falls_back_to_in_cluster_sandbox_api_url(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.delenv("PORTER_SANDBOX_BASE_URL", raising=False)

    assert Config.resolve().base_url == DEFAULT_BASE_URL


def test_config_uses_environment_base_url_when_no_base_url_is_passed(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("PORTER_SANDBOX_BASE_URL", "https://sandbox.example/")

    assert Config.resolve().base_url == "https://sandbox.example"


def test_config_prefers_explicit_base_url_over_environment(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("PORTER_SANDBOX_BASE_URL", "https://sandbox.example")

    assert Config.resolve(base_url="https://sandbox.override/").base_url == "https://sandbox.override"
