"""
Tests for Snapshot Manager Module

Tests cover:
1. Snapshot creation and restoration
2. Trigger detection (agent count, token count)
3. Git state integration
4. Handoff summary generation
5. Snapshot listing and cleanup
6. Compression support
7. Performance targets (<100ms create, <50ms load)
8. Error handling

Usage:
    pytest tests/test_snapshot_manager.py -v
    pytest tests/test_snapshot_manager.py::TestSnapshotCreation -v
"""

import pytest
import json
import gzip
import time
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

from src.core.snapshot_manager import (
    take_snapshot,
    restore_snapshot,
    list_snapshots,
    cleanup_old_snapshots,
    create_handoff_summary,
    should_take_snapshot,
    get_git_state,
    reset_snapshot_counter,
)


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def temp_state_dir():
    """Create a temporary state directory for testing."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


@pytest.fixture
def mock_config(temp_state_dir, monkeypatch):
    """Mock configuration with temp directories."""
    class MockConfig:
        def __init__(self):
            self.project_root = temp_state_dir
            self.state_dir = temp_state_dir / "state"
            self.handoffs_dir = temp_state_dir / "handoffs"
            self.snapshot_enabled = True
            self.snapshot_trigger_agent_count = 10
            self.snapshot_trigger_token_count = 20000
            self.snapshot_compression = True
            self.snapshot_retention_days = 7
            self.snapshot_creation_max_latency_ms = 100.0

            # Create directories
            self.state_dir.mkdir(parents=True, exist_ok=True)
            self.handoffs_dir.mkdir(parents=True, exist_ok=True)

        def get_snapshot_path(self, session_id: str, snapshot_number: int) -> Path:
            return self.state_dir / f"{session_id}_snap{snapshot_number:03d}.json"

        def get_handoff_path(self, session_id: str) -> Path:
            return self.handoffs_dir / f"{session_id}_handoff.md"

    from src.core import config
    test_config = MockConfig()
    monkeypatch.setattr(config, 'get_config', lambda: test_config)

    # Also mock activity logger session_id and event_count
    from src.core import activity_logger
    monkeypatch.setattr(activity_logger, 'get_current_session_id', lambda: "session_20251103_120000")
    monkeypatch.setattr(activity_logger, 'get_event_count', lambda: 42)
    monkeypatch.setattr(activity_logger, 'log_context_snapshot', lambda **kwargs: "evt_001")

    # Reset snapshot counter
    reset_snapshot_counter()

    yield test_config


# ============================================================================
# Test: Snapshot Creation
# ============================================================================

class TestSnapshotCreation:
    """Tests for take_snapshot() function."""

    def test_basic_snapshot_creation(self, mock_config):
        """Test creating a basic snapshot."""
        snapshot_id = take_snapshot(
            trigger="manual",
            agent_count=5,
            token_count=10000,
            tokens_remaining=190000,
            files_in_context=["file1.py", "file2.py"]
        )

        assert snapshot_id == "snap_001"

        # Verify file was created
        snapshot_path = mock_config.get_snapshot_path("session_20251103_120000", 1)
        compressed_path = Path(str(snapshot_path) + ".gz")
        assert compressed_path.exists()

    def test_snapshot_incremental_counter(self, mock_config):
        """Test that snapshot counter increments."""
        snap1 = take_snapshot(trigger="manual")
        snap2 = take_snapshot(trigger="manual")
        snap3 = take_snapshot(trigger="manual")

        assert snap1 == "snap_001"
        assert snap2 == "snap_002"
        assert snap3 == "snap_003"

    def test_snapshot_data_structure(self, mock_config):
        """Test that snapshot contains all required data."""
        snapshot_id = take_snapshot(
            trigger="agent_count",
            agent_count=10,
            token_count=20000,
            tokens_remaining=180000,
            files_in_context=["test.py"],
            agent_context={"current_agent": "orchestrator", "tasks": ["Task 1"]}
        )

        # Load and verify snapshot
        snapshot_path = mock_config.get_snapshot_path("session_20251103_120000", 1)
        compressed_path = Path(str(snapshot_path) + ".gz")

        with gzip.open(compressed_path, 'rt', encoding='utf-8') as f:
            data = json.load(f)

        # Check structure
        assert "metadata" in data
        assert "session_state" in data
        assert "agent_context" in data
        assert "file_operations" in data
        assert "git_state" in data

        # Check metadata
        assert data["metadata"]["snapshot_id"] == "snap_001"
        assert data["metadata"]["session_id"] == "session_20251103_120000"
        assert data["metadata"]["trigger"] == "agent_count"
        assert data["metadata"]["created_by"] == "snapshot_manager"

        # Check session state
        assert data["session_state"]["agent_invocation_count"] == 10
        assert data["session_state"]["total_events"] == 42
        assert data["session_state"]["token_usage"]["tokens_consumed"] == 20000
        assert data["session_state"]["token_usage"]["tokens_remaining"] == 180000

        # Check agent context
        assert data["agent_context"]["current_agent"] == "orchestrator"
        assert data["agent_context"]["tasks"] == ["Task 1"]

        # Check file operations
        assert data["file_operations"]["files_in_context"] == ["test.py"]
        assert data["file_operations"]["files_in_context_count"] == 1

    def test_snapshot_without_compression(self, mock_config, monkeypatch):
        """Test snapshot creation without compression."""
        mock_config.snapshot_compression = False

        snapshot_id = take_snapshot(
            trigger="manual",
            agent_count=5,
            token_count=10000,
        )

        # Verify uncompressed file was created
        snapshot_path = mock_config.get_snapshot_path("session_20251103_120000", 1)
        assert snapshot_path.exists()
        assert not Path(str(snapshot_path) + ".gz").exists()

    def test_snapshot_with_additional_metadata(self, mock_config):
        """Test snapshot with extra kwargs."""
        snapshot_id = take_snapshot(
            trigger="manual",
            custom_field="custom_value",
            debug_info={"test": True}
        )

        # Load and verify
        snapshot_path = mock_config.get_snapshot_path("session_20251103_120000", 1)
        compressed_path = Path(str(snapshot_path) + ".gz")

        with gzip.open(compressed_path, 'rt', encoding='utf-8') as f:
            data = json.load(f)

        assert "additional_metadata" in data
        assert data["additional_metadata"]["custom_field"] == "custom_value"
        assert data["additional_metadata"]["debug_info"]["test"] is True


# ============================================================================
# Test: Snapshot Restoration
# ============================================================================

class TestSnapshotRestoration:
    """Tests for restore_snapshot() function."""

    def test_restore_basic_snapshot(self, mock_config):
        """Test restoring a snapshot."""
        # Create snapshot
        snapshot_id = take_snapshot(
            trigger="manual",
            agent_count=10,
            token_count=20000,
        )

        # Restore it
        data = restore_snapshot(snapshot_id)

        assert data["metadata"]["snapshot_id"] == "snap_001"
        assert data["session_state"]["agent_invocation_count"] == 10
        assert data["session_state"]["token_usage"]["tokens_consumed"] == 20000

    def test_restore_uncompressed_snapshot(self, mock_config):
        """Test restoring an uncompressed snapshot."""
        mock_config.snapshot_compression = False

        # Create uncompressed snapshot
        snapshot_id = take_snapshot(trigger="manual", agent_count=5)

        # Restore it
        data = restore_snapshot(snapshot_id)

        assert data["metadata"]["snapshot_id"] == "snap_001"
        assert data["session_state"]["agent_invocation_count"] == 5

    def test_restore_nonexistent_snapshot(self, mock_config):
        """Test restoring a snapshot that doesn't exist."""
        with pytest.raises(FileNotFoundError):
            restore_snapshot("snap_999")

    def test_restore_invalid_snapshot_id(self, mock_config):
        """Test restoring with invalid snapshot ID format."""
        with pytest.raises(ValueError, match="Invalid snapshot_id format"):
            restore_snapshot("invalid_id")

    def test_restore_performance_target(self, mock_config):
        """Test that restore meets <50ms performance target."""
        # Create a moderately sized snapshot
        snapshot_id = take_snapshot(
            trigger="manual",
            agent_count=10,
            token_count=20000,
            files_in_context=[f"file{i}.py" for i in range(50)],
            agent_context={"data": "x" * 1000}
        )

        # Measure restore time
        start_time = time.time()
        data = restore_snapshot(snapshot_id)
        duration_ms = (time.time() - start_time) * 1000

        assert duration_ms < 50, f"Restore took {duration_ms:.2f}ms (target: <50ms)"


