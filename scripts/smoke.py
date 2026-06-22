"""End-to-end smoke test against a real sandbox-api.

Reads PORTER_SANDBOX_BASE_URL and PORTER_SANDBOX_API_KEY from env. Exercises
the public Porter client surface against the live API. Intended for in-cluster
execution, where TLS/auth/header issues that kubectl port-forward exhibits
don't apply.

Defaults to the sync Porter client. Pass --async to exercise AsyncPorter instead.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
import time

from porter_sandbox import AsyncPorter, Porter, SandboxError


def run_sync() -> int:
    base = os.environ.get("PORTER_SANDBOX_BASE_URL", "")
    print(f"target: {base or '(default)'} (sync)")
    porter = Porter()
    failures = 0

    try:
        print("\n[1/6] list (initial)")
        existing = porter.sandboxes.list()
        print(f"  ok, {len(existing)} sandbox(es) present")

        print("\n[2/6] create")
        sb = porter.sandboxes.create(
            image="python:3.11-alpine",
            command=["python", "-c", "print('hello from sandbox')"],
            tags={"created_by": "sdk-smoke", "ts": str(int(time.time()))},
        )
        print(f"  ok, id={sb.id}")

        print("\n[3/6] refresh (poll until phase != queued)")
        for attempt in range(15):
            sb.refresh()
            print(f"  attempt {attempt + 1}: phase={sb.phase}")
            if sb.phase and sb.phase.value not in ("queued", "creating"):
                break
            time.sleep(1)

        print("\n[4/6] logs")
        try:
            logs = sb.logs(limit=20)
            print(f"  ok, {len(logs)} line(s)")
            for line in logs[:5]:
                print(f"    | {line}")
        except SandboxError as e:
            print(f"  FAIL: {type(e).__name__}: {e.message} status={e.status_code}")
            failures += 1

        print("\n[5/6] list (filtered by tag)")
        filtered = porter.sandboxes.list(tags={"created_by": "sdk-smoke"})
        found = any(s.id == sb.id for s in filtered)
        if found:
            print(f"  ok, our sandbox is present in {len(filtered)} matching result(s)")
        else:
            print(f"  FAIL: our sandbox {sb.id} not in {len(filtered)} tag-filtered results")
            failures += 1

        print("\n[6/6] terminate")
        sb.terminate()
        print("  ok")

    except SandboxError as e:
        print(f"\n!! TOP-LEVEL FAILURE: {type(e).__name__}: {e.message} status={e.status_code} body={e.body}")
        failures += 1
    finally:
        porter.close()

    print(f"\nfinished, {failures} failure(s)")
    return 1 if failures else 0


async def run_async() -> int:
    base = os.environ.get("PORTER_SANDBOX_BASE_URL", "")
    print(f"target: {base or '(default)'} (async)")
    failures = 0

    try:
        print("\n[1/3] create x3 concurrently")
        async with AsyncPorter() as porter:
            sandboxes = await asyncio.gather(
                porter.sandboxes.create(image="python:3.11-alpine", command=["python", "-c", "print(1)"], tags={"created_by": "sdk-smoke-async"}),
                porter.sandboxes.create(image="python:3.11-alpine", command=["python", "-c", "print(2)"], tags={"created_by": "sdk-smoke-async"}),
                porter.sandboxes.create(image="python:3.11-alpine", command=["python", "-c", "print(3)"], tags={"created_by": "sdk-smoke-async"}),
            )
            for sb in sandboxes:
                print(f"  ok, id={sb.id}")

            print("\n[2/3] refresh all concurrently")
            await asyncio.gather(*[sb.refresh() for sb in sandboxes])
            for sb in sandboxes:
                print(f"  {sb.id}: phase={sb.phase}")

            print("\n[3/3] terminate all concurrently")
            await asyncio.gather(*[sb.terminate() for sb in sandboxes])
            print("  ok")

    except SandboxError as e:
        print(f"\n!! TOP-LEVEL FAILURE: {type(e).__name__}: {e.message} status={e.status_code} body={e.body}")
        failures += 1

    print(f"\nfinished, {failures} failure(s)")
    return 1 if failures else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--async", dest="use_async", action="store_true", help="exercise AsyncSandbox instead of Sandbox")
    args = parser.parse_args()

    if args.use_async:
        return asyncio.run(run_async())
    return run_sync()


if __name__ == "__main__":
    sys.exit(main())
