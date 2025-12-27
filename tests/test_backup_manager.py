"""
Tests for Backup Manager - Google Drive Integration

Tests the backup and restore functionality using mocked Google Drive API.

Test Coverage:
- Authentication and connection testing
- Session backup (archive creation, upload)
- Session restore (download, extraction)
- Error handling (missing credentials, API failures)
- Archive operations (tar.gz creation/extraction)
- Convenience functions
"""

import pytest
import tempfile
import tarfile
import json
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
from typing import Dict, Any

# Import after mocking to avoid ImportError
import sys

sys.modules["google.auth.transport.requests"] = MagicMock()
sys.modules["google.oauth2.credentials"] = MagicMock()
sys.modules["google_auth_oauthlib.flow"] = MagicMock()
sys.modules["googleapiclient.discovery"] = MagicMock()
sys.modules["googleapiclient.http"] = MagicMock()

from src.core import backup_manager
from src.core import config as config_module


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def temp_project_dir():
    """Create temporary directory structure."""
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_path = Path(tmpdir)
        (temp_path / "logs").mkdir()
        (temp_path / "state").mkdir()
        (temp_path / "handoffs").mkdir()
        (temp_path / "analytics").mkdir()
        (temp_path / "credentials").mkdir()
        yield temp_path


@pytest.fixture
def mock_config(temp_project_dir, monkeypatch):
    """Mock configuration with temp directories."""

    class MockConfig:
        def __init__(self):
            self.project_root = temp_project_dir
            self.logs_dir = temp_project_dir / "logs"
            self.state_dir = temp_project_dir / "state"
            self.handoffs_dir = temp_project_dir / "handoffs"
            self.analytics_dir = temp_project_dir / "analytics"
            self.credentials_dir = temp_project_dir / "credentials"
            self.backup_enabled = True
            self.backup_on_handoff = True
            self.backup_async = True
            self.google_drive_folder_name = "SubAgentTracking"

    test_config = MockConfig()
    monkeypatch.setattr(config_module, "get_config", lambda: test_config)
    monkeypatch.setattr("src.core.backup_manager.get_config", lambda: test_config)

    yield test_config


@pytest.fixture
def mock_google_drive_service():
    """Mock Google Drive API service."""
    service = MagicMock()

    # Mock files().list() for folder search
    list_result = MagicMock()
    list_result.execute.return_value = {"files": [{"id": "folder_123", "name": "SubAgentTracking"}]}
    service.files().list.return_value = list_result

    # Mock files().create() for folder creation
    create_result = MagicMock()
    create_result.execute.return_value = {"id": "file_456"}
    service.files().create.return_value = create_result

    # Mock files().get_media() for download
    get_media_result = MagicMock()
    service.files().get_media.return_value = get_media_result

    return service


def create_test_session_files(config: Any, session_id: str):
    """
    Create test session files for backup testing.

    Args:
        config: Mock config object
        session_id: Session ID
    """
    # Create activity log
    log_path = config.logs_dir / f"{session_id}.jsonl.gz"
    import gzip

    with gzip.open(log_path, "wt") as f:
        f.write('{"event_type":"test"}\n')

    # Create snapshots
    snapshot1_path = config.state_dir / f"{session_id}_snap001.json.gz"
    with gzip.open(snapshot1_path, "wt") as f:
        f.write('{"snapshot_id":"snap_001"}')

    snapshot2_path = config.state_dir / f"{session_id}_snap002.json.gz"
    with gzip.open(snapshot2_path, "wt") as f:
        f.write('{"snapshot_id":"snap_002"}')

    # Create handoff
    handoff_path = config.handoffs_dir / f"{session_id}_handoff.md"
    handoff_path.write_text("# Session Handoff\nSession completed successfully")

    # Create analytics DB
    analytics_path = config.analytics_dir / "tracking.db"
    analytics_path.write_text("fake db content")


# ============================================================================
# Test BackupManager Initialization
# ============================================================================