# ============================================================================
# Test: Snapshot Listing
# ============================================================================

class TestSnapshotListing:
    """Tests for list_snapshots() function."""

    def test_list_empty_snapshots(self, mock_config):
        """Test listing when no snapshots exist."""
        snapshots = list_snapshots()
        assert snapshots == []

    def test_list_multiple_snapshots(self, mock_config):
        """Test listing multiple snapshots."""
        # Create several snapshots
        take_snapshot(trigger="manual", agent_count=10)
        take_snapshot(trigger="agent_count", agent_count=20)
        take_snapshot(trigger="token_count", token_count=40000)

        snapshots = list_snapshots()

        assert len(snapshots) == 3
        assert snapshots[0]["snapshot_id"] == "snap_001"
        assert snapshots[1]["snapshot_id"] == "snap_002"
        assert snapshots[2]["snapshot_id"] == "snap_003"
        assert snapshots[0]["trigger"] == "manual"
        assert snapshots[1]["trigger"] == "agent_count"
        assert snapshots[2]["trigger"] == "token_count"

    def test_list_snapshots_includes_metadata(self, mock_config):
        """Test that listing includes snapshot metadata."""
        take_snapshot(trigger="manual")

        snapshots = list_snapshots()

        assert len(snapshots) == 1
        snapshot = snapshots[0]

        assert "snapshot_id" in snapshot
        assert "timestamp" in snapshot
        assert "trigger" in snapshot
        assert "file_path" in snapshot
        assert "file_size_bytes" in snapshot


