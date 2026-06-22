"""Smoke tests for the bundled ``examples/``.

The examples drifted out of sync with the current API and silently rotted
(``await event_bus.publish(...)`` after ``publish`` became sync, ``with
log_tool_usage(...)`` after it stopped being a context manager, invalid
``FileOperationType`` values, a missing required ``rationale``, writing to a
``.subagent/`` dir that didn't exist). These tests keep them honest:

* Self-contained examples are executed end-to-end and must exit 0.
* Server examples (which start a WebSocket/dashboard server and loop) can't run
  to completion in CI, so we at least import them to catch syntax/import drift.
"""

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
EXAMPLES = REPO / "examples"

# Run to completion without binding ports / starting servers.
SELF_CONTAINED = ["basic_usage", "custom_events", "analytics_queries", "mcp_smoke_test"]

# Start servers and loop; import-checked only.
SERVER_EXAMPLES = ["dashboard_example", "full_observability_example"]


@pytest.mark.parametrize("name", SELF_CONTAINED)
def test_self_contained_example_runs(name, tmp_path):
    data_dir = tmp_path / ".subagent"
    data_dir.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, "PYTHONPATH": str(REPO), "SUBAGENT_DATA_DIR": str(data_dir)}

    result = subprocess.run(
        [sys.executable, str(EXAMPLES / f"{name}.py")],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )

    assert result.returncode == 0, (
        f"examples/{name}.py exited {result.returncode}\n"
        f"STDOUT:\n{result.stdout[-2000:]}\nSTDERR:\n{result.stderr[-2000:]}"
    )
    assert "Traceback" not in result.stderr, (
        f"examples/{name}.py logged a traceback:\n{result.stderr[-2000:]}"
    )


@pytest.mark.parametrize("name", SERVER_EXAMPLES)
def test_server_example_imports(name):
    spec = importlib.util.spec_from_file_location(name, EXAMPLES / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # raises on syntax/import drift
