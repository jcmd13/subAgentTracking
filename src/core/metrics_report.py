"""Metrics aggregation and value reporting."""

from __future__ import annotations

import gzip
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import yaml

from src.core.config import get_config
from src.core.activity_logger import list_log_files, get_current_session_id
from src.core.event_types import (
    AGENT_COMPLETED,
    AGENT_FAILED,
    TASK_STARTED,
    TASK_COMPLETED,
    TEST_RUN_COMPLETED,
    COST_TRACKED,
)


_NAIVE_MULTIPLIER_ENV = "SUBAGENT_NAIVE_COST_MULTIPLIER"


@dataclass
class LogMetrics:
    session_id: Optional[str]
    events_total: int = 0
    agents_completed: int = 0
    agents_failed: int = 0
    tasks_started: int = 0
    tasks_completed: int = 0
    tests_passed: int = 0
    tests_failed: int = 0
    tests_warning: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cost_total: float = 0.0
    cost_by_task: Dict[str, float] = None
    cost_by_model: Dict[str, float] = None
    cost_source: str = "none"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "events_total": self.events_total,
            "agents": {
                "completed": self.agents_completed,
                "failed": self.agents_failed,
            },
            "tasks": {
                "started": self.tasks_started,
                "completed": self.tasks_completed,
            },
            "tests": {
                "passed": self.tests_passed,
                "failed": self.tests_failed,
                "warning": self.tests_warning,
            },
            "tokens": {
                "input": self.input_tokens,
                "output": self.output_tokens,
                "total": self.total_tokens,
            },
            "cost": {
                "total": round(self.cost_total, 6),
                "by_task": self.cost_by_task or {},
                "by_model": self.cost_by_model or {},
                "source": self.cost_source,
            },
        }


