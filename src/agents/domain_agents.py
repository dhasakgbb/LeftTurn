"""Chat-facing agents that delegate to the orchestrator."""
from __future__ import annotations
from typing import Any


class _BaseAgent:
    def __init__(self, orchestrator: Any) -> None:
        self._orchestrator = orchestrator

    def handle(self, query: Any) -> Any:
        return self._orchestrator.handle(query)


class DomainAgent(_BaseAgent):
    """Generic agent for broad logistics questions."""

    @property
    def default_prompt(self) -> str:
        """Return the system prompt used for domain-wide queries."""
        return "General logistics assistant."


class CarrierAgent(_BaseAgent):
    """Agent dedicated to carrier-specific operations and contracts."""

    @property
    def default_prompt(self) -> str:
        """Return the system prompt used for carrier questions."""
        return "Carrier operations assistant."


class CustomerOpsAgent(_BaseAgent):
    """Agent focused on customer operations and support topics."""

    @property
    def default_prompt(self) -> str:
        """Return the system prompt used for customer ops questions."""
        return "Customer operations assistant."


class ClaimsAgent(_BaseAgent):
    """Agent focused on claims/disputes workflows.

    Delegates retrieval and calculations to the orchestrator, while the
    front-end (Teams or Copilot) can present specialized intents like
    "open dispute packet" or "explain variance".
    """

    @property
    def default_prompt(self) -> str:
<<<<<<< Updated upstream
        """Return the system prompt used for claims questions."""
        return "Claims assistant."

=======
        return "Claims and dispute assistant."
>>>>>>> Stashed changes