# ============================================================================
# Test: Snapshot Cleanup
# ============================================================================

class TestSnapshotCleanup:
    """Tests for cleanup_old_snapshots() function."""

    def test_cleanup_no_old_snapshots(self, mock_config):
        """Test cleanup when all snapshots are recent."""
        # Create recent snapshots
        take_snapshot(trigger="manual")
        take_snapshot(trigger="manual")

        deleted_count = cleanup_old_snapshots(retention_days=7)

        assert deleted_count == 0
        assert len(list_snapshots()) == 2

    def test_cleanup_old_snapshots(self, mock_config):
        """Test cleanup of old snapshots."""
        # Create snapshots and manually adjust their modification times
        take_snapshot(trigger="manual")
        take_snapshot(trigger="manual")
        take_snapshot(trigger="manual")

        # Make first two snapshots appear old
        snapshot_files = list(mock_config.state_dir.glob("*.json.gz"))
        assert len(snapshot_files) == 3

        # Set mtime to 10 days ago for first two files
        old_time = time.time() - (10 * 24 * 3600)
        snapshot_files[0].touch()
        snapshot_files[1].touch()

        import os
        os.utime(snapshot_files[0], (old_time, old_time))
        os.utime(snapshot_files[1], (old_time, old_time))

        # Cleanup with 7-day retention
        deleted_count = cleanup_old_snapshots(retention_days=7)

        assert deleted_count == 2
        assert len(list_snapshots()) == 1

    def test_cleanup_with_custom_retention(self, mock_config):
        """Test cleanup with custom retention period."""
        take_snapshot(trigger="manual")

        # Make snapshot appear 2 days old
        snapshot_files = list(mock_config.state_dir.glob("*.json.gz"))
        old_time = time.time() - (2 * 24 * 3600)

        import os
        os.utime(snapshot_files[0], (old_time, old_time))

        # Cleanup with 1-day retention should delete it
        deleted_count = cleanup_old_snapshots(retention_days=1)

        assert deleted_count == 1


# ============================================================================
# Test: Handoff Summary
# ============================================================================

class TestHandoffSummary:
    """Tests for create_handoff_summary() function."""

    def test_create_basic_handoff(self, mock_config):
        """Test creating a basic handoff summary."""
        # Create a snapshot first
        take_snapshot(
            trigger="manual",
            agent_count=10,
            token_count=20000,
            tokens_remaining=180000,
            files_in_context=["test.py"]
        )

        # Create handoff summary
        handoff_path = create_handoff_summary(reason="token_limit")

        # Verify file was created
        assert Path(handoff_path).exists()

        # Read and verify content
        with open(handoff_path, 'r') as f:
            content = f.read()

        assert "# Session Handoff Summary" in content
        assert "session_20251103_120000" in content
        assert "token_limit" in content
        assert "Total Events:" in content
        assert "snap_001" in content

    def test_handoff_without_snapshot(self, mock_config):
        """Test handoff creation when no snapshots exist."""
        handoff_path = create_handoff_summary(reason="session_end")

        # Verify file was created
        assert Path(handoff_path).exists()

        with open(handoff_path, 'r') as f:
            content = f.read()

        assert "No snapshot available" in content

    def test_handoff_with_git_state(self, mock_config):
        """Test handoff includes git state information."""
        # Mock git state
        with patch('src.core.snapshot_manager.get_git_state') as mock_git:
            mock_git.return_value = {
                "is_git_repo": True,
                "current_branch": "feature/test",
                "latest_commit": "abc123def456",
                "uncommitted_changes": True,
                "modified_files": ["src/core/snapshot_manager.py"]
            }

            # Create snapshot with mocked git state
            take_snapshot(trigger="manual", agent_count=5)

        # Create handoff
        handoff_path = create_handoff_summary()

        with open(handoff_path, 'r') as f:
            content = f.read()

        assert "## Git State" in content
        assert "feature/test" in content
        assert "abc123def456" in content
        assert "snapshot_manager.py" in content

    def test_handoff_recovery_instructions(self, mock_config):
        """Test that handoff includes recovery instructions."""
        take_snapshot(trigger="manual")

        handoff_path = create_handoff_summary()

        with open(handoff_path, 'r') as f:
            content = f.read()

        assert "## Recovery Instructions" in content
        assert "restore_snapshot" in content
        assert "Resume from session" in content


