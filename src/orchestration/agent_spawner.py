"""Agent spawner for creating registry entries and selecting models."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.core.agent_registry import AgentRegistry, AgentStatus
from src.core import activity_logger_compat as activity_logger
from src.orchestration.agent_executor import AgentExecutor
from src.orchestration.agent_lifecycle import AgentLifecycle
from src.orchestration.model_router import get_model_router, ModelRouter


DEFAULT_MODEL = "claude-sonnet-3.5"


class AgentSpawner:
    """Creates agent records and selects models via the ModelRouter."""

    def __init__(
        self,
        registry: Optional[AgentRegistry] = None,
        router: Optional[ModelRouter] = None,
    ) -> None:
        self.registry = registry or AgentRegistry()
        self.router = router or get_model_router()

    def spawn(
        self,
        *,
        agent_type: str,
        task_id: Optional[str] = None,
        session_id: Optional[str] = None,
        model: Optional[str] = None,
        invoked_by: str = "user",
        reason: str = "Manual agent spawn",
        task_type: Optional[str] = None,
        context_tokens: int = 0,
        files: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        budget: Optional[Dict[str, Any]] = None,
        permission_profile: Optional[str] = None,
        execute: bool = False,
        execution: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        routing_metadata: Dict[str, Any] = {}
        selected_model = model

        if not selected_model and self.router:
            task = {
                "type": task_type or agent_type,
                "context_tokens": context_tokens,
                "files": files or [],
            }
            selected_model, tier, routing_metadata = self.router.select_model(task)
            routing_metadata = dict(routing_metadata)
            routing_metadata["tier"] = tier

        if not selected_model:
            selected_model = DEFAULT_MODEL

        combined_metadata = dict(metadata or {})
        if routing_metadata:
            combined_metadata.setdefault("routing", routing_metadata)
        combined_metadata.setdefault("invoked_by", invoked_by)
        combined_metadata.setdefault("spawn_reason", reason)
        if permission_profile:
            combined_metadata.setdefault("permission_profile", permission_profile)

        if execute:
            exec_meta: Dict[str, Any] = {}
            exec_cfg = execution or {}
            if exec_cfg.get("command"):
                exec_meta["mode"] = "subprocess"
                exec_meta["command"] = exec_cfg.get("command")
            else:
                exec_meta["mode"] = exec_cfg.get("mode", "in_process")
                if exec_cfg.get("prompt"):
                    exec_meta["prompt_preview"] = str(exec_cfg.get("prompt"))[:200]
            exec_meta["background"] = exec_cfg.get("background", True)
            combined_metadata.setdefault("execution", exec_meta)

        record = self.registry.create_agent(
            agent_type=agent_type,
            model=selected_model,
            status=AgentStatus.RUNNING,
            session_id=session_id,
            task_id=task_id,
            budget=budget,
            metadata=combined_metadata,
        )

        try:
            activity_logger.log_agent_invocation(
                agent=record["agent_id"],
                invoked_by=invoked_by,
                reason=reason,
                status="started",
                session_id=session_id,
                context={
                    "agent_type": agent_type,
                    "model": selected_model,
                    "task_id": task_id,
                    "session_id": session_id,
                },
                agent_type=agent_type,
                model=selected_model,
                task_id=task_id,
                budget=budget,
                model_tier=routing_metadata.get("tier") if routing_metadata else None,
                context_tokens=context_tokens,
                files=files or [],
            )
        except Exception:
            pass

        if execute:
            executor = AgentExecutor(registry=self.registry)
            lifecycle = AgentLifecycle(registry=self.registry)
            try:
                exec_args = {
                    key: value
                    for key, value in (execution or {}).items()
                    if key in {
                        "mode",
                        "prompt",
                        "command",
                        "provider",
                        "env",
                        "cwd",
                        "background",
                        "permission_profile",
                        "requires_bash",
                        "requires_network",
                        "file_path",
                    }
                }
                executor.start_execution(record["agent_id"], **exec_args)
            except Exception as exc:
                lifecycle.fail_agent(
                    record["agent_id"],
                    reason="Execution failed to start",
                    error=str(exc),
                    error_type="SpawnError",
                )

        return record


__all__ = ["AgentSpawner"]
