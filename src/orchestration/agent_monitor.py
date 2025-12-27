"""Agent monitoring helpers for lifecycle tracking."""

from __future__ import annotations

from typing import Any, Dict, Optional

from src.core.agent_registry import AgentRegistry, AgentStatus, TERMINAL_STATUSES
from src.core import activity_logger_compat as activity_logger
from src.orchestration.agent_lifecycle import AgentLifecycle
from src.orchestration.budget import BudgetEnforcer


class AgentMonitor:
    """Tracks agent heartbeats and enforces budgets."""

    def __init__(
        self,
        registry: Optional[AgentRegistry] = None,
        budget_enforcer: Optional[BudgetEnforcer] = None,
        lifecycle: Optional[AgentLifecycle] = None,
    ) -> None:
        self.registry = registry or AgentRegistry()
        self.budget_enforcer = budget_enforcer or BudgetEnforcer()
        self.lifecycle = lifecycle or AgentLifecycle(registry=self.registry)

    def record_heartbeat(
        self,
        agent_id: str,
        *,
        metrics: Optional[Dict[str, Any]] = None,
        note: Optional[str] = None,
    ) -> Dict[str, Any]:
        agent = self.registry.record_heartbeat(agent_id, metrics=metrics, note=note)
        if not agent:
            return {"success": False, "error": "agent_not_found"}

        budget_check = self.budget_enforcer.check(agent)
        updated_metrics = budget_check.get("metrics")
        if updated_metrics and updated_metrics != agent.get("metrics"):
            agent = self.registry.update_agent(agent_id, metrics=updated_metrics) or agent

        alerts = budget_check.get("alerts", [])
        if budget_check.get("exceeded") and agent.get("status") not in TERMINAL_STATUSES:
            reason = budget_check.get("reason") or "budget_exceeded"
            timeout_alert = _select_timeout_alert(alerts)
            if timeout_alert:
                agent = self._handle_timeout(agent, timeout_alert, alerts)
            else:
                agent = self.lifecycle.terminate_agent(
                    agent_id,
                    reason=_format_reason(reason),
                    error_type="BudgetExceeded",
                    metadata={"budget_alerts": alerts},
                ) or agent
            return {
                "success": True,
                "terminated": True,
                "agent": agent,
                "alerts": alerts,
            }

        return {
            "success": True,
            "terminated": False,
            "agent": agent,
            "alerts": alerts,
        }

    def check_timeouts(self) -> Dict[str, Any]:
        """Scan running agents for SLA or heartbeat timeouts."""
        agents = self.registry.list_agents(status=AgentStatus.RUNNING.value)
        timed_out = []
        for agent in agents:
            budget_check = self.budget_enforcer.check(agent)
            alerts = budget_check.get("alerts", [])
            timeout_alert = _select_timeout_alert(alerts)
            if not timeout_alert:
                continue
            updated_metrics = budget_check.get("metrics")
            if updated_metrics and updated_metrics != agent.get("metrics"):
                agent = self.registry.update_agent(
                    agent.get("agent_id"),
                    metrics=updated_metrics,
                ) or agent
            timed_out_agent = self._handle_timeout(agent, timeout_alert, alerts)
            if timed_out_agent:
                timed_out.append(timed_out_agent)
        return {"checked": len(agents), "timed_out": timed_out}

    def _handle_timeout(
        self,
        agent: Dict[str, Any],
        timeout_alert: Dict[str, Any],
        alerts: list,
    ) -> Dict[str, Any]:
        agent_id = agent.get("agent_id")
        timeout_seconds = timeout_alert.get("limit") or 0
        elapsed_seconds = timeout_alert.get("value") or 0
        reason = _timeout_reason(timeout_alert.get("type"))
        updated_agent = self.lifecycle.terminate_agent(
            agent_id,
            reason=reason,
            error_type="TimeoutError",
            metadata={"budget_alerts": alerts},
        ) or agent
        try:
            activity_logger.log_agent_timeout(
                agent=agent_id or "unknown",
                timeout_ms=int(timeout_seconds * 1000),
                elapsed_ms=int(elapsed_seconds * 1000),
                session_id=agent.get("session_id"),
                reason=reason,
                agent_type=agent.get("agent_type"),
                model=agent.get("model"),
            )
        except Exception:
            pass
        return updated_agent


def _select_timeout_alert(alerts: list) -> Optional[Dict[str, Any]]:
    for alert in alerts:
        if alert.get("type") in ("heartbeat_timeout", "sla_timeout", "time_limit"):
            return alert
    return None


def _timeout_reason(alert_type: Optional[str]) -> str:
    if alert_type == "heartbeat_timeout":
        return "Heartbeat timeout exceeded"
    if alert_type == "sla_timeout":
        return "SLA timeout exceeded"
    return "Time limit exceeded"


def _format_reason(reason: str) -> str:
    if len(reason) >= 10:
        return reason
    return f"{reason} exceeded"


__all__ = ["AgentMonitor"]
