"""Chat-facing agents that delegate to the orchestrator."""
from __future__ import annotations
from typing import Any


class _BaseAgent:
    def __init__(self, orchestrator: Any) -> None:
        self._orchestrator = orchestrator

    def handle(self, query: str) -> Any:
        return self._orchestrator.handle(query)


class DomainAgent(_BaseAgent):
    pass


class CarrierAgent(_BaseAgent):
    pass


class CustomerOpsAgent(_BaseAgent):
    pass
