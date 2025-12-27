from src.orchestration.permissions import PermissionManager
from src.orchestration.tool_proxy import ToolProxy


def test_permission_validation(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SUBAGENT_DATA_DIR", str(tmp_path / ".subagent"))
    monkeypatch.setenv("SUBAGENT_CODEX_PROMPT_INSTALL", "false")

    config = {
        "permissions": {
            "default_worker": {
                "tools": ["read", "write"],
                "paths_allowed": ["src/**"],
                "paths_forbidden": [".env*"],
                "can_modify_tests": False,
                "can_run_bash": False,
                "can_access_network": False,
            }
        }
    }
    manager = PermissionManager(config=config, project_root=tmp_path)

    assert manager.validate(tool="read", path="src/main.py").allowed is True
    assert manager.validate(tool="read", path="README.md").allowed is False
    assert manager.validate(tool="read", path=".env").allowed is False
    assert manager.validate(tool="bash", requires_bash=True).allowed is False
    assert manager.validate(tool="curl", requires_network=True).allowed is False
    assert (
        manager.validate(tool="write", operation="write", path="tests/test_app.py").allowed
        is False
    )


def test_tool_proxy_blocks_and_allows(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SUBAGENT_DATA_DIR", str(tmp_path / ".subagent"))
    monkeypatch.setenv("SUBAGENT_CODEX_PROMPT_INSTALL", "false")

    config = {
        "permissions": {
            "default_worker": {
                "tools": ["read"],
                "paths_allowed": ["src/**"],
            }
        }
    }
    manager = PermissionManager(config=config, project_root=tmp_path)
    proxy = ToolProxy(agent_id="agent-test", permission_manager=manager)

    def read_file(path: str) -> str:
        return f"read:{path}"

    denied = proxy.execute(
        "write",
        read_file,
        parameters={"path": "src/main.py"},
        operation="write",
        file_path="src/main.py",
    )
    assert denied.success is False

    allowed = proxy.execute(
        "read",
        read_file,
        parameters={"path": "src/main.py"},
        operation="read",
        file_path="src/main.py",
    )
    assert allowed.success is True
    assert allowed.result == "read:src/main.py"


def test_tool_proxy_requires_approval(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SUBAGENT_DATA_DIR", str(tmp_path / ".subagent"))
    monkeypatch.setenv("SUBAGENT_CODEX_PROMPT_INSTALL", "false")
    monkeypatch.setenv("SUBAGENT_APPROVALS_ENABLED", "true")
    monkeypatch.setenv("SUBAGENT_APPROVAL_THRESHOLD", "0.5")

    config = {
        "permissions": {
            "default_worker": {
                "tools": ["delete"],
                "paths_allowed": ["src/**"],
                "can_modify_tests": True,
            }
        }
    }
    manager = PermissionManager(config=config, project_root=tmp_path)
    proxy = ToolProxy(agent_id="agent-test", permission_manager=manager)

    def delete_file(path: str) -> str:
        return f"deleted:{path}"

    result = proxy.execute(
        "delete",
        delete_file,
        parameters={"path": "src/main.py"},
        operation="delete",
        file_path="src/main.py",
    )
    assert result.success is False
    assert result.error == "approval_required"
