"""Adapter for Aider-style events."""

from __future__ import annotations

from typing import Any, Dict, Optional

from src.adapters.base import AdapterEvent, BaseAdapter


class AiderAdapter(BaseAdapter):
    name = "aider"

    def map_event(self, raw_event: Dict[str, Any]) -> Optional[AdapterEvent]:
        event_type = raw_event.get("type") or raw_event.get("event_type")
        if not event_type:
            return None

        if event_type == "task_started":
            return self._map_task_started(raw_event)
        if event_type == "task_stage":
            return self._map_task_stage(raw_event)
        if event_type == "task_completed":
            return self._map_task_completed(raw_event)
        if event_type == "tool":
            return self._map_tool_used(raw_event)
        if event_type == "test_started":
            return self._map_test_started(raw_event)
        if event_type == "test_completed":
            return self._map_test_completed(raw_event)
        return None

    def _map_task_started(self, raw_event: Dict[str, Any]) -> Optional[AdapterEvent]:
        task_id = raw_event.get("task_id")
        task_name = raw_event.get("task_name") or raw_event.get("name")
        stage = raw_event.get("stage")
        if not task_id or not task_name or not stage:
            return None
        payload = {
            "task_id": task_id,
            "task_name": task_name,
            "stage": stage,
            "summary": raw_event.get("summary"),
            "eta_minutes": raw_event.get("eta_minutes"),
            "owner": raw_event.get("owner"),
            "progress_pct": raw_event.get("progress_pct"),
        }
        return AdapterEvent(event_type="task.started", payload=payload)

    def _map_task_stage(self, raw_event: Dict[str, Any]) -> Optional[AdapterEvent]:
        task_id = raw_event.get("task_id")
        stage = raw_event.get("stage")
        if not task_id or not stage:
            return None
        payload = {
            "task_id": task_id,
            "stage": stage,
            "task_name": raw_event.get("task_name"),
            "previous_stage": raw_event.get("previous_stage"),
            "summary": raw_event.get("summary"),
            "progress_pct": raw_event.get("progress_pct"),
        }
        return AdapterEvent(event_type="task.stage_changed", payload=payload)

    def _map_task_completed(self, raw_event: Dict[str, Any]) -> Optional[AdapterEvent]:
        task_id = raw_event.get("task_id")
        status = raw_event.get("status")
        if not task_id or not status:
            return None
        payload = {
            "task_id": task_id,
            "status": status,
            "task_name": raw_event.get("task_name"),
            "summary": raw_event.get("summary"),
            "duration_ms": raw_event.get("duration_ms"),
        }
        return AdapterEvent(event_type="task.completed", payload=payload)

    def _map_tool_used(self, raw_event: Dict[str, Any]) -> Optional[AdapterEvent]:
        tool_name = raw_event.get("tool") or raw_event.get("name")
        if not tool_name:
            return None
        payload = {
            "agent": raw_event.get("agent") or "aider",
            "tool": tool_name,
            "success": raw_event.get("success", True),
            "args": raw_event.get("args") or raw_event.get("parameters"),
            "duration_ms": raw_event.get("duration_ms"),
            "result_size_bytes": raw_event.get("result_size_bytes"),
        }
        return AdapterEvent(event_type="tool.used", payload=payload)

    def _map_test_started(self, raw_event: Dict[str, Any]) -> Optional[AdapterEvent]:
        test_suite = raw_event.get("test_suite") or raw_event.get("suite")
        if not test_suite:
            return None
        payload = {
            "test_suite": test_suite,
            "task_id": raw_event.get("task_id"),
        }
        return AdapterEvent(event_type="test.run_started", payload=payload)

    def _map_test_completed(self, raw_event: Dict[str, Any]) -> Optional[AdapterEvent]:
        test_suite = raw_event.get("test_suite") or raw_event.get("suite")
        status = raw_event.get("status")
        if not test_suite or not status:
            return None
        payload = {
            "test_suite": test_suite,
            "status": status,
            "task_id": raw_event.get("task_id"),
            "duration_ms": raw_event.get("duration_ms"),
            "passed": raw_event.get("passed"),
            "failed": raw_event.get("failed"),
            "summary": raw_event.get("summary"),
        }
        return AdapterEvent(event_type="test.run_completed", payload=payload)


__all__ = ["AiderAdapter"]
