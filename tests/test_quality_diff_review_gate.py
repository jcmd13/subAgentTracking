from src.quality.gates import DiffReviewGate


def test_diff_review_gate_passes_with_overlap(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SUBAGENT_DATA_DIR", str(tmp_path / ".subagent"))
    monkeypatch.setenv("SUBAGENT_CODEX_PROMPT_INSTALL", "false")

    diff_text = """
    diff --git a/src/core/config.py b/src/core/config.py
    +config_loader = True
    """
    gate = DiffReviewGate(
        task_summary="Update config loader",
        diff_text=diff_text,
        modified_paths=["src/core/config.py"],
    )
    result = gate.run()
    assert result.passed is True


def test_diff_review_gate_warns_on_off_task(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SUBAGENT_DATA_DIR", str(tmp_path / ".subagent"))
    monkeypatch.setenv("SUBAGENT_CODEX_PROMPT_INSTALL", "false")

    diff_text = """
    diff --git a/src/worker.py b/src/worker.py
    +worker_mode = "fast"
    """
    gate = DiffReviewGate(
        task_summary="Add metrics exporter",
        diff_text=diff_text,
        modified_paths=["src/worker.py"],
    )
    result = gate.run()
    assert result.passed is False
    assert result.message == "diff_review_off_task"


def test_diff_review_gate_blocks_test_modifications(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SUBAGENT_DATA_DIR", str(tmp_path / ".subagent"))
    monkeypatch.setenv("SUBAGENT_CODEX_PROMPT_INSTALL", "false")

    diff_text = "diff --git a/tests/test_app.py b/tests/test_app.py\n+pass\n"
    gate = DiffReviewGate(
        task_summary="Update config",
        diff_text=diff_text,
        modified_paths=["tests/test_app.py"],
    )
    result = gate.run()
    assert result.passed is False
    assert "Test modifications detected" in result.message