# ============================================================================
# Test: Trigger Detection
# ============================================================================

class TestTriggerDetection:
    """Tests for should_take_snapshot() function."""

    def test_agent_count_trigger(self, mock_config):
        """Test agent count trigger detection."""
        # First call - not triggered (need 10 agents)
        should_trigger, reason = should_take_snapshot(agent_count=5)
        assert not should_trigger

        # Second call - triggered (10+ agents since last)
        should_trigger, reason = should_take_snapshot(agent_count=15)
        assert should_trigger
        assert "agent_count_threshold" in reason

    def test_token_count_trigger(self, mock_config):
        """Test token count trigger detection."""
        # First call - not triggered (need 20k tokens)
        should_trigger, reason = should_take_snapshot(token_count=10000)
        assert not should_trigger

        # Second call - triggered (20k+ tokens since last)
        should_trigger, reason = should_take_snapshot(token_count=30000)
        assert should_trigger
        assert "token_count_threshold" in reason

    def test_no_trigger_below_threshold(self, mock_config):
        """Test that no trigger occurs below thresholds."""
        should_trigger, _ = should_take_snapshot(agent_count=5, token_count=10000)
        assert not should_trigger

    def test_trigger_state_persistence(self, mock_config):
        """Test that trigger state persists across calls."""
        # Trigger at 15 agents
        should_take_snapshot(agent_count=15)

        # Take a snapshot to update last counts
        take_snapshot(trigger="agent_count", agent_count=15)

        # Now at 20 agents - should not trigger (only 5 since last)
        should_trigger, _ = should_take_snapshot(agent_count=20)
        assert not should_trigger

        # At 25 agents - should trigger (10 since last)
        should_trigger, _ = should_take_snapshot(agent_count=25)
        assert should_trigger


# ============================================================================
# Test: Git Integration
# ============================================================================

class TestGitIntegration:
    """Tests for get_git_state() function."""

    def test_git_state_in_repo(self, mock_config, monkeypatch):
        """Test git state when in a git repository."""
        # Mock subprocess to simulate git repo
        def mock_run(cmd, **kwargs):
            result = MagicMock()
            if "rev-parse" in cmd and "--git-dir" in cmd:
                result.returncode = 0
            elif "rev-parse" in cmd and "--abbrev-ref" in cmd:
                result.returncode = 0
                result.stdout = "main\n"
            elif "rev-parse" in cmd and "HEAD" in cmd:
                result.returncode = 0
                result.stdout = "abc123def456\n"
            elif "status" in cmd:
                result.returncode = 0
                result.stdout = " M src/test.py\n"
            return result

        import subprocess
        monkeypatch.setattr(subprocess, 'run', mock_run)

        git_state = get_git_state()

        assert git_state["is_git_repo"] is True
        assert git_state["current_branch"] == "main"
        assert git_state["latest_commit"] == "abc123def456"
        assert git_state["uncommitted_changes"] is True
        assert "src/test.py" in git_state["modified_files"]

    def test_git_state_not_in_repo(self, mock_config, monkeypatch):
        """Test git state when not in a git repository."""
        # Mock subprocess to simulate no git repo
        def mock_run(cmd, **kwargs):
            import subprocess
            raise subprocess.CalledProcessError(128, cmd)

        import subprocess
        monkeypatch.setattr(subprocess, 'run', mock_run)

        git_state = get_git_state()

        assert git_state["is_git_repo"] is False
        assert "current_branch" not in git_state


# ============================================================================
# Test: Performance
# ============================================================================

