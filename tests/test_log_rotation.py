"""
Tests for Activity Logger - Log Rotation Functionality

Tests the log rotation, cleanup, and file management features of the activity logger.

Test Coverage:
- list_log_files(): List all log files with metadata
- get_log_file_stats(): Get statistics about log files
- rotate_logs(): Rotate/cleanup old log files
- Automatic rotation on startup
- Edge cases: no files, single file, many files, errors
"""

import pytest
import tempfile
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any

from src.core import activity_logger
from src.core import config as config_module


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def temp_logs_dir():
    """Create temporary directory for log files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_config(temp_logs_dir, monkeypatch):
    """Mock configuration with temp directories."""

    class MockConfig:
        def __init__(self):
            self.project_root = temp_logs_dir
            self.logs_dir = temp_logs_dir / "logs"
            self.activity_log_enabled = True
            self.activity_log_compression = True
            self.activity_log_retention_count = 2
            self.validate_event_schemas = False
            self.strict_mode = False

            self.logs_dir.mkdir(parents=True, exist_ok=True)

    test_config = MockConfig()

    # Mock get_config in both places
    monkeypatch.setattr(config_module, "get_config", lambda: test_config)
    monkeypatch.setattr("src.core.activity_logger.get_config", lambda: test_config)

    # Reset logger state
    activity_logger._initialized = False
    activity_logger._writer = None
    activity_logger._session_id = None
    activity_logger._event_counter = None

    yield test_config

    # Cleanup after test
    if activity_logger._initialized:
        activity_logger.shutdown()


def create_dummy_log_file(
    logs_dir: Path, session_id: str, compressed: bool = True, size_bytes: int = 1000
):
    """
    Helper function to create a dummy log file.

    Args:
        logs_dir: Directory to create log file in
        session_id: Session ID for the log file
        compressed: Whether to create .gz file
        size_bytes: Approximate file size
    """
    suffix = ".jsonl.gz" if compressed else ".jsonl"
    file_path = logs_dir / f"{session_id}{suffix}"

    # Write dummy content
    content = '{"event_type":"test"}\n' * (size_bytes // 20)

    if compressed:
        import gzip

        with gzip.open(file_path, "wt", encoding="utf-8") as f:
            f.write(content)
    else:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

    return file_path


# ============================================================================
# Test list_log_files()
# ============================================================================


class TestListLogFiles:
    """Tests for list_log_files() function."""

    def test_empty_directory(self, mock_config):
        """Test listing with no log files."""
        files = activity_logger.list_log_files()
        assert files == []

    def test_single_compressed_file(self, mock_config):
        """Test listing with one compressed log file."""
        session_id = "session_20251103_120000"
        create_dummy_log_file(mock_config.logs_dir, session_id, compressed=True)

        files = activity_logger.list_log_files()

        assert len(files) == 1
        assert files[0]["session_id"] == session_id
        assert files[0]["is_compressed"] is True
        assert files[0]["file_size_bytes"] > 0

    def test_single_uncompressed_file(self, mock_config):
        """Test listing with one uncompressed log file."""
        session_id = "session_20251103_130000"
        create_dummy_log_file(mock_config.logs_dir, session_id, compressed=False)

        files = activity_logger.list_log_files()

        assert len(files) == 1
        assert files[0]["session_id"] == session_id
        assert files[0]["is_compressed"] is False

    def test_multiple_files_sorted_by_time(self, mock_config):
        """Test that files are sorted by creation time (newest first)."""
        sessions = [
            "session_20251103_100000",
            "session_20251103_110000",
            "session_20251103_120000",
        ]

        for i, session_id in enumerate(sessions):
            create_dummy_log_file(mock_config.logs_dir, session_id)
            time.sleep(0.01)  # Ensure different creation times

        files = activity_logger.list_log_files()

        assert len(files) == 3
        # Newest should be first (120000)
        assert files[0]["session_id"] == sessions[2]
        assert files[1]["session_id"] == sessions[1]
        assert files[2]["session_id"] == sessions[0]

    def test_mixed_compressed_and_uncompressed(self, mock_config):
        """Test listing with both compressed and uncompressed files."""
        create_dummy_log_file(mock_config.logs_dir, "session_20251103_120000", compressed=True)
        create_dummy_log_file(mock_config.logs_dir, "session_20251103_130000", compressed=False)

        files = activity_logger.list_log_files()

        assert len(files) == 2
        compressed_count = sum(1 for f in files if f["is_compressed"])
        uncompressed_count = sum(1 for f in files if not f["is_compressed"])

        assert compressed_count == 1
        assert uncompressed_count == 1

    def test_ignores_non_log_files(self, mock_config):
        """Test that non-log files are ignored."""
        create_dummy_log_file(mock_config.logs_dir, "session_20251103_120000")

        # Create non-log files
        (mock_config.logs_dir / "README.md").write_text("test")
        (mock_config.logs_dir / "data.json").write_text("{}")
        (mock_config.logs_dir / ".gitkeep").write_text("")

        files = activity_logger.list_log_files()

        assert len(files) == 1
        assert files[0]["session_id"] == "session_20251103_120000"


# ============================================================================
# Test get_log_file_stats()
# ============================================================================


class TestLogFileStats:
    """Tests for get_log_file_stats() function."""

    def test_stats_empty_directory(self, mock_config):
        """Test stats with no log files."""
        stats = activity_logger.get_log_file_stats()

        assert stats["total_files"] == 0
        assert stats["total_size_bytes"] == 0
        assert stats["oldest_session"] is None
        assert stats["newest_session"] is None

    def test_stats_single_file(self, mock_config):
        """Test stats with one log file."""
        session_id = "session_20251103_120000"
        create_dummy_log_file(mock_config.logs_dir, session_id, size_bytes=5000)

        stats = activity_logger.get_log_file_stats()

        assert stats["total_files"] == 1
        assert stats["total_size_bytes"] > 0
        assert stats["oldest_session"] == session_id
        assert stats["newest_session"] == session_id

    def test_stats_multiple_files(self, mock_config):
        """Test stats with multiple log files."""
        sessions = [
            "session_20251103_100000",
            "session_20251103_110000",
            "session_20251103_120000",
        ]

        for session_id in sessions:
            create_dummy_log_file(mock_config.logs_dir, session_id, size_bytes=2000)
            time.sleep(0.01)

        stats = activity_logger.get_log_file_stats()

        assert stats["total_files"] == 3
        assert stats["total_size_bytes"] > 0
        assert stats["oldest_session"] == sessions[0]
        assert stats["newest_session"] == sessions[2]


# ============================================================================
# Test rotate_logs()
# ============================================================================


class TestRotateLogs:
    """Tests for rotate_logs() function."""

    def test_rotate_empty_directory(self, mock_config):
        """Test rotation with no log files."""
        result = activity_logger.rotate_logs()

        assert result["files_deleted"] == 0
        assert result["files_kept"] == 0
        assert result["bytes_freed"] == 0
        assert result["sessions_deleted"] == []
        assert result["errors"] == []

    def test_rotate_single_file_no_current_session(self, mock_config):
        """Test rotation with one file and no active session."""
        session_id = "session_20251103_120000"
        create_dummy_log_file(mock_config.logs_dir, session_id)

        # Retention count = 2 (keep 2 files)
        result = activity_logger.rotate_logs(retention_count=2)

        # File should be kept (within retention limit)
        assert result["files_deleted"] == 0
        assert result["files_kept"] == 1

    def test_rotate_keeps_recent_files(self, mock_config):
        """Test that recent files are kept within retention limit."""
        sessions = [
            "session_20251103_100000",
            "session_20251103_110000",
            "session_20251103_120000",
        ]

        for session_id in sessions:
            create_dummy_log_file(mock_config.logs_dir, session_id)
            time.sleep(0.01)

        # Keep 2 files (current + 1 previous)
        result = activity_logger.rotate_logs(retention_count=2)

        # Should delete 1 file (oldest)
        assert result["files_deleted"] == 1
        assert result["files_kept"] == 2
        assert sessions[0] in result["sessions_deleted"]
        assert result["bytes_freed"] > 0

        # Verify files on disk
        remaining_files = activity_logger.list_log_files()
        assert len(remaining_files) == 2
        remaining_sessions = [f["session_id"] for f in remaining_files]
        assert sessions[1] in remaining_sessions
        assert sessions[2] in remaining_sessions
        assert sessions[0] not in remaining_sessions

    def test_rotate_deletes_old_files(self, mock_config):
        """Test that old files are deleted when exceeding retention."""
        sessions = [
            "session_20251103_100000",
            "session_20251103_110000",
            "session_20251103_120000",
            "session_20251103_130000",
            "session_20251103_140000",
        ]

        for session_id in sessions:
            create_dummy_log_file(mock_config.logs_dir, session_id, size_bytes=500)
            time.sleep(0.01)

        # Keep only 2 files
        result = activity_logger.rotate_logs(retention_count=2)

        # Should delete 3 oldest files
        assert result["files_deleted"] == 3
        assert result["files_kept"] == 2
        assert len(result["sessions_deleted"]) == 3
        assert result["bytes_freed"] > 0

        # Verify correct files deleted (oldest 3)
        for old_session in sessions[:3]:
            assert old_session in result["sessions_deleted"]

        # Verify remaining files
        remaining_files = activity_logger.list_log_files()
        assert len(remaining_files) == 2

    def test_rotate_never_deletes_current_session(self, mock_config, monkeypatch):
        """Test that current active session is never deleted."""
        sessions = [
            "session_20251103_100000",
            "session_20251103_110000",
            "session_20251103_120000",
        ]

        for session_id in sessions:
            create_dummy_log_file(mock_config.logs_dir, session_id)
            time.sleep(0.01)

        # Mock current session to be the newest
        current_session = sessions[2]
        monkeypatch.setattr(activity_logger, "get_current_session_id", lambda: current_session)

        # Keep only 1 file (should keep current + 0 previous)
        result = activity_logger.rotate_logs(retention_count=1)

        # Should delete 2 older files but NOT current
        assert result["files_deleted"] == 2
        assert result["files_kept"] == 1
        assert current_session not in result["sessions_deleted"]

        # Verify current session still exists
        remaining_files = activity_logger.list_log_files()
        assert len(remaining_files) == 1
        assert remaining_files[0]["session_id"] == current_session

    def test_rotate_with_custom_retention_count(self, mock_config):
        """Test rotation with custom retention count."""
        sessions = [f"session_2025110{i}_120000" for i in range(10)]

        for session_id in sessions:
            create_dummy_log_file(mock_config.logs_dir, session_id)
            time.sleep(0.01)

        # Keep 5 files
        result = activity_logger.rotate_logs(retention_count=5)

        assert result["files_deleted"] == 5
        assert result["files_kept"] == 5

        remaining_files = activity_logger.list_log_files()
        assert len(remaining_files) == 5

    def test_rotate_uses_config_default(self, mock_config):
        """Test that rotation uses config default when not specified."""
        mock_config.activity_log_retention_count = 3

        sessions = [f"session_2025110{i}_120000" for i in range(5)]
        for session_id in sessions:
            create_dummy_log_file(mock_config.logs_dir, session_id)
            time.sleep(0.01)

        # Don't specify retention_count, should use config default (3)
        result = activity_logger.rotate_logs()

        assert result["files_deleted"] == 2
        assert result["files_kept"] == 3


# ============================================================================
# Test Automatic Rotation on Startup
# ============================================================================


class TestAutomaticRotation:
    """Tests for automatic log rotation on startup."""

    def test_rotation_on_initialize(self, mock_config, monkeypatch):
        """Test that rotation happens automatically on initialize()."""
        # Create old log files
        sessions = [
            "session_20251103_100000",
            "session_20251103_110000",
            "session_20251103_120000",
        ]

        for session_id in sessions:
            create_dummy_log_file(mock_config.logs_dir, session_id)
            time.sleep(0.01)

        mock_config.activity_log_retention_count = 2

        # Initialize should trigger rotation
        activity_logger.initialize(session_id="session_20251103_130000")

        # Wait for rotation to complete
        time.sleep(0.1)

        # Should have deleted 1 old file, kept 2 + new current session
        files = activity_logger.list_log_files()

        # Note: New session file may not exist yet (not written to)
        # But old files should be cleaned up
        assert len(files) <= 3  # At most: 2 kept + 1 current

        # Oldest session should be deleted
        remaining_sessions = [f["session_id"] for f in files]
        assert sessions[0] not in remaining_sessions

        # Cleanup
        activity_logger.shutdown()

    def test_rotation_failure_does_not_break_initialization(self, mock_config, monkeypatch):
        """Test that rotation failure doesn't prevent logger initialization."""
        # Create log file
        create_dummy_log_file(mock_config.logs_dir, "session_20251103_120000")

        # Mock rotate_logs to raise exception
        def failing_rotate(*args, **kwargs):
            raise RuntimeError("Rotation failed!")

        original_rotate = activity_logger.rotate_logs
        monkeypatch.setattr(activity_logger, "rotate_logs", failing_rotate)

        # Initialize should succeed despite rotation failure
        activity_logger.initialize(session_id="session_20251103_130000")

        assert activity_logger._initialized is True
        assert activity_logger.get_current_session_id() == "session_20251103_130000"

        # Cleanup
        activity_logger.shutdown()


