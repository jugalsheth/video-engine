from __future__ import annotations

from src.pipeline_config import ai_cost_ceiling_usd


class AICostBudget:
    """Shared AI spend pool across broll, custom visuals, and cutouts."""

    def __init__(self, ceiling_usd: float | None = None) -> None:
        self.ceiling = ceiling_usd if ceiling_usd is not None else ai_cost_ceiling_usd()
        self.spent = 0.0

    @property
    def remaining(self) -> float:
        return max(0.0, self.ceiling - self.spent)

    def can_spend(self, estimate: float = 0.0) -> bool:
        return self.spent + estimate <= self.ceiling + 1e-9

    def charge(self, amount: float) -> bool:
        if not self.can_spend(amount):
            return False
        self.spent = round(self.spent + amount, 4)
        return True

    def exceeded(self) -> bool:
        return self.spent > self.ceiling
