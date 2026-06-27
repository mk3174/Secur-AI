"""Model router.

Phase 1 routes every request to the single configured backend and computes
cost. The interface is deliberately the seam where Phase 2 multi-backend,
strategy-based routing, fallback and circuit breaking plug in.
"""

from __future__ import annotations

from securai.config import Settings
from securai.modules.gateway.domain.messages import CanonicalChatResponse, Usage
from securai.modules.gateway.domain.ports import LLMProvider

# Default pricing table (micro-USD per 1k tokens). Phase 2 sources this per backend.
DEFAULT_PRICE_IN = 0
DEFAULT_PRICE_OUT = 0


class RouteDecision:
    def __init__(self, *, provider: LLMProvider, model: str) -> None:
        self.provider = provider
        self.model = model


class ModelRouter:
    def __init__(self, *, provider: LLMProvider, settings: Settings) -> None:
        self._provider = provider
        self._settings = settings

    def select(self, model: str | None) -> RouteDecision:
        chosen_model = model or self._settings.default_model
        return RouteDecision(provider=self._provider, model=chosen_model)

    @staticmethod
    def estimate_cost_micro_usd(
        usage: Usage, *, price_in: int = DEFAULT_PRICE_IN, price_out: int = DEFAULT_PRICE_OUT
    ) -> int:
        cost = (usage.prompt_tokens * price_in + usage.completion_tokens * price_out) // 1000
        return int(cost)

    async def health(self) -> bool:
        return await self._provider.health()

    @property
    def provider_name(self) -> str:
        return self._provider.name

    def annotate_cost(self, response: CanonicalChatResponse) -> int:
        return self.estimate_cost_micro_usd(response.usage)
