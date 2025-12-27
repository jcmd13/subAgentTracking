"""Budget enforcement helpers for agent lifecycle."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from src.core.cost_tracker import CostTracker


def _parse_iso(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


class BudgetEnforcer:
    """Checks agent metrics against configured budgets."""

    def __init__(self, cost_tracker: Optional[CostTracker] = None) -> None:
        self.cost_tracker = cost_tracker or CostTracker()

    def check(self, record: Dict[str, Any]) -> Dict[str, Any]:
        budget = record.get("budget") or {}
        metrics = dict(record.get("metrics") or {})
        now = datetime.now(timezone.utc)

        input_tokens = metrics.get("input_tokens")
        output_tokens = metrics.get("output_tokens")
        if metrics.get("tokens_used") is None and (input_tokens is not None or output_tokens is not None):
            metrics["tokens_used"] = (input_tokens or 0) + (output_tokens or 0)

        if metrics.get("elapsed_seconds") is None:
            started_at = _parse_iso(record.get("started_at"))
            if started_at:
                metrics["elapsed_seconds"] = (now - started_at).total_seconds()

        if metrics.get("heartbeat_age_seconds") is None:
            last_heartbeat = _parse_iso(record.get("last_heartbeat"))
            if last_heartbeat:
                metrics["heartbeat_age_seconds"] = (now - last_heartbeat).total_seconds()

        cost_limit = budget.get("cost_limit_usd")
        if cost_limit is not None and metrics.get("cost_usd") is None:
            model = record.get("model")
            if model and input_tokens is not None and output_tokens is not None:
                metrics["cost_usd"] = self.cost_tracker.calculate_cost(
                    model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                )

        alerts = []
        hard_alerts = []

        def add_alert(alert_type: str, limit: Any, value: Any, *, severity: str) -> None:
            entry = {"type": alert_type, "limit": limit, "value": value, "severity": severity}
            alerts.append(entry)
            if severity == "hard":
                hard_alerts.append(entry)

        token_limit = budget.get("token_limit")
        tokens_used = metrics.get("tokens_used")
        if token_limit is not None and tokens_used is not None and tokens_used >= token_limit:
            add_alert("token_limit", token_limit, tokens_used, severity="hard")

        time_limit = budget.get("time_limit_seconds")
        elapsed = metrics.get("elapsed_seconds")
        if time_limit is not None and elapsed is not None and elapsed >= time_limit:
            add_alert("time_limit", time_limit, elapsed, severity="hard")

        if cost_limit is not None:
            cost_usd = metrics.get("cost_usd")
            if cost_usd is not None and cost_usd >= cost_limit:
                add_alert("cost_limit", cost_limit, cost_usd, severity="hard")

        heartbeat_interval = budget.get("heartbeat_interval_seconds")
        heartbeat_age = metrics.get("heartbeat_age_seconds")
        if heartbeat_interval is not None and heartbeat_age is not None and heartbeat_age >= heartbeat_interval:
            add_alert("heartbeat_interval", heartbeat_interval, heartbeat_age, severity="soft")

        heartbeat_timeout = budget.get("heartbeat_timeout_seconds")
        if heartbeat_timeout is not None and heartbeat_age is not None and heartbeat_age >= heartbeat_timeout:
            add_alert("heartbeat_timeout", heartbeat_timeout, heartbeat_age, severity="hard")

        sla_timeout = budget.get("sla_timeout_seconds")
        if sla_timeout is not None and elapsed is not None and elapsed >= sla_timeout:
            add_alert("sla_timeout", sla_timeout, elapsed, severity="hard")

        if not alerts:
            return {"exceeded": False, "alerts": [], "metrics": metrics}

        if len(hard_alerts) == 1:
            reason = hard_alerts[0]["type"]
        elif len(hard_alerts) > 1:
            reason = "multiple_limits"
        else:
            reason = None

        return {
            "exceeded": bool(hard_alerts),
            "reason": reason,
            "alerts": alerts,
            "metrics": metrics,
        }


__all__ = ["BudgetEnforcer"]
