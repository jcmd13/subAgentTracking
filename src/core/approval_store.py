"""Approval persistence store for risky actions."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from src.core.config import get_config

logger = logging.getLogger(__name__)

_DECISION_STATUSES = {"granted", "denied"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _store_path() -> Path:
    cfg = get_config(reload=True)
    cfg.approvals_dir.mkdir(parents=True, exist_ok=True)
    return cfg.approvals_dir / "approvals.json"


def _read_store(path: Optional[Path] = None) -> Dict[str, Any]:
    path = path or _store_path()
    if not path.exists():
        return {"approvals": {}}
    try:
        data = json.loads(path.read_text())
        if isinstance(data, dict) and "approvals" in data:
            return data
    except Exception:
        logger.warning("Failed to read approvals store at %s", path, exc_info=True)
    return {"approvals": {}}


def _write_store(data: Dict[str, Any], path: Optional[Path] = None) -> None:
    path = path or _store_path()
    tmp_path = path.with_suffix(".tmp")
    tmp_path.write_text(json.dumps(data, indent=2))
    tmp_path.replace(path)


@dataclass
class ApprovalRecord:
    approval_id: str
    status: str
    tool: str
    risk_score: float
    reasons: List[str]
    action: str
    created_at: str
    updated_at: str
    session_id: Optional[str] = None
    operation: Optional[str] = None
    file_path: Optional[str] = None
    agent: Optional[str] = None
    profile: Optional[str] = None
    requires_network: Optional[bool] = None
    requires_bash: Optional[bool] = None
    modifies_tests: Optional[bool] = None
    summary: Optional[str] = None
    decision: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "approval_id": self.approval_id,
            "status": self.status,
            "tool": self.tool,
            "risk_score": self.risk_score,
            "reasons": self.reasons,
            "action": self.action,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "session_id": self.session_id,
            "operation": self.operation,
            "file_path": self.file_path,
            "agent": self.agent,
            "profile": self.profile,
            "requires_network": self.requires_network,
            "requires_bash": self.requires_bash,
            "modifies_tests": self.modifies_tests,
            "summary": self.summary,
            "decision": self.decision,
        }


def record_required(
    *,
    tool: str,
    risk_score: float,
    reasons: List[str],
    action: str,
    approval_id: Optional[str] = None,
    session_id: Optional[str] = None,
    operation: Optional[str] = None,
    file_path: Optional[str] = None,
    agent: Optional[str] = None,
    profile: Optional[str] = None,
    requires_network: Optional[bool] = None,
    requires_bash: Optional[bool] = None,
    modifies_tests: Optional[bool] = None,
    summary: Optional[str] = None,
) -> ApprovalRecord:
    approval_id = approval_id or f"appr_{uuid4().hex[:10]}"
    timestamp = _now_iso()
    record = ApprovalRecord(
        approval_id=approval_id,
        status="required",
        tool=tool,
        risk_score=risk_score,
        reasons=reasons,
        action=action,
        created_at=timestamp,
        updated_at=timestamp,
        session_id=session_id,
        operation=operation,
        file_path=file_path,
        agent=agent,
        profile=profile,
        requires_network=requires_network,
        requires_bash=requires_bash,
        modifies_tests=modifies_tests,
        summary=summary,
        decision=None,
    )

    data = _read_store()
    approvals = data.setdefault("approvals", {})
    approvals[approval_id] = record.to_dict()
    _write_store(data)
    return record


def record_decision(
    approval_id: str,
    status: str,
    *,
    actor: Optional[str] = None,
    reason: Optional[str] = None,
) -> Optional[ApprovalRecord]:
    if status not in _DECISION_STATUSES:
        raise ValueError(f"Invalid approval status: {status}")
    data = _read_store()
    approvals = data.setdefault("approvals", {})
    existing = approvals.get(approval_id)
    if not existing:
        return None

    timestamp = _now_iso()
    existing["status"] = status
    existing["updated_at"] = timestamp
    existing["decision"] = {
        "status": status,
        "actor": actor,
        "reason": reason,
        "decided_at": timestamp,
    }
    approvals[approval_id] = existing
    _write_store(data)
    return ApprovalRecord(**existing)


def list_approvals(status: Optional[str] = None) -> List[Dict[str, Any]]:
    data = _read_store()
    approvals = list(data.get("approvals", {}).values())
    if status:
        approvals = [item for item in approvals if item.get("status") == status]
    approvals.sort(key=lambda item: item.get("updated_at", ""), reverse=True)
    return approvals


def get_approval(approval_id: str) -> Optional[Dict[str, Any]]:
    data = _read_store()
    return data.get("approvals", {}).get(approval_id)


__all__ = [
    "ApprovalRecord",
    "record_required",
    "record_decision",
    "list_approvals",
    "get_approval",
]
