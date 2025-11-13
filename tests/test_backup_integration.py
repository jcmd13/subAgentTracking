"""
Tests for Backup Integration with Activity Logger

Tests automatic backup triggers and event logging.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from src.core.backup_integration import (
    trigger_automatic_backup,
    should_backup_on_handoff,
    backup_on_shutdown,
    backup_on_handoff,
)


@pytest.fixture
def mock_config(monkeypatch):
    """Mock configuration."""
    from src.core.config import Config

    config = Config()
    config.backup_enabled = True
    config.backup_on_handoff = True
    config.backup_on_token_limit = True

    def mock_get_config():
        return config

    monkeypatch.setattr("src.core.backup_integration.get_config", mock_get_config)
    monkeypatch.setattr("src.core.activity_logger.get_config", mock_get_config)

    return config


@pytest.fixture
def mock_activity_logger(monkeypatch):
    """Mock activity logger."""
    mock = MagicMock()
    mock.get_current_session_id.return_value = "test_session"
    mock.log_decision.return_value = "evt_001"
    mock.log_agent_invocation.return_value = "evt_002"
    mock.log_validation.return_value = "evt_003"
    mock.log_error.return_value = "evt_004"

    monkeypatch.setattr("src.core.backup_integration.activity_logger", mock)

    return mock


def test_trigger_backup_when_disabled(mock_config, mock_activity_logger):
    """Test that backup is skipped when disabled in config."""
    mock_config.backup_enabled = False

    result = trigger_automatic_backup(reason="test")

    assert result["attempted"] is False
    assert result["success"] is False
    assert result["skipped_reason"] == "backup_disabled_in_config"

    # Should log decision to skip
    mock_activity_logger.log_decision.assert_called_once()


def test_trigger_backup_with_force(mock_config, mock_activity_logger):
    """Test that force=True bypasses config check."""
    mock_config.backup_enabled = False

    with patch("src.core.backup_manager.BackupManager") as MockBackupManager:
        mock_manager = MockBackupManager.return_value
        mock_manager.is_available.return_value = False

        result = trigger_automatic_backup(reason="test", force=True)

        # Should attempt backup even though disabled
        assert result["attempted"] is True


def test_trigger_backup_google_drive_unavailable(mock_config, mock_activity_logger):
    """Test backup when Google Drive API not available."""
    with patch("src.core.backup_manager.BackupManager") as MockBackupManager:
        mock_manager = MockBackupManager.return_value
        mock_manager.is_available.return_value = False

        result = trigger_automatic_backup(reason="test")

        assert result["attempted"] is True
        assert result["success"] is False
        assert result["error"] == "google_drive_not_available"

        # Should log error
        mock_activity_logger.log_error.assert_called_once()


def test_trigger_backup_authentication_failed(mock_config, mock_activity_logger):
    """Test backup when authentication fails."""
    with patch("src.core.backup_manager.BackupManager") as MockBackupManager:
        mock_manager = MockBackupManager.return_value
        mock_manager.is_available.return_value = True
        mock_manager.authenticate.return_value = False

        result = trigger_automatic_backup(reason="test")

        assert result["attempted"] is True
        assert result["success"] is False
        assert result["error"] == "authentication_failed"

        # Should log error
        mock_activity_logger.log_error.assert_called_once()


def test_trigger_backup_success(mock_config, mock_activity_logger):
    """Test successful backup."""
    with patch("src.core.backup_manager.BackupManager") as MockBackupManager:
        mock_manager = MockBackupManager.return_value
        mock_manager.is_available.return_value = True
        mock_manager.authenticate.return_value = True
        mock_manager.backup_session.return_value = {"success": True, "file_id": "backup_123"}

        result = trigger_automatic_backup(reason="test")

        assert result["attempted"] is True
        assert result["success"] is True
        assert result["backup_id"] == "backup_123"

        # Should log validation
        mock_activity_logger.log_validation.assert_called_once()


def test_trigger_backup_failure(mock_config, mock_activity_logger):
    """Test backup failure."""
    with patch("src.core.backup_manager.BackupManager") as MockBackupManager:
        mock_manager = MockBackupManager.return_value
        mock_manager.is_available.return_value = True
        mock_manager.authenticate.return_value = True
        mock_manager.backup_session.return_value = {"success": False, "error": "quota_exceeded"}

        result = trigger_automatic_backup(reason="test")

        assert result["attempted"] is True
        assert result["success"] is False
        assert result["error"] == "quota_exceeded"

        # Should log error
        mock_activity_logger.log_error.assert_called()


def test_should_backup_on_handoff_token_limit(mock_config):
    """Test backup decision for token limit."""
    mock_config.backup_on_token_limit = True

    assert should_backup_on_handoff("token_limit") is True
    assert should_backup_on_handoff("token_limit_approaching") is True

    mock_config.backup_on_token_limit = False
    assert should_backup_on_handoff("token_limit") is False


def test_should_backup_on_handoff_session_end(mock_config):
    """Test backup decision for session end."""
    mock_config.backup_on_handoff = True

    assert should_backup_on_handoff("session_end") is True
    assert should_backup_on_handoff("handoff") is True
    assert should_backup_on_handoff("manual") is True

    mock_config.backup_on_handoff = False
    assert should_backup_on_handoff("session_end") is False


def test_backup_on_shutdown(mock_config, mock_activity_logger):
    """Test backup_on_shutdown convenience function."""
    with patch("src.core.backup_integration.trigger_automatic_backup") as mock_trigger:
        mock_trigger.return_value = {"success": True}

        result = backup_on_shutdown()

        mock_trigger.assert_called_once_with(session_id=None, reason="session_shutdown")


def test_backup_on_handoff_with_check(mock_config, mock_activity_logger):
    """Test backup_on_handoff with reason check."""
    mock_config.backup_on_token_limit = False

    # Should skip because backup_on_token_limit is False
    result = backup_on_handoff(reason="token_limit")

    assert result["attempted"] is False
    assert result["skipped_reason"] == "backup_not_enabled_for_token_limit"


def test_backup_on_handoff_enabled(mock_config, mock_activity_logger):
    """Test backup_on_handoff when enabled."""
    mock_config.backup_on_handoff = True

    with patch("src.core.backup_integration.trigger_automatic_backup") as mock_trigger:
        mock_trigger.return_value = {"success": True}

        result = backup_on_handoff(reason="session_end")

        mock_trigger.assert_called_once_with(session_id=None, reason="handoff_session_end")


def test_backup_logs_all_events(mock_config, mock_activity_logger):
    """Test that backup integration logs all events to tracking system."""
    with patch("src.core.backup_manager.BackupManager") as MockBackupManager:
        mock_manager = MockBackupManager.return_value
        mock_manager.is_available.return_value = True
        mock_manager.authenticate.return_value = True
        mock_manager.backup_session.return_value = {"success": True, "file_id": "backup_456"}

        result = trigger_automatic_backup(reason="integration_test")

        # Should log decision
        assert mock_activity_logger.log_decision.called

        # Should log agent invocation
        assert mock_activity_logger.log_agent_invocation.called

        # Should log validation (success)
        assert mock_activity_logger.log_validation.called
