"""Redaction helpers for adapter payloads."""

from __future__ import annotations

import copy
import re
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional


@dataclass
class RedactionRule:
    path: Optional[str] = None
    pattern: Optional[str] = None
    replacement: str = "***REDACTED***"


def redact_payload(
    payload: Dict[str, Any],
    *,
    rules: Optional[Iterable[RedactionRule]] = None,
    allowlist: Optional[Iterable[str]] = None,
) -> Dict[str, Any]:
    """Apply allowlist and redaction rules to a payload."""
    data = copy.deepcopy(payload)
    if allowlist:
        data = _apply_allowlist(data, allowlist)
    if rules:
        for rule in rules:
            _apply_redaction_rule(data, rule)
    return data


def _apply_allowlist(payload: Dict[str, Any], allowlist: Iterable[str]) -> Dict[str, Any]:
    filtered: Dict[str, Any] = {}
    for path in allowlist:
        parts = _split_path(path)
        if not parts:
            continue
        value = _get_path_value(payload, parts)
        if value is None:
            continue
        _set_path_value(filtered, parts, value)
    return filtered


def _split_path(path: str) -> List[str]:
    return [part for part in path.split(".") if part]


def _get_path_value(payload: Any, parts: List[str]) -> Optional[Any]:
    current = payload
    for part in parts:
        if isinstance(current, dict):
            if part not in current:
                return None
            current = current[part]
        elif isinstance(current, list) and part.isdigit():
            idx = int(part)
            if idx < 0 or idx >= len(current):
                return None
            current = current[idx]
        else:
            return None
    return current


def _set_path_value(payload: Dict[str, Any], parts: List[str], value: Any) -> None:
    current: Dict[str, Any] = payload
    for idx, part in enumerate(parts):
        is_last = idx == len(parts) - 1
        if is_last:
            current[part] = copy.deepcopy(value)
        else:
            if part not in current or not isinstance(current[part], dict):
                current[part] = {}
            current = current[part]


def _apply_redaction_rule(payload: Any, rule: RedactionRule) -> None:
    if not rule.path:
        _redact_all_strings(payload, rule)
        return
    parts = _split_path(rule.path)
    _apply_rule_to_path(payload, parts, rule)


def _apply_rule_to_path(payload: Any, parts: List[str], rule: RedactionRule) -> Any:
    if not parts:
        return _redact_value(payload, rule)

    part = parts[0]
    remainder = parts[1:]

    if isinstance(payload, dict):
        if part == "*":
            for key in list(payload.keys()):
                payload[key] = _apply_rule_to_path(payload[key], remainder, rule)
        elif part in payload:
            payload[part] = _apply_rule_to_path(payload[part], remainder, rule)
    elif isinstance(payload, list):
        if part == "*":
            for idx in range(len(payload)):
                payload[idx] = _apply_rule_to_path(payload[idx], remainder, rule)
        elif part.isdigit():
            idx = int(part)
            if 0 <= idx < len(payload):
                payload[idx] = _apply_rule_to_path(payload[idx], remainder, rule)
    return payload


def _redact_all_strings(payload: Any, rule: RedactionRule) -> Any:
    if isinstance(payload, dict):
        for key, value in payload.items():
            payload[key] = _redact_all_strings(value, rule)
        return payload
    if isinstance(payload, list):
        for idx, value in enumerate(payload):
            payload[idx] = _redact_all_strings(value, rule)
        return payload
    if isinstance(payload, str):
        return _redact_value(payload, rule)
    return payload


def _redact_value(value: Any, rule: RedactionRule) -> Any:
    if isinstance(value, str):
        if rule.pattern:
            return re.sub(rule.pattern, rule.replacement, value)
        return rule.replacement
    if isinstance(value, dict):
        if rule.pattern:
            return _redact_all_strings(value, rule)
        return rule.replacement
    if isinstance(value, list):
        if rule.pattern:
            return _redact_all_strings(value, rule)
        return rule.replacement
    if rule.pattern:
        return value
    return rule.replacement


__all__ = ["RedactionRule", "redact_payload"]
