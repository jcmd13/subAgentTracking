"""Quality gate runner."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.quality.gates import (
    GateResult,
    QualityGate,
    ProtectedTestsGate,
    PytestGate,
    CoverageGate,
    DiffReviewGate,
    SecretScanGate,
)
from src.core.config import get_config


class QualityGateRunner:
    """Runs quality gates and aggregates results."""

    def __init__(self, gates: Optional[List[QualityGate]] = None) -> None:
        self.gates = gates or [
            ProtectedTestsGate(),
            PytestGate(),
            CoverageGate(),
            SecretScanGate(),
            DiffReviewGate(),
        ]

    def run(self, *, persist: bool = True) -> Dict[str, Any]:
        results: List[GateResult] = []
        for gate in self.gates:
            try:
                result = gate.run()
            except Exception as exc:
                result = GateResult(
                    name=getattr(gate, "name", gate.__class__.__name__),
                    passed=False,
                    required=getattr(gate, "required", True),
                    message=str(exc),
                )
            results.append(result)

        passed = all(result.passed or not result.required for result in results)
        report = {
            "passed": passed,
            "results": [asdict(result) for result in results],
            "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        }
        if persist:
            self._persist_report(report)
        return report

    def _persist_report(self, report: Dict[str, Any]) -> None:
        try:
            cfg = get_config(reload=True)
            quality_dir = cfg.claude_dir / "quality"
            quality_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            report_path = quality_dir / f"report_{timestamp}.json"
            latest_path = quality_dir / "latest.json"
            payload = json.dumps(report, indent=2)
            report_path.write_text(payload)
            latest_path.write_text(payload)
        except Exception:
            return


__all__ = ["QualityGateRunner"]
