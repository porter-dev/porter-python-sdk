from __future__ import annotations

import httpx
import pytest
import respx

from porter_sandbox import Porter
from porter_sandbox._errors import SandboxError, SandboxTimeoutError
from porter_sandbox._models import ExecRequest


def test_exec_runs_without_client_timeout() -> None:
    with respx.mock(base_url="https://sandbox.example") as mock:
        mock.post("/v1/sandbox/run").respond(202, json={"id": "sb_123", "name": "sb_123"})
        exec_route = mock.post("/v1/sandbox/sb_123/exec").respond(
            200, json={"stdout": "hi", "stderr": "", "exit_code": 0}
        )

        porter = Porter(api_key="test", base_url="https://sandbox.example")
        try:
            sandbox = porter.sandboxes.create(image="python:3.11-alpine")
            response = sandbox.exec(["echo", "hi"])
            assert response.exit_code == 0

            request_timeout = exec_route.calls.last.request.extensions["timeout"]
            assert request_timeout["read"] is None
        finally:
            porter.close()


def test_exec_accepts_explicit_timeout_via_raw_resource() -> None:
    with respx.mock(base_url="https://sandbox.example") as mock:
        exec_route = mock.post("/v1/sandbox/sb_123/exec").respond(
            200, json={"stdout": "hi", "stderr": "", "exit_code": 0}
        )

        porter = Porter(api_key="test", base_url="https://sandbox.example")
        try:
            porter.sandboxes.raw.exec_sandbox(
                id="sb_123", body=ExecRequest(command=["echo", "hi"]), timeout=120
            )
            request_timeout = exec_route.calls.last.request.extensions["timeout"]
            assert request_timeout["read"] == 120
        finally:
            porter.close()


def test_timed_out_request_raises_without_retrying() -> None:
    with respx.mock(base_url="https://sandbox.example") as mock:
        route = mock.get("/v1/sandbox/sb_123")
        route.side_effect = httpx.ReadTimeout("timed out")

        porter = Porter(api_key="test", base_url="https://sandbox.example")
        try:
            with pytest.raises(SandboxTimeoutError):
                porter.sandboxes.raw.get_sandbox(id="sb_123")
            assert route.call_count == 1
        finally:
            porter.close()


def test_exec_network_error_is_not_retried() -> None:
    with respx.mock(base_url="https://sandbox.example") as mock:
        exec_route = mock.post("/v1/sandbox/sb_123/exec")
        exec_route.side_effect = httpx.ConnectError("connection reset")

        porter = Porter(api_key="test", base_url="https://sandbox.example")
        try:
            with pytest.raises(SandboxError):
                porter.sandboxes.raw.exec_sandbox(
                    id="sb_123", body=ExecRequest(command=["sleep", "60"])
                )
            assert exec_route.call_count == 1
        finally:
            porter.close()