# ============================================================================
# Test Edge Cases and Error Handling
# ============================================================================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_rotation_with_zero_retention(self, mock_config):
        """Test rotation with retention_count=0 (should keep nothing except current)."""
        sessions = [
            "session_20251103_100000",
            "session_20251103_110000",
        ]

        for session_id in sessions:
            create_dummy_log_file(mock_config.logs_dir, session_id)
            time.sleep(0.01)

        # Retention count of 0 is invalid, should use max(0, count-1) = 0
        result = activity_logger.rotate_logs(retention_count=0)

        # All files should be deleted (no current session active)
        assert result["files_deleted"] == 2
        assert result["files_kept"] == 0

    def test_rotation_with_permission_error(self, mock_config, monkeypatch):
        """Test rotation handles permission errors gracefully."""
        session_id = "session_20251103_120000"
        file_path = create_dummy_log_file(mock_config.logs_dir, session_id)

        # Mock unlink to raise permission error
        original_unlink = Path.unlink

        def failing_unlink(self, *args, **kwargs):
            if self == file_path:
                raise PermissionError("Permission denied")
            return original_unlink(self, *args, **kwargs)

        monkeypatch.setattr(Path, "unlink", failing_unlink)

        # Rotation should handle error gracefully
        result = activity_logger.rotate_logs(retention_count=0)

        assert result["files_deleted"] == 0
        assert len(result["errors"]) == 1
        assert "Permission denied" in result["errors"][0]

    def test_list_files_with_corrupted_filenames(self, mock_config):
        """Test that corrupted/invalid log filenames are skipped."""
        # Create valid log file
        create_dummy_log_file(mock_config.logs_dir, "session_20251103_120000")

        # Create files with invalid names
        (mock_config.logs_dir / "invalid.jsonl").write_text("{}")
        (mock_config.logs_dir / "session_invalid.jsonl.gz").write_text("data")
        (mock_config.logs_dir / "test.txt").write_text("test")

        files = activity_logger.list_log_files()

        # Should only find the valid log file
        assert len(files) == 1
        assert files[0]["session_id"] == "session_20251103_120000"

    def test_stats_includes_current_session(self, mock_config, monkeypatch):
        """Test that stats includes current session ID."""
        current_session = "session_20251103_150000"
        monkeypatch.setattr(activity_logger, "get_current_session_id", lambda: current_session)

        create_dummy_log_file(mock_config.logs_dir, "session_20251103_120000")

        stats = activity_logger.get_log_file_stats()

        assert stats["current_session"] == current_session
