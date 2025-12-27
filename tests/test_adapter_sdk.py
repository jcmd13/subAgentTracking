from src.adapters.aider import AiderAdapter
from src.adapters.base import AdapterRegistry
from src.adapters.redaction import RedactionRule, redact_payload


def test_redact_payload_allowlist_and_regex():
    payload = {
        "prompt": "token=sk-1234",
        "metadata": {"user": "alice", "secret": "keep"},
    }
    rules = [RedactionRule(path="prompt", pattern=r"sk-[A-Za-z0-9]+")]
    result = redact_payload(
        payload,
        rules=rules,
        allowlist=["prompt", "metadata.user"],
    )

    assert "metadata" in result
    assert "secret" not in result["metadata"]
    assert "***REDACTED***" in result["prompt"]


def test_aider_adapter_maps_task_started():
    adapter = AiderAdapter()
    event = adapter.map_event(
        {
            "type": "task_started",
            "task_id": "task_1",
            "task_name": "Plan work",
            "stage": "plan",
            "progress_pct": 5,
        }
    )
    assert event is not None
    assert event.event_type == "task.started"
    assert event.payload["task_id"] == "task_1"
    assert event.payload["task_name"] == "Plan work"


def test_aider_adapter_maps_tool_used_defaults_agent():
    adapter = AiderAdapter()
    event = adapter.map_event(
        {
            "type": "tool",
            "tool": "read",
            "success": True,
            "args": {"path": "README.md"},
        }
    )
    assert event is not None
    assert event.event_type == "tool.used"
    assert event.payload["agent"] == "aider"


def test_adapter_registry_register_and_get():
    AdapterRegistry.clear()
    adapter = AiderAdapter()
    AdapterRegistry.register(adapter)
    assert AdapterRegistry.get("aider") is adapter
