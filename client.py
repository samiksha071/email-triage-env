"""
Python client for the Email Triage OpenEnv environment.

Usage (sync)
------------
    from client import EmailTriageEnv
    from models import EmailTriageAction

    with EmailTriageEnv(base_url="http://localhost:7860").sync() as env:
        result = env.reset(task_id="easy")
        obs = result.observation
        while not result.done if hasattr(result, 'done') else True:
            action = EmailTriageAction(
                category="urgent",
                priority="high",
                summary="...",
                suggested_action="Reply now",
            )
            result = env.step(action)
            if result.done:
                break

Usage (async)
-------------
    import asyncio
    from client import EmailTriageEnv

    async def main():
        async with EmailTriageEnv(base_url="http://localhost:7860") as env:
            result = await env.reset(task_id="medium")
            ...

    asyncio.run(main())
"""
import os
import asyncio
from contextlib import contextmanager, asynccontextmanager
from dataclasses import dataclass
from typing import Optional

import httpx

from models import EmailTriageAction, EmailObservation, EmailTriageState


BASE_URL = os.environ.get("ENV_BASE_URL", "http://localhost:7860")


@dataclass
class ResetResult:
    observation: EmailObservation
    info: dict


@dataclass
class StepResult:
    observation: EmailObservation
    reward: float
    done: bool
    info: dict


class _SyncEmailTriageEnv:
    """Synchronous wrapper around the async client."""

    def __init__(self, base_url: str):
        self._base_url = base_url.rstrip("/")
        self._client = httpx.Client(timeout=30)

    def reset(self, task_id: str = "easy") -> ResetResult:
        resp = self._client.post(f"{self._base_url}/reset", json={"task_id": task_id})
        resp.raise_for_status()
        data = resp.json()
        return ResetResult(
            observation=EmailObservation(**data["observation"]),
            info=data["info"],
        )

    def step(self, action: EmailTriageAction) -> StepResult:
        resp = self._client.post(f"{self._base_url}/step", json=action.model_dump())
        resp.raise_for_status()
        data = resp.json()
        return StepResult(
            observation=EmailObservation(**data["observation"]),
            reward=data["reward"],
            done=data["done"],
            info=data["info"],
        )

    def state(self) -> EmailTriageState:
        resp = self._client.get(f"{self._base_url}/state")
        resp.raise_for_status()
        return EmailTriageState(**resp.json())

    def close(self):
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class EmailTriageEnv:
    """Async Email Triage environment client."""

    def __init__(self, base_url: str = BASE_URL):
        self._base_url = base_url.rstrip("/")
        self._client: Optional[httpx.AsyncClient] = None

    def sync(self) -> "_SyncEmailTriageEnv":
        return _SyncEmailTriageEnv(self._base_url)

    async def __aenter__(self):
        self._client = httpx.AsyncClient(timeout=30)
        return self

    async def __aexit__(self, *args):
        if self._client:
            await self._client.aclose()

    async def reset(self, task_id: str = "easy") -> ResetResult:
        assert self._client, "Use as async context manager"
        resp = await self._client.post(
            f"{self._base_url}/reset", json={"task_id": task_id}
        )
        resp.raise_for_status()
        data = resp.json()
        return ResetResult(
            observation=EmailObservation(**data["observation"]),
            info=data["info"],
        )

    async def step(self, action: EmailTriageAction) -> StepResult:
        assert self._client
        resp = await self._client.post(
            f"{self._base_url}/step", json=action.model_dump()
        )
        resp.raise_for_status()
        data = resp.json()
        return StepResult(
            observation=EmailObservation(**data["observation"]),
            reward=data["reward"],
            done=data["done"],
            info=data["info"],
        )

    async def state(self) -> EmailTriageState:
        assert self._client
        resp = await self._client.get(f"{self._base_url}/state")
        resp.raise_for_status()
        return EmailTriageState(**resp.json())
