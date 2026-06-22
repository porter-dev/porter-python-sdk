from __future__ import annotations

import asyncio
import random
import time

DEFAULT_MAX_RETRIES = 3
INITIAL_BACKOFF_SECONDS = 0.5
MAX_BACKOFF_SECONDS = 8.0


def should_retry(status_code: int) -> bool:
    return status_code == 429 or 500 <= status_code < 600


def backoff_delay(attempt: int) -> float:
    """Exponential backoff with full jitter. `attempt` is 0-indexed."""
    capped = min(INITIAL_BACKOFF_SECONDS * (2 ** attempt), MAX_BACKOFF_SECONDS)
    return random.uniform(0, capped)


def sleep_for_attempt_sync(attempt: int) -> None:
    time.sleep(backoff_delay(attempt))


async def sleep_for_attempt(attempt: int) -> None:
    await asyncio.sleep(backoff_delay(attempt))