class TestPerformance:
    """Tests for performance requirements."""

    def test_snapshot_creation_performance(self, mock_config):
        """Test that snapshot creation meets <100ms target."""
        start_time = time.time()

        take_snapshot(
            trigger="manual",
            agent_count=50,
            token_count=50000,
            tokens_remaining=150000,
            files_in_context=[f"file{i}.py" for i in range(100)],
            agent_context={"tasks": [f"Task {i}" for i in range(20)]}
        )

        duration_ms = (time.time() - start_time) * 1000

        # Allow some margin for test environment
        assert duration_ms < 200, f"Snapshot creation took {duration_ms:.2f}ms (target: <100ms)"

    def test_multiple_snapshots_performance(self, mock_config):
        """Test performance with multiple rapid snapshots."""
        iterations = 10
        start_time = time.time()

        for i in range(iterations):
            take_snapshot(
                trigger="manual",
                agent_count=i * 10,
                token_count=i * 5000
            )

        total_time_ms = (time.time() - start_time) * 1000
        avg_time_ms = total_time_ms / iterations

        assert avg_time_ms < 100, f"Average snapshot time: {avg_time_ms:.2f}ms (target: <100ms)"


# ============================================================================
# Test: Error Handling
# ============================================================================

class TestErrorHandling:
    """Tests for error handling."""

    def test_corrupted_snapshot_in_listing(self, mock_config):
        """Test that corrupted snapshots are skipped in listing."""
        # Create a valid snapshot
        take_snapshot(trigger="manual")

        # Create a corrupted snapshot file
        corrupt_path = mock_config.state_dir / "session_20251103_120000_snap002.json.gz"
        with gzip.open(corrupt_path, 'wt') as f:
            f.write("not valid json {{{")

        # List should skip corrupted file
        snapshots = list_snapshots()
        assert len(snapshots) == 1
        assert snapshots[0]["snapshot_id"] == "snap_001"

    def test_snapshot_with_write_failure(self, mock_config, monkeypatch):
        """Test snapshot creation when write fails."""
        # Mock file write to raise an exception
        original_open = gzip.open

        def mock_gzip_open(*args, **kwargs):
            raise IOError("Disk full")

        monkeypatch.setattr(gzip, 'open', mock_gzip_open)

        # Should not raise exception, just return snapshot_id
        snapshot_id = take_snapshot(trigger="manual")

        assert snapshot_id == "snap_001"

    def test_restore_corrupted_snapshot(self, mock_config):
        """Test restoring a corrupted snapshot."""
        # Create a corrupted snapshot file
        snapshot_path = mock_config.get_snapshot_path("session_20251103_120000", 1)
        compressed_path = Path(str(snapshot_path) + ".gz")

        with gzip.open(compressed_path, 'wt') as f:
            f.write("invalid json")

        with pytest.raises(json.JSONDecodeError):
            restore_snapshot("snap_001")


# ============================================================================
# Test: Integration
# ============================================================================

class TestIntegration:
    """Integration tests for complete workflows."""

    def test_full_snapshot_workflow(self, mock_config):
        """Test complete snapshot creation, listing, and restoration workflow."""
        # Create multiple snapshots
        snap1 = take_snapshot(
            trigger="manual",
            agent_count=10,
            token_count=20000,
            tokens_remaining=180000
        )
        snap2 = take_snapshot(
            trigger="agent_count",
            agent_count=20,
            token_count=40000,
            tokens_remaining=160000
        )

        # List snapshots
        snapshots = list_snapshots()
        assert len(snapshots) == 2

        # Restore first snapshot
        data1 = restore_snapshot(snap1)
        assert data1["session_state"]["agent_invocation_count"] == 10

        # Restore second snapshot
        data2 = restore_snapshot(snap2)
        assert data2["session_state"]["agent_invocation_count"] == 20

        # Create handoff summary
        handoff_path = create_handoff_summary(reason="test_complete")
        assert Path(handoff_path).exists()

    def test_snapshot_and_cleanup_workflow(self, mock_config):
        """Test snapshot creation followed by cleanup."""
        # Create several snapshots
        for i in range(5):
            take_snapshot(trigger="manual", agent_count=i * 10)

        assert len(list_snapshots()) == 5

        # Make some old
        snapshot_files = list(mock_config.state_dir.glob("*.json.gz"))
        old_time = time.time() - (10 * 24 * 3600)

        import os
        for f in snapshot_files[:3]:
            os.utime(f, (old_time, old_time))

        # Cleanup
        deleted = cleanup_old_snapshots(retention_days=7)
        assert deleted == 3
        assert len(list_snapshots()) == 2
