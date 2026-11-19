"""Model calls of the offline Reading pipeline, recorded like the app's (one `llm_calls` row each).

Every attempt counts, failed and rejected ones too: they cost money. Free models (`:free` routes)
cost nothing; the rest use the configured prices (`LLM_PRICE_*_PER_MTOK`). The running total is
what the pipeline's cost cap reads.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import psycopg

from app.llm.gateway import Attempt
from app.writing.model_calls import Prices


@dataclass
class CallLog:
    prices: Prices
    pending: list[Attempt] = field(default_factory=list)
    calls: int = 0
    failed: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0

    def observe(self, attempt: Attempt) -> None:
        self.pending.append(attempt)

    def cost(self, a: Attempt) -> float:
        return 0.0 if a.route.model.endswith(":free") else self.prices.cost(a)

    def flush(self, conn: psycopg.Connection[Any], now: datetime) -> None:
        """Write the attempts seen since the last flush and add them to the totals."""
        for a in self.pending:
            out = a.output_tokens + a.thoughts_tokens
            cost = self.cost(a)
            conn.execute(
                "insert into llm_calls(tier,model,latency_ms,cost_usd,success,task,"
                "input_tokens,output_tokens,created_at) values (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (a.tier, a.route.model, round(a.latency_ms), cost, a.status == "success",
                 a.task, a.input_tokens, out, now),
            )  # fmt: skip
            self.calls += 1
            self.failed += int(a.status != "success")
            self.input_tokens += a.input_tokens
            self.output_tokens += out
            self.cost_usd += cost
        self.pending.clear()

    def summary(self) -> str:
        return (
            f"model calls: {self.calls} ({self.failed} failed), tokens in {self.input_tokens} "
            f"out {self.output_tokens}, cost US${self.cost_usd:.4f}"
        )