@dataclass
class QualityMetrics:
    report_count: int = 0
    gate_pass_rate: Optional[float] = None
    required_pass_rate: Optional[float] = None
    coverage_percentages: List[int] = None
    latest_report: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_count": self.report_count,
            "gate_pass_rate": self.gate_pass_rate,
            "required_pass_rate": self.required_pass_rate,
            "coverage_percentages": self.coverage_percentages or [],
            "latest_report": self.latest_report,
        }


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _iter_events(log_path: Path) -> Iterable[Dict[str, Any]]:
    opener = gzip.open if log_path.suffix == ".gz" else open
    with opener(log_path, "rt", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def _load_pricing(config_dir: Path) -> Dict[str, Dict[str, Any]]:
    pricing_path = config_dir / "model_pricing.yaml"
    if not pricing_path.exists():
        return {}
    try:
        data = yaml.safe_load(pricing_path.read_text()) or {}
    except Exception:
        return {}
    models = data.get("models", {})
    return models if isinstance(models, dict) else {}


def _calculate_cost(
    pricing: Dict[str, Dict[str, Any]],
    model: Optional[str],
    input_tokens: int,
    output_tokens: int,
    tokens_used: int,
) -> Tuple[float, Optional[str]]:
    if not model:
        return 0.0, None
    model_cfg = pricing.get(model)
    if not model_cfg:
        return 0.0, None

    input_price = float(model_cfg.get("input_price_per_1m", 0.0))
    output_price = float(model_cfg.get("output_price_per_1m", 0.0))

    if input_tokens == 0 and output_tokens == 0 and tokens_used:
        input_tokens = tokens_used
        output_tokens = 0
        return (
            round((input_tokens / 1_000_000) * input_price, 6),
            "tokens_used",
        )

    cost = (input_tokens / 1_000_000) * input_price + (output_tokens / 1_000_000) * output_price
    return round(cost, 6), None


def _summarize_log(
    log_path: Path,
    *,
    session_id: Optional[str] = None,
    task_id: Optional[str] = None,
    pricing: Optional[Dict[str, Dict[str, Any]]] = None,
) -> LogMetrics:
    metrics = LogMetrics(session_id=session_id, cost_by_task={}, cost_by_model={})
    pricing = pricing or {}
    cost_from_agent = 0.0
    cost_from_cost_events = 0.0

    for event in _iter_events(log_path):
        metrics.events_total += 1
        event_type = event.get("event_type")

        if task_id:
            event_task = event.get("task_id")
            if event_task and event_task != task_id:
                continue

        if event_type == AGENT_COMPLETED:
            metrics.agents_completed += 1
            input_tokens = int(event.get("input_tokens") or 0)
            output_tokens = int(event.get("output_tokens") or 0)
            tokens_used = int(event.get("tokens_used") or event.get("tokens_consumed") or 0)
            metrics.input_tokens += input_tokens
            metrics.output_tokens += output_tokens
            metrics.total_tokens += max(tokens_used, input_tokens + output_tokens)

            model = event.get("model")
            cost, _ = _calculate_cost(pricing, model, input_tokens, output_tokens, tokens_used)
            if cost:
                cost_from_agent += cost
                if model:
                    metrics.cost_by_model[model] = round(metrics.cost_by_model.get(model, 0.0) + cost, 6)
                task_key = event.get("task_id")
                if task_key:
                    metrics.cost_by_task[task_key] = round(
                        metrics.cost_by_task.get(task_key, 0.0) + cost,
                        6,
                    )

        elif event_type == AGENT_FAILED:
            metrics.agents_failed += 1

        elif event_type == TASK_STARTED:
            metrics.tasks_started += 1

        elif event_type == TASK_COMPLETED:
            metrics.tasks_completed += 1

        elif event_type == TEST_RUN_COMPLETED:
            status = event.get("status")
            if status == "passed":
                metrics.tests_passed += 1
            elif status == "failed":
                metrics.tests_failed += 1
            else:
                metrics.tests_warning += 1

        elif event_type == COST_TRACKED:
            cost = float(event.get("cost_usd") or event.get("cost") or 0.0)
            if cost:
                cost_from_cost_events += cost

    if cost_from_cost_events > 0:
        metrics.cost_total = round(cost_from_cost_events, 6)
        metrics.cost_source = "cost_events"
    elif cost_from_agent > 0:
        metrics.cost_total = round(cost_from_agent, 6)
        metrics.cost_source = "agent_events"

    return metrics


def _find_log_for_session(session_id: Optional[str]) -> Optional[Path]:
    if not session_id:
        return None
    for entry in list_log_files():
        if entry.get("session_id") == session_id:
            return Path(entry.get("file_path"))
    return None


def _collect_quality_reports(quality_dir: Path) -> List[Dict[str, Any]]:
    if not quality_dir.exists():
        return []
    reports = []
    for path in sorted(quality_dir.glob("report_*.json")):
        try:
            reports.append(json.loads(path.read_text()))
        except Exception:
            continue
    return reports


def _extract_coverage_percent(result: Dict[str, Any]) -> Optional[int]:
    details = result.get("details") or {}
    stdout = details.get("stdout") or ""
    match = re.search(r"TOTAL\s+\d+\s+\d+\s+(\d+)%", stdout)
    if not match:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None


def _summarize_quality(reports: List[Dict[str, Any]]) -> QualityMetrics:
    metrics = QualityMetrics(report_count=len(reports), coverage_percentages=[])
    if not reports:
        return metrics

    gate_rates: List[float] = []
    required_rates: List[float] = []

    for report in reports:
        results = report.get("results") or []
        if not results:
            continue
        total = len(results)
        passed = sum(1 for r in results if r.get("passed"))
        required_results = [r for r in results if r.get("required", True)]
        required_total = len(required_results)
        required_passed = sum(1 for r in required_results if r.get("passed"))
        if total:
            gate_rates.append(passed / total)
        if required_total:
            required_rates.append(required_passed / required_total)

        for result in results:
            if result.get("name") == "coverage":
                coverage = _extract_coverage_percent(result)
                if coverage is not None:
                    metrics.coverage_percentages.append(coverage)

    if gate_rates:
        metrics.gate_pass_rate = round(sum(gate_rates) / len(gate_rates), 4)
    if required_rates:
        metrics.required_pass_rate = round(sum(required_rates) / len(required_rates), 4)

    metrics.latest_report = reports[-1]
    return metrics


def _naive_comparison(cost_total: float, compare: bool) -> Optional[Dict[str, Any]]:
    if not compare:
        return None
    multiplier = float(os.getenv(_NAIVE_MULTIPLIER_ENV, "2.0"))
    naive_cost = round(cost_total * multiplier, 6)
    savings = None
    if naive_cost > 0:
        savings = round(((naive_cost - cost_total) / naive_cost) * 100, 2)
    return {
        "naive_multiplier": multiplier,
        "naive_cost": naive_cost,
        "savings_pct": savings,
    }


def generate_metrics_report(
    *,
    scope: str = "session",
    session_id: Optional[str] = None,
    task_id: Optional[str] = None,
    compare_naive: bool = True,
) -> Dict[str, Any]:
    cfg = get_config(reload=True)
    pricing = _load_pricing(cfg.claude_dir / "config")

    scope_lower = scope.lower()
    logs = list_log_files()
    quality_reports = _collect_quality_reports(cfg.claude_dir / "quality")
    quality_metrics = _summarize_quality(quality_reports).to_dict()

    summary: LogMetrics
    log_paths: List[Path] = []

    if scope_lower == "session":
        session_id = session_id or get_current_session_id()
        if session_id is None and logs:
            session_id = logs[0].get("session_id")
        log_path = _find_log_for_session(session_id)
        if log_path:
            log_paths = [log_path]
            summary = _summarize_log(log_path, session_id=session_id, pricing=pricing)
        else:
            summary = LogMetrics(session_id=session_id, cost_by_task={}, cost_by_model={})

    elif scope_lower == "task":
        if not task_id:
            raise ValueError("task_id is required for task scope")
        log_paths = [Path(entry.get("file_path")) for entry in logs]
        combined = LogMetrics(session_id=None, cost_by_task={}, cost_by_model={})
        cost_sources: set[str] = set()
        for entry in logs:
            path = Path(entry.get("file_path"))
            metrics = _summarize_log(
                path,
                session_id=entry.get("session_id"),
                task_id=task_id,
                pricing=pricing,
            )
            combined.events_total += metrics.events_total
            combined.agents_completed += metrics.agents_completed
            combined.agents_failed += metrics.agents_failed
            combined.tasks_started += metrics.tasks_started
            combined.tasks_completed += metrics.tasks_completed
            combined.tests_passed += metrics.tests_passed
            combined.tests_failed += metrics.tests_failed
            combined.tests_warning += metrics.tests_warning
            combined.input_tokens += metrics.input_tokens
            combined.output_tokens += metrics.output_tokens
            combined.total_tokens += metrics.total_tokens
            combined.cost_total += metrics.cost_total
            if metrics.cost_total > 0 and metrics.cost_source:
                cost_sources.add(metrics.cost_source)
            for key, value in (metrics.cost_by_task or {}).items():
                combined.cost_by_task[key] = round(combined.cost_by_task.get(key, 0.0) + value, 6)
            for key, value in (metrics.cost_by_model or {}).items():
                combined.cost_by_model[key] = round(combined.cost_by_model.get(key, 0.0) + value, 6)
        if cost_sources:
            combined.cost_source = cost_sources.pop() if len(cost_sources) == 1 else "mixed"
        summary = combined

    elif scope_lower == "project":
        log_paths = [Path(entry.get("file_path")) for entry in logs]
        combined = LogMetrics(session_id=None, cost_by_task={}, cost_by_model={})
        cost_sources: set[str] = set()
        for entry in logs:
            path = Path(entry.get("file_path"))
            metrics = _summarize_log(path, session_id=entry.get("session_id"), pricing=pricing)
            combined.events_total += metrics.events_total
            combined.agents_completed += metrics.agents_completed
            combined.agents_failed += metrics.agents_failed
            combined.tasks_started += metrics.tasks_started
            combined.tasks_completed += metrics.tasks_completed
            combined.tests_passed += metrics.tests_passed
            combined.tests_failed += metrics.tests_failed
            combined.tests_warning += metrics.tests_warning
            combined.input_tokens += metrics.input_tokens
            combined.output_tokens += metrics.output_tokens
            combined.total_tokens += metrics.total_tokens
            combined.cost_total += metrics.cost_total
            if metrics.cost_total > 0 and metrics.cost_source:
                cost_sources.add(metrics.cost_source)
            for key, value in (metrics.cost_by_task or {}).items():
                combined.cost_by_task[key] = round(combined.cost_by_task.get(key, 0.0) + value, 6)
            for key, value in (metrics.cost_by_model or {}).items():
                combined.cost_by_model[key] = round(combined.cost_by_model.get(key, 0.0) + value, 6)
        if cost_sources:
            combined.cost_source = cost_sources.pop() if len(cost_sources) == 1 else "mixed"
        summary = combined

    else:
        raise ValueError(f"Unknown scope: {scope}")

    naive_comparison = _naive_comparison(summary.cost_total, compare_naive)

    return {
        "scope": scope_lower,
        "session_id": session_id,
        "task_id": task_id,
        "log_files": [str(path) for path in log_paths],
        "metrics": summary.to_dict(),
        "quality": quality_metrics,
        "naive_comparison": naive_comparison,
        "generated_at": _now_iso(),
    }


def render_metrics_markdown(report: Dict[str, Any]) -> str:
    metrics = report.get("metrics", {})
    cost = metrics.get("cost", {})
    tokens = metrics.get("tokens", {})
    tasks = metrics.get("tasks", {})
    tests = metrics.get("tests", {})
    agents = metrics.get("agents", {})
    quality = report.get("quality", {})
    naive = report.get("naive_comparison") or {}

    lines = [
        "# SubAgent Metrics Report",
        "",
        f"- Scope: {report.get('scope')}",
    ]
    if report.get("session_id"):
        lines.append(f"- Session: {report.get('session_id')}")
    if report.get("task_id"):
        lines.append(f"- Task: {report.get('task_id')}")
    lines.append(f"- Generated: {report.get('generated_at')}")
    lines.append("")

    lines.extend(
        [
            "## Activity",
            f"- Events: {metrics.get('events_total', 0)}",
            f"- Agents: {agents.get('completed', 0)} completed, {agents.get('failed', 0)} failed",
            f"- Tasks: {tasks.get('started', 0)} started, {tasks.get('completed', 0)} completed",
            f"- Tests: {tests.get('passed', 0)} passed, {tests.get('failed', 0)} failed, {tests.get('warning', 0)} warning",
            "",
            "## Tokens",
            f"- Input: {tokens.get('input', 0)}",
            f"- Output: {tokens.get('output', 0)}",
            f"- Total: {tokens.get('total', 0)}",
            "",
            "## Cost",
            f"- Total: ${cost.get('total', 0.0)}",
            f"- Source: {cost.get('source', 'none')}",
        ]
    )

    if naive:
        savings = naive.get("savings_pct")
        savings_label = f"{savings}%" if savings is not None else "n/a"
        lines.extend(
            [
                f"- Naive multiplier: {naive.get('naive_multiplier')}",
                f"- Naive cost: ${naive.get('naive_cost')}",
                f"- Savings: {savings_label}",
            ]
        )

    lines.extend(["", "## Quality"])
    lines.append(f"- Reports: {quality.get('report_count', 0)}")
    if quality.get("gate_pass_rate") is not None:
        lines.append(f"- Gate pass rate: {quality.get('gate_pass_rate')}")
    if quality.get("required_pass_rate") is not None:
        lines.append(f"- Required gate pass rate: {quality.get('required_pass_rate')}")
    coverage = quality.get("coverage_percentages") or []
    if coverage:
        lines.append(f"- Coverage trend: {', '.join(str(c) + '%' for c in coverage[-5:])}")

    return "\n".join(lines) + "\n"


__all__ = ["generate_metrics_report", "render_metrics_markdown"]
