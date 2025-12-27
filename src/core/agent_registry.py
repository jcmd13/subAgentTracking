"""Agent registry for SubAgent Tracking.

Stores agent lifecycle state in a local JSON registry under .subagent/state/.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.core.config import get_config


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _atomic_write(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(payload, indent=2))
    tmp_path.replace(path)


class AgentStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    TERMINATED = "terminated"


TERMINAL_STATUSES = {
    AgentStatus.COMPLETED.value,
    AgentStatus.FAILED.value,
    AgentStatus.TERMINATED.value,
}


@dataclass
class AgentRecord:
    agent_id: str
    agent_type: str
    model: str
    status: AgentStatus = AgentStatus.PENDING
    session_id: Optional[str] = None
    task_id: Optional[str] = None
    created_at: str = field(default_factory=_now_iso)
    updated_at: str = field(default_factory=_now_iso)
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    last_heartbeat: Optional[str] = None
    budget: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["status"] = (
            self.status.value if isinstance(self.status, AgentStatus) else self.status
        )
        return data


class AgentRegistry:
    """Persistent registry for agent lifecycle state."""

    def __init__(self, registry_path: Optional[Path] = None):
        cfg = get_config(reload=True)
        self.registry_path = registry_path or (cfg.state_dir / "agents.json")

    def _load_agents(self) -> List[Dict[str, Any]]:
        if not self.registry_path.exists():
            return []
        try:
            data = json.loads(self.registry_path.read_text())
        except Exception:
            return []
        if isinstance(data, dict):
            agents = data.get("agents", [])
        elif isinstance(data, list):
            agents = data
        else:
            agents = []
        return agents if isinstance(agents, list) else []

    def _save_agents(self, agents: List[Dict[str, Any]]) -> None:
        payload = {"updated_at": _now_iso(), "agents": agents}
        _atomic_write(self.registry_path, payload)

    def _next_agent_id(self, agents: List[Dict[str, Any]]) -> str:
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        return f"agent_{ts}_{len(agents) + 1:03d}"

    def list_agents(
        self,
        *,
        status: Optional[str] = None,
        session_id: Optional[str] = None,
        agent_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        agents = self._load_agents()
        if status:
            agents = [a for a in agents if a.get("status") == status]
        if session_id:
            agents = [a for a in agents if a.get("session_id") == session_id]
        if agent_type:
            agents = [a for a in agents if a.get("agent_type") == agent_type]
        return agents

    def get_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        for agent in self._load_agents():
            if agent.get("agent_id") == agent_id:
                return agent
        return None

    def create_agent(
        self,
        *,
        agent_type: str,
        model: str,
        status: AgentStatus = AgentStatus.RUNNING,
        session_id: Optional[str] = None,
        task_id: Optional[str] = None,
        budget: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        agents = self._load_agents()
        agent_id = self._next_agent_id(agents)
        record = AgentRecord(
            agent_id=agent_id,
            agent_type=agent_type,
            model=model,
            status=status,
            session_id=session_id,
            task_id=task_id,
            started_at=_now_iso() if status == AgentStatus.RUNNING else None,
            budget=budget or {},
            metadata=metadata or {},
        )
        agent_dict = record.to_dict()
        agents.append(agent_dict)
        self._save_agents(agents)
        return agent_dict

    def update_agent(self, agent_id: str, **updates: Any) -> Optional[Dict[str, Any]]:
        agents = self._load_agents()
        for agent in agents:
            if agent.get("agent_id") != agent_id:
                continue
            for key, value in updates.items():
                if value is None:
                    continue
                if key in ("metadata", "metrics", "budget") and isinstance(value, dict):
                    agent.setdefault(key, {}).update(value)
                else:
                    agent[key] = value
            if "status" in updates:
                status_value = updates["status"]
                if isinstance(status_value, AgentStatus):
                    status_value = status_value.value
                agent["status"] = status_value
                if status_value == AgentStatus.RUNNING.value and not agent.get("started_at"):
                    agent["started_at"] = _now_iso()
                if status_value in TERMINAL_STATUSES and not agent.get("completed_at"):
                    agent["completed_at"] = _now_iso()
            agent["updated_at"] = _now_iso()
            self._save_agents(agents)
            return agent
        return None

    def record_heartbeat(
        self,
        agent_id: str,
        *,
        metrics: Optional[Dict[str, Any]] = None,
        note: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        updates: Dict[str, Any] = {"last_heartbeat": _now_iso()}
        if metrics:
            updates["metrics"] = metrics
        if note:
            updates["metadata"] = {"heartbeat_note": note}
        return self.update_agent(agent_id, **updates)


__all__ = [
    "AgentRegistry",
    "AgentRecord",
    "AgentStatus",
]
