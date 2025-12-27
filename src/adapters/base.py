"""Adapter base classes and registry."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Union

from src.core import activity_logger_compat as activity_logger
from src.adapters.redaction import RedactionRule, redact_payload


@dataclass
class AdapterEvent:
    event_type: str
    payload: Dict[str, Any]
    session_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class BaseAdapter:
    name = "base"

    def __init__(
        self,
        *,
        allowlist: Optional[Iterable[str]] = None,
        redaction_rules: Optional[Iterable[RedactionRule]] = None,
    ) -> None:
        self.allowlist = list(allowlist) if allowlist else None
        self.redaction_rules = list(redaction_rules) if redaction_rules else []

    def sanitize(self, raw_event: Dict[str, Any]) -> Dict[str, Any]:
        return redact_payload(
            raw_event,
            rules=self.redaction_rules,
            allowlist=self.allowlist,
        )

    def map_event(self, raw_event: Dict[str, Any]) -> Optional[Union[AdapterEvent, List[AdapterEvent]]]:
        raise NotImplementedError

    def emit(self, event: AdapterEvent) -> str:
        payload = dict(event.payload)
        if event.metadata:
            payload.setdefault("metadata", event.metadata)
        return activity_logger.emit_event(
            event.event_type,
            payload,
            session_id=event.session_id,
        )

    def handle_event(self, raw_event: Dict[str, Any]) -> Optional[Union[str, List[str]]]:
        sanitized = self.sanitize(raw_event)
        mapped = self.map_event(sanitized)
        if mapped is None:
            return None
        if isinstance(mapped, list):
            return [self.emit(item) for item in mapped]
        return self.emit(mapped)

    async def handle_event_async(self, raw_event: Dict[str, Any]) -> Optional[Union[str, List[str]]]:
        return self.handle_event(raw_event)


class AdapterRegistry:
    _registry: Dict[str, BaseAdapter] = {}

    @classmethod
    def register(cls, adapter: BaseAdapter) -> BaseAdapter:
        if not adapter.name:
            raise ValueError("Adapter name is required")
        cls._registry[adapter.name] = adapter
        return adapter

    @classmethod
    def get(cls, name: str) -> Optional[BaseAdapter]:
        return cls._registry.get(name)

    @classmethod
    def list(cls) -> List[str]:
        return sorted(cls._registry.keys())

    @classmethod
    def clear(cls) -> None:
        cls._registry.clear()


__all__ = ["AdapterEvent", "BaseAdapter", "AdapterRegistry", "RedactionRule"]