class TestBackupManagerInit:
    """Tests for BackupManager initialization."""

    def test_init_basic(self, mock_config):
        """Test basic initialization."""
        # Mock GOOGLE_DRIVE_AVAILABLE
        with patch.object(backup_manager, "GOOGLE_DRIVE_AVAILABLE", True):
            manager = backup_manager.BackupManager()

            assert manager.config == mock_config
            assert manager.service is None
            assert manager.drive_folder_id is None

    def test_is_available_when_enabled(self, mock_config):
        """Test is_available returns True when properly configured."""
        token_path = mock_config.credentials_dir / "google_drive_token.pickle"
        token_path.write_bytes(b"token")
        with patch.object(backup_manager, "GOOGLE_DRIVE_AVAILABLE", True):
            manager = backup_manager.BackupManager()
            assert manager.is_available() is True

    def test_is_available_when_disabled(self, mock_config):
        """Test is_available returns False when disabled."""
        mock_config.backup_enabled = False
        token_path = mock_config.credentials_dir / "google_drive_token.pickle"
        token_path.write_bytes(b"token")

        with patch.object(backup_manager, "GOOGLE_DRIVE_AVAILABLE", True):
            manager = backup_manager.BackupManager()
            assert manager.is_available() is False

    def test_is_available_when_api_not_installed(self, mock_config):
        """Test is_available returns False when Google Drive API not installed."""
        token_path = mock_config.credentials_dir / "google_drive_token.pickle"
        token_path.write_bytes(b"token")
        with patch.object(backup_manager, "GOOGLE_DRIVE_AVAILABLE", False):
            manager = backup_manager.BackupManager()
            assert manager.is_available() is False

    def test_is_available_without_token(self, mock_config):
        """Test is_available returns False when token is missing."""
        with patch.object(backup_manager, "GOOGLE_DRIVE_AVAILABLE", True):
            manager = backup_manager.BackupManager()
            assert manager.is_available() is False


# ============================================================================
# Test Authentication
# ============================================================================


class TestAuthentication:
    """Tests for OAuth 2.0 authentication."""

    def test_authenticate_no_credentials_file(self, mock_config):
        """Test authentication fails when credentials file missing."""
        with patch.object(backup_manager, "GOOGLE_DRIVE_AVAILABLE", True):
            manager = backup_manager.BackupManager()
            result = manager.authenticate()

            assert result is False
            assert manager.service is None

    def test_authenticate_with_existing_token(self, mock_config, mock_google_drive_service):
        """Test authentication with existing valid token."""
        # Create credentials file
        credentials_path = mock_config.credentials_dir / "google_drive_credentials.json"
        credentials_path.write_text('{"installed":{"client_id":"test","client_secret":"secret"}}')

        # Create token file with mock credentials (can't pickle MagicMock, so use patch instead)
        with patch.object(backup_manager, "GOOGLE_DRIVE_AVAILABLE", True):
            with patch("src.core.backup_manager.build", return_value=mock_google_drive_service):
                with patch("src.core.backup_manager.pickle.load") as mock_load:
                    with patch("src.core.backup_manager.pickle.dump"):
                        # Mock valid credentials
                        mock_creds = MagicMock()
                        mock_creds.valid = True
                        mock_load.return_value = mock_creds

                        # Create empty token file
                        token_path = mock_config.credentials_dir / "google_drive_token.pickle"
                        token_path.write_bytes(b"fake_pickle_data")

                        manager = backup_manager.BackupManager()
                        result = manager.authenticate()

                        assert result is True
                        assert manager.service is not None

    def test_authenticate_api_not_available(self, mock_config):
        """Test authentication fails when API not available."""
        with patch.object(backup_manager, "GOOGLE_DRIVE_AVAILABLE", False):
            manager = backup_manager.BackupManager()
            result = manager.authenticate()

            assert result is False


# ============================================================================
# Test Archive Operations
# ============================================================================


