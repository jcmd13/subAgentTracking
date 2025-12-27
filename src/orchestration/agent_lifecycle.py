"""Lifecycle controls for agents."""

from __future__ import annotations

from typing import Any, Dict, Optional

from src.core.agent_registry import AgentRegistry, AgentStatus
from src.core import activity_logger_compat as activity_logger
from src.orchestration.agent_runtime import get_agent_runtime_manager


class AgentLifecycle:
    """Pause/resume/terminate agents and record status changes."""

    def __init__(
        self,
        registry: Optional[AgentRegistry] = None,
    ) -> None:
        self.registry = registry or AgentRegistry()
        self.runtime = get_agent_runtime_manager()

    def pause_agent(
        self,
        agent_id: str,
        *,
        reason: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        updates = {"status": AgentStatus.PAUSED}
        meta_updates: Dict[str, Any] = {}
        if reason:
            meta_updates["pause_reason"] = reason
        if metadata:
            meta_updates.update(metadata)
        if meta_updates:
            updates["metadata"] = meta_updates
        agent = self.registry.update_agent(agent_id, **updates)
        if agent:
            self.runtime.pause(agent_id)
        return agent

    def resume_agent(
        self,
        agent_id: str,
        *,
        reason: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        updates = {"status": AgentStatus.RUNNING}
        meta_updates: Dict[str, Any] = {}
        if reason:
            meta_updates["resume_reason"] = reason
        if metadata:
            meta_updates.update(metadata)
        if meta_updates:
            updates["metadata"] = meta_updates
        agent = self.registry.update_agent(agent_id, **updates)
        if agent:
            self.runtime.resume(agent_id)
        return agent

    def terminate_agent(
        self,
        agent_id: str,
        *,
        reason: Optional[str] = None,
        error_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        duration_ms: Optional[int] = None,
        tokens_used: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        updates = {"status": AgentStatus.TERMINATED}
        meta_updates: Dict[str, Any] = {}
        if reason:
            meta_updates["termination_reason"] = reason
        if metadata:
            meta_updates.update(metadata)
        if meta_updates:
            updates["metadata"] = meta_updates
        agent = self.registry.update_agent(agent_id, **updates)
        if agent:
            self.runtime.terminate(agent_id)
            self.runtime.unregister(agent_id)
            if error_type:
                self._log_completion(
                    agent,
                    status="failed",
                    reason=reason or "terminated",
                    error_type=error_type,
                    duration_ms=duration_ms,
                    tokens_used=tokens_used,
                )
            else:
                self._log_completion(
                    agent,
                    status="failed",
                    reason=reason or "terminated",
                    duration_ms=duration_ms,
                    tokens_used=tokens_used,
                )
        return agent

    def complete_agent(
        self,
        agent_id: str,
        *,
        reason: Optional[str] = None,
        result: Optional[Dict[str, Any]] = None,
        duration_ms: Optional[int] = None,
        tokens_used: Optional[int] = None,
        input_tokens: Optional[int] = None,
        output_tokens: Optional[int] = None,
        metrics: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        updates: Dict[str, Any] = {"status": AgentStatus.COMPLETED}
        meta_updates: Dict[str, Any] = {}
        if result:
            meta_updates["result"] = result
        if metadata:
            meta_updates.update(metadata)
        if meta_updates:
            updates["metadata"] = meta_updates
        if metrics:
            updates["metrics"] = metrics
        agent = self.registry.update_agent(agent_id, **updates)
        if agent:
            self.runtime.unregister(agent_id)
            self._log_completion(
                agent,
                status="completed",
                reason=reason or "completed",
                duration_ms=duration_ms,
                tokens_used=tokens_used,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            )
        return agent

    def fail_agent(
        self,
        agent_id: str,
        *,
        reason: Optional[str] = None,
        error: Optional[str] = None,
        duration_ms: Optional[int] = None,
        tokens_used: Optional[int] = None,
        input_tokens: Optional[int] = None,
        output_tokens: Optional[int] = None,
        error_type: Optional[str] = None,
        metrics: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        updates: Dict[str, Any] = {"status": AgentStatus.FAILED}
        meta_updates: Dict[str, Any] = {}
        if error:
            meta_updates["error"] = error
        if metadata:
            meta_updates.update(metadata)
        if meta_updates:
            updates["metadata"] = meta_updates
        if metrics:
            updates["metrics"] = metrics
        agent = self.registry.update_agent(agent_id, **updates)
        if agent:
            self.runtime.unregister(agent_id)
            self._log_completion(
                agent,
                status="failed",
                reason=reason or "failed",
                duration_ms=duration_ms,
                tokens_used=tokens_used,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                error_type=error_type,
                error_message=error,
            )
        return agent

    def switch_model(self, agent_id: str, model: str, *, reason: Optional[str] = None) -> Optional[Dict[str, Any]]:
        updates: Dict[str, Any] = {"model": model}
        if reason:
            updates["metadata"] = {"model_switch_reason": reason}
        return self.registry.update_agent(agent_id, **updates)

    def _log_completion(
        self,
        agent: Dict[str, Any],
        *,
        status: str,
        reason: str,
        duration_ms: Optional[int] = None,
        tokens_used: Optional[int] = None,
        input_tokens: Optional[int] = None,
        output_tokens: Optional[int] = None,
        error_type: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> None:
        meta = agent.get("metadata", {}) if isinstance(agent.get("metadata"), dict) else {}
        invoked_by = meta.get("invoked_by", "system")
        agent_type = agent.get("agent_type")
        model = agent.get("model")
        task_id = agent.get("task_id")
        session_id = agent.get("session_id")
        budget = agent.get("budget")
        metrics = agent.get("metrics", {}) if isinstance(agent.get("metrics"), dict) else {}

        duration_ms = duration_ms if duration_ms is not None else int(
            (metrics.get("elapsed_seconds") or 0) * 1000
        )
        if tokens_used is None:
            tokens_used = metrics.get("tokens_used") or metrics.get("tokens_consumed") or 0
        if input_tokens is None:
            input_tokens = metrics.get("input_tokens")
        if output_tokens is None:
            output_tokens = metrics.get("output_tokens")

        reason_text = reason or "agent_completed"
        if len(reason_text) < 10:
            reason_text = f"{reason_text} event"
        try:
            extra: Dict[str, Any] = {}
            if input_tokens is not None:
                extra["input_tokens"] = input_tokens
            if output_tokens is not None:
                extra["output_tokens"] = output_tokens
            if error_type is not None:
                extra["error_type"] = error_type
            if error_message is not None:
                extra["error_message"] = error_message
            activity_logger.log_agent_invocation(
                agent=agent.get("agent_id", "unknown"),
                invoked_by=invoked_by,
                reason=reason_text,
                status=status,
                duration_ms=duration_ms,
                tokens_consumed=tokens_used,
                session_id=session_id,
                context={
                    "agent_type": agent_type,
                    "model": model,
                },
                agent_type=agent_type,
                model=model,
                task_id=task_id,
                budget=budget,
                metrics=metrics,
                **extra,
            )
        except Exception:
            return


__all__ = ["AgentLifecycle"]
