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

Volumes can be created up front and mounted into sandboxes at launch, and their
contents browsed and read straight from the volume handle:

```python
volume = porter.volumes.create(name="my-data")

sb = porter.sandboxes.create(
    image="python:3.11-alpine",
    volume_mounts={"/mnt/my-data": volume.id},
)

for file in volume.listdir("/checkpoints"):
    print(file.path, file.size_bytes)

config = volume.read_text("/checkpoints/config.json")

with open("model.safetensors", "wb") as out:
    for chunk in volume.stream("/checkpoints/model.safetensors"):
        out.write(chunk)
```

Inside a sandbox-enabled Porter cluster, the SDK connects to the in-cluster
sandbox API at `http://sandbox-api.porter-sandbox-system.svc.cluster.local:8080`
automatically, with no configuration needed.

From outside the cluster, set a Porter API token (created from
**Settings > API tokens** in the Porter Dashboard) and the cluster where
sandboxes are enabled:

```bash
export PORTER_SANDBOX_API_KEY=<porter-api-token>
export PORTER_CLUSTER_ID=<cluster-id>
```

The SDK reads the project from the token and calls the sandbox API through the
Porter API at `dashboard.porter.run`. To target a specific URL instead, set
`PORTER_SANDBOX_BASE_URL` or pass `base_url` - both take precedence over
everything above.

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

Everything under `porter_sandbox/` is generated from the Porter Sandbox OpenAPI
spec. Do not edit it by hand - changes there are overwritten on the next release.

- `porter_sandbox/sandbox.py`, `porter_sandbox/volume.py` - sync and async `Sandbox` and `Volume` handles
- `porter_sandbox/porter.py` and resource namespace modules like `porter_sandbox/sandboxes.py` - public client and namespaces
- `porter_sandbox/_client.py`, `_models.py`, `enums.py`, `_errors.py`, `resources/` - low-level client, models, and errors
- `porter_sandbox/_base_client.py`, `_async_base_client.py`, `_config.py`, `_retries.py` - sync and async HTTP transports, env-var resolution, retry/backoff

## Development

```bash
pip install -e ".[dev]"
pytest
ruff check .
mypy
```