class TestArchiveOperations:
    """Tests for session archive creation and extraction."""

    def test_create_session_archive(self, mock_config):
        """Test creating session archive."""
        session_id = "session_20251103_120000"
        create_test_session_files(mock_config, session_id)

        with patch.object(backup_manager, "GOOGLE_DRIVE_AVAILABLE", True):
            manager = backup_manager.BackupManager()
            archive_path = manager._create_session_archive(session_id, compress=True)

            assert archive_path is not None
            assert archive_path.exists()
            assert archive_path.suffix == ".gz"

            # Verify archive contents
            with tarfile.open(archive_path, "r:gz") as tar:
                names = tar.getnames()
                assert any("activity.jsonl" in name for name in names)
                assert any("snapshots" in name for name in names)
                assert any("handoff.md" in name for name in names)

            # Cleanup
            archive_path.unlink()

    def test_create_archive_uncompressed(self, mock_config):
        """Test creating uncompressed archive."""
        session_id = "session_20251103_130000"
        create_test_session_files(mock_config, session_id)

        with patch.object(backup_manager, "GOOGLE_DRIVE_AVAILABLE", True):
            manager = backup_manager.BackupManager()
            archive_path = manager._create_session_archive(session_id, compress=False)

            assert archive_path is not None
            assert archive_path.exists()

            # Cleanup
            archive_path.unlink()

    def test_create_archive_missing_files(self, mock_config):
        """Test creating archive when some files are missing."""
        session_id = "session_20251103_140000"

        # Only create log file, no snapshots/handoff
        log_path = mock_config.logs_dir / f"{session_id}.jsonl.gz"
        import gzip

        with gzip.open(log_path, "wt") as f:
            f.write('{"event_type":"test"}\n')

        with patch.object(backup_manager, "GOOGLE_DRIVE_AVAILABLE", True):
            manager = backup_manager.BackupManager()
            archive_path = manager._create_session_archive(session_id)

            assert archive_path is not None
            assert archive_path.exists()

            # Cleanup
            archive_path.unlink()

    def test_extract_session_archive(self, mock_config):
        """Test extracting session archive."""
        session_id = "session_20251103_150000"
        create_test_session_files(mock_config, session_id)

        with patch.object(backup_manager, "GOOGLE_DRIVE_AVAILABLE", True):
            manager = backup_manager.BackupManager()

            # Create archive
            archive_path = manager._create_session_archive(session_id)
            assert archive_path is not None

            # Clear original files
            for file in mock_config.logs_dir.glob(f"{session_id}*"):
                file.unlink()
            for file in mock_config.state_dir.glob(f"{session_id}*"):
                file.unlink()
            for file in mock_config.handoffs_dir.glob(f"{session_id}*"):
                file.unlink()

            # Extract archive
            restored_files = manager._extract_session_archive(archive_path, session_id)

            assert len(restored_files) > 0
            # Check that files were restored to the correct locations
            assert any(str(mock_config.logs_dir) in str(f) for f in restored_files)

            # Verify activity log was restored
            restored_log = mock_config.logs_dir / f"{session_id}.jsonl.gz"
            assert restored_log.exists()

            # Cleanup
            archive_path.unlink()


# ============================================================================
# Test Backup Operations
# ============================================================================


class TestBackupOperations:
    """Tests for session backup functionality."""

    def test_backup_session_not_available(self, mock_config):
        """Test backup fails when not available."""
        with patch.object(backup_manager, "GOOGLE_DRIVE_AVAILABLE", False):
            manager = backup_manager.BackupManager()
            result = manager.backup_session("session_20251103_120000")

            assert result["success"] is False
            assert "not available" in result["error"].lower()

    def test_backup_session_success(self, mock_config, mock_google_drive_service):
        """Test successful session backup."""
        session_id = "session_20251103_120000"
        create_test_session_files(mock_config, session_id)

        # Create credentials
        credentials_path = mock_config.credentials_dir / "google_drive_credentials.json"
        credentials_path.write_text('{"installed":{"client_id":"test"}}')
        token_path = mock_config.credentials_dir / "google_drive_token.pickle"
        token_path.write_bytes(b"token")

        with patch.object(backup_manager, "GOOGLE_DRIVE_AVAILABLE", True):
            with patch("src.core.backup_manager.build", return_value=mock_google_drive_service):
                with patch("src.core.backup_manager.pickle"):
                    manager = backup_manager.BackupManager()
                    manager.authenticate()
                    manager.service = mock_google_drive_service
                    manager.drive_folder_id = "folder_123"

                    result = manager.backup_session(session_id)

                    assert result["session_id"] == session_id
                    assert result["success"] is True
                    assert result["file_id"] is not None
                    assert result["size_bytes"] > 0
                    assert result["duration_ms"] >= 0

    def test_backup_session_no_session_id(self, mock_config):
        """Test backup fails when no session ID provided."""
        with patch.object(backup_manager, "GOOGLE_DRIVE_AVAILABLE", True):
            with patch("src.core.activity_logger.get_current_session_id", return_value=None):
                manager = backup_manager.BackupManager()
                manager.service = MagicMock()  # Mock authenticated
                result = manager.backup_session()

                assert result["success"] is False
                assert "no session" in result["error"].lower()


# ============================================================================
# Test Restore Operations
# ============================================================================


class TestRestoreOperations:
    """Tests for session restore functionality."""

    def test_restore_session_not_available(self, mock_config):
        """Test restore fails when not available."""
        with patch.object(backup_manager, "GOOGLE_DRIVE_AVAILABLE", False):
            manager = backup_manager.BackupManager()
            result = manager.restore_session("session_20251103_120000")

            assert result["success"] is False
            assert "not available" in result["error"].lower()

    def test_restore_session_not_found(self, mock_config, mock_google_drive_service):
        """Test restore fails when session not found in Drive."""
        session_id = "session_20251103_999999"

        # Mock no files found
        list_result = MagicMock()
        list_result.execute.return_value = {"files": []}
        mock_google_drive_service.files().list.return_value = list_result

        with patch.object(backup_manager, "GOOGLE_DRIVE_AVAILABLE", True):
            manager = backup_manager.BackupManager()
            manager.service = mock_google_drive_service
            manager.drive_folder_id = "folder_123"

            result = manager.restore_session(session_id)

            assert result["success"] is False
            assert "not found" in result["error"].lower()


