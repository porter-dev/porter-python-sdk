# porter-sandbox

Python SDK for the [Porter Sandbox API](https://porter.run).

> **Pre-release.** Pilot for Porter's multi-language SDK rollout.

## Install

```bash
pip install porter-sandbox
```

## Usage

```python
from porter_sandbox import Porter

with Porter() as porter:
    sb = porter.sandboxes.create(
        image="python:3.11-alpine",
        command=["python", "-c", "print('hi')"],
    )
    print(sb.logs())
    sb.terminate()
```

Set `PORTER_SANDBOX_API_KEY` in your environment.
By default, the SDK connects to Porter's in-cluster sandbox API at
`http://sandbox-api.porter-sandbox-system.svc.cluster.local:8080`. Override it
with `PORTER_SANDBOX_BASE_URL` or by passing `base_url`.

### Async

For async code (FastAPI handlers, concurrent sandbox fan-out, etc.) use `AsyncPorter` — same surface, awaitable methods:

```python
import asyncio
from porter_sandbox import AsyncPorter

async def main():
    async with AsyncPorter() as porter:
        sb = await porter.sandboxes.create(image="python:3.11-alpine", command=["python", "-c", "print('hi')"])
        print(await sb.logs())
        await sb.terminate()

asyncio.run(main())
```

Async is also the right choice when launching many sandboxes in parallel:

```python
async with AsyncPorter() as porter:
    results = await asyncio.gather(*[
        porter.sandboxes.create(image="python:3.11", command=cmd) for cmd in commands
    ])
```

## Layout

- `porter_sandbox/porter.py`, resource namespace modules like `porter_sandbox/sandboxes.py`, `porter_sandbox/_client.py`, `_models.py`, `enums.py`, `_errors.py`, `resources/` — generated from the [sandbox-api OpenAPI spec](https://github.com/porter-dev/workstation/tree/main/code/sandbox/schemas) via the [sdk-gen workspace](https://github.com/porter-dev/workstation/tree/main/code/sandbox/sdk-gen). Do not edit by hand.
- `porter_sandbox/sandbox.py` — hand-written rich sandbox handle used by the generated `sandboxes` namespace
- `porter_sandbox/_base_client.py` / `_async_base_client.py` — hand-written sync and async HTTP transports
- `porter_sandbox/_config.py`, `_retries.py` — hand-written runtime (env-var resolution, retry/backoff)

## Development

```bash
pip install -e ".[dev]"
pytest
ruff check .
mypy
```

To pull in a fresh generation from the sdk-gen workspace:

```bash
./scripts/sync-generated.sh /path/to/workstation/code/sandbox/sdk-gen/out/python
```
