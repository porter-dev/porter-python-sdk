from __future__ import annotations

import builtins

from porter_sandbox._models import ExecRequest, ExecResponse, LogLine, StatusResponse
from porter_sandbox.enums import StatusResponsePhase
from porter_sandbox.resources.sandboxes import AsyncSandboxes as AsyncSandboxesResource
from porter_sandbox.resources.sandboxes import Sandboxes as SandboxesResource


class Sandbox:
    """Ergonomic handle for a single sandbox (sync).

    Constructed by `Porter().sandboxes`. Holds a back-reference to the generated
    sandbox resource so lifecycle methods do not need a client to be re-passed.

    For async usage, see `AsyncSandbox` (same surface, async methods).
    """

    def __init__(
        self,
        *,
        id: str,
        resource: SandboxesResource,
        status: StatusResponse | None = None,
    ) -> None:
        self.id = id
        self._sandboxes = resource
        self._status = status

    @property
    def phase(self) -> StatusResponsePhase | None:
        return self._status.phase if self._status else None

    @property
    def tags(self) -> dict[str, str] | None:
        return self._status.tags if self._status else None

    def refresh(self) -> StatusResponse:
        """Refetch and cache the sandbox status."""
        self._status = self._sandboxes.get_sandbox(id=self.id)
        return self._status

    def terminate(self) -> None:
        """Terminate the sandbox and clean up its resources."""
        self._sandboxes.delete_sandbox(id=self.id)

    def logs(self, *, since: str | None = None, limit: int | None = None) -> builtins.list[LogLine]:
        """Fetch log lines from the sandbox. Logs persist after termination."""
        response = self._sandboxes.get_sandbox_logs(id=self.id, since=since, limit=limit)
        return response.logs

    def exec(self, command: list[str]) -> ExecResponse:
        """Run a command inside the sandbox and return stdout/stderr/exit code."""
        return self._sandboxes.exec_sandbox(id=self.id, body=ExecRequest(command=command))


class AsyncSandbox:
    """Ergonomic handle for a single sandbox (async).

    Same surface as `Sandbox`, but every method is an awaitable.
    """

    def __init__(
        self,
        *,
        id: str,
        resource: AsyncSandboxesResource,
        status: StatusResponse | None = None,
    ) -> None:
        self.id = id
        self._sandboxes = resource
        self._status = status

    @property
    def phase(self) -> StatusResponsePhase | None:
        return self._status.phase if self._status else None

    @property
    def tags(self) -> dict[str, str] | None:
        return self._status.tags if self._status else None

    async def refresh(self) -> StatusResponse:
        """Refetch and cache the sandbox status."""
        self._status = await self._sandboxes.get_sandbox(id=self.id)
        return self._status

    async def terminate(self) -> None:
        """Terminate the sandbox and clean up its resources."""
        await self._sandboxes.delete_sandbox(id=self.id)

    async def logs(self, *, since: str | None = None, limit: int | None = None) -> builtins.list[LogLine]:
        """Fetch log lines from the sandbox. Logs persist after termination."""
        response = await self._sandboxes.get_sandbox_logs(id=self.id, since=since, limit=limit)
        return response.logs

    async def exec(self, command: list[str]) -> ExecResponse:
        """Run a command inside the sandbox and return stdout/stderr/exit code."""
        return await self._sandboxes.exec_sandbox(id=self.id, body=ExecRequest(command=command))