# ============================================================================
# Test Convenience Functions
# ============================================================================


class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""

    def test_test_connection_not_available(self, mock_config):
        """Test test_connection returns False when not available."""
        with patch.object(backup_manager, "GOOGLE_DRIVE_AVAILABLE", False):
            result = backup_manager.test_connection()
            assert result is False

    def test_backup_current_session(self, mock_config):
        """Test backup_current_session convenience function."""
        with patch.object(backup_manager, "GOOGLE_DRIVE_AVAILABLE", False):
            result = backup_manager.backup_current_session()
            assert result["success"] is False

    def test_list_available_backups_not_available(self, mock_config):
        """Test list_available_backups returns empty when not available."""
        with patch.object(backup_manager, "GOOGLE_DRIVE_AVAILABLE", False):
            result = backup_manager.list_available_backups()
            assert result == []


# ============================================================================
# Test Error Handling
# ============================================================================


class TestErrorHandling:
    """Tests for error handling and edge cases."""

    def test_upload_with_no_service(self, mock_config):
        """Test upload fails gracefully when service not initialized."""
        with patch.object(backup_manager, "GOOGLE_DRIVE_AVAILABLE", True):
            manager = backup_manager.BackupManager()
            # Don't authenticate, service is None

            import tempfile

            temp_file = Path(tempfile.gettempdir()) / "test.tar.gz"
            temp_file.write_text("test content")

            result = manager._upload_to_drive(temp_file, "test.tar.gz", "folder_123")

            assert result is None

            temp_file.unlink()

    def test_download_with_no_service(self, mock_config):
        """Test download fails gracefully when service not initialized."""
        with patch.object(backup_manager, "GOOGLE_DRIVE_AVAILABLE", True):
            manager = backup_manager.BackupManager()
            # Don't authenticate, service is None

            import tempfile

            temp_file = Path(tempfile.gettempdir()) / "download.tar.gz"

            result = manager._download_from_drive("file_123", temp_file)

            assert result is False

    def test_find_file_with_no_service(self, mock_config):
        """Test find file fails gracefully when service not initialized."""
        with patch.object(backup_manager, "GOOGLE_DRIVE_AVAILABLE", True):
            manager = backup_manager.BackupManager()
            # Don't authenticate, service is None

            result = manager._find_file_in_drive("test.tar.gz")

            assert result is None

    def test_list_backups_with_no_service(self, mock_config):
        """Test list backups returns empty when service not initialized."""
        with patch.object(backup_manager, "GOOGLE_DRIVE_AVAILABLE", True):
            manager = backup_manager.BackupManager()
            result = manager.list_backups()

            assert result == []


# ============================================================================
# Test Google Drive Folder Management
# ============================================================================


class TestFolderManagement:
    """Tests for Google Drive folder creation and management."""

    def test_get_or_create_folder_existing(self, mock_config, mock_google_drive_service):
        """Test getting existing folder."""
        with patch.object(backup_manager, "GOOGLE_DRIVE_AVAILABLE", True):
            manager = backup_manager.BackupManager()
            manager.service = mock_google_drive_service

            folder_id = manager._get_or_create_folder("SubAgentTracking")

            assert folder_id == "folder_123"

    def test_get_or_create_folder_new(self, mock_config, mock_google_drive_service):
        """Test creating new folder when it doesn't exist."""
        # Mock no existing folder
        list_result = MagicMock()
        list_result.execute.return_value = {"files": []}
        mock_google_drive_service.files().list.return_value = list_result

        with patch.object(backup_manager, "GOOGLE_DRIVE_AVAILABLE", True):
            manager = backup_manager.BackupManager()
            manager.service = mock_google_drive_service

            folder_id = manager._get_or_create_folder("NewFolder")

            assert folder_id == "file_456"

    def test_get_or_create_folder_no_service(self, mock_config):
        """Test folder creation fails when no service."""
        with patch.object(backup_manager, "GOOGLE_DRIVE_AVAILABLE", True):
            manager = backup_manager.BackupManager()
            # Don't set service

            folder_id = manager._get_or_create_folder("TestFolder")

            assert folder_id is None
