from __future__ import annotations

import respx

from porter_sandbox import AsyncPorter, Porter, Volumes


def test_porter_sandboxes_create_returns_handle() -> None:
    with respx.mock(base_url="https://sandbox.example") as mock:
        mock.post("/v1/sandbox/run").respond(202, json={"id": "sb_123", "name": "sb_123"})

        porter = Porter(api_key="test", base_url="https://sandbox.example")
        try:
            assert isinstance(porter.volumes, Volumes)
            sandbox = porter.sandboxes.create(image="python:3.11-alpine")
            assert sandbox.id == "sb_123"
            assert sandbox.phase is None
            assert sandbox.tags is None
        finally:
            porter.close()


async def test_async_porter_exposes_sandboxes_namespace() -> None:
    async with AsyncPorter(api_key="test", base_url="https://sandbox.example") as porter:
        assert porter.sandboxes.raw is not None
        assert porter.volumes.raw is not None
