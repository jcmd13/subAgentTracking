"""
Tests for src.core.config module

Tests cover:
- Default configuration
- Environment variable overrides
- Path generation methods
- Validation logic
- Configuration dictionary conversion
- Singleton pattern
- Directory creation
"""

import os
import tempfile
import shutil
from pathlib import Path
import pytest

from src.core.config import (
    Config,
    get_config,
    reset_config,
    is_backup_enabled,
    is_analytics_enabled,
    get_snapshot_triggers,
    get_performance_budgets,
)


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path)


@pytest.fixture
def clean_config():
    """Reset global configuration before and after each test."""
    reset_config()
    yield
    reset_config()


@pytest.fixture
def clean_env():
    """Clean environment variables before and after each test."""
    env_vars = [
        "SUBAGENT_TRACKING_ROOT",
        "SUBAGENT_SNAPSHOT_AGENT_COUNT",
        "SUBAGENT_SNAPSHOT_TOKEN_COUNT",
        "SUBAGENT_BACKUP_ENABLED",
        "SUBAGENT_ANALYTICS_ENABLED",
        "SUBAGENT_LOG_LATENCY_MS",
        "SUBAGENT_STRICT_MODE",
    ]

    # Save original values
    original_values = {var: os.environ.get(var) for var in env_vars}

    # Clear all
    for var in env_vars:
        os.environ.pop(var, None)

    yield

    # Restore original values
    for var, value in original_values.items():
        if value is not None:
            os.environ[var] = value
        else:
            os.environ.pop(var, None)


class TestConfigDefaults:
    """Test default configuration values."""

    def test_default_paths(self, temp_dir, clean_config):
        """Test that default paths are correctly set."""
        config = Config()
        config.project_root = temp_dir
        config.claude_dir = temp_dir / ".claude"
        config._update_tracking_dirs()
        config._ensure_directories()

        assert config.logs_dir == temp_dir / ".claude" / "logs"
        assert config.state_dir == temp_dir / ".claude" / "state"
        assert config.analytics_dir == temp_dir / ".claude" / "analytics"
        assert config.credentials_dir == temp_dir / ".claude" / "credentials"
        assert config.handoffs_dir == temp_dir / ".claude" / "handoffs"

    def test_default_settings(self, clean_config):
        """Test that default settings are sensible."""
        config = Config()

        # Activity log settings
        assert config.activity_log_enabled is True
        assert config.activity_log_compression is True
        assert config.activity_log_retention_count == 2

        # Snapshot settings
        assert config.snapshot_enabled is True
        assert config.snapshot_trigger_agent_count == 10
        assert config.snapshot_trigger_token_count == 20000
        assert config.snapshot_compression is True

        # Backup settings
        assert config.backup_enabled is False  # Disabled by default
        assert config.backup_on_handoff is True
        assert config.backup_async is True

        # Analytics settings
        assert config.analytics_enabled is True
        assert config.analytics_db_name == "tracking.db"

    def test_default_performance_budgets(self, clean_config):
        """Test that performance budgets are correctly set."""
        config = Config()

        assert config.event_logging_max_latency_ms == 1.0
        assert config.snapshot_creation_max_latency_ms == 100.0
        assert config.query_max_latency_ms == 10.0
        assert config.backup_max_duration_minutes == 2.0

    def test_default_token_threshold(self, clean_config):
        """Test token limit warning threshold."""
        config = Config()
        assert config.token_limit_warning_threshold == 0.9


class TestEnvironmentVariables:
    """Test environment variable overrides."""

    def test_snapshot_agent_count_override(self, clean_env, clean_config):
        """Test SUBAGENT_SNAPSHOT_AGENT_COUNT override."""
        os.environ["SUBAGENT_SNAPSHOT_AGENT_COUNT"] = "15"
        config = Config()
        assert config.snapshot_trigger_agent_count == 15

    def test_snapshot_token_count_override(self, clean_env, clean_config):
        """Test SUBAGENT_SNAPSHOT_TOKEN_COUNT override."""
        os.environ["SUBAGENT_SNAPSHOT_TOKEN_COUNT"] = "30000"
        config = Config()
        assert config.snapshot_trigger_token_count == 30000

    def test_backup_enabled_override(self, clean_env, clean_config):
        """Test SUBAGENT_BACKUP_ENABLED override."""
        os.environ["SUBAGENT_BACKUP_ENABLED"] = "true"
        config = Config()
        assert config.backup_enabled is True

        reset_config()
        os.environ["SUBAGENT_BACKUP_ENABLED"] = "false"
        config = Config()
        assert config.backup_enabled is False

    def test_analytics_enabled_override(self, clean_env, clean_config):
        """Test SUBAGENT_ANALYTICS_ENABLED override."""
        os.environ["SUBAGENT_ANALYTICS_ENABLED"] = "false"
        config = Config()
        assert config.analytics_enabled is False

    def test_log_latency_override(self, clean_env, clean_config):
        """Test SUBAGENT_LOG_LATENCY_MS override."""
        os.environ["SUBAGENT_LOG_LATENCY_MS"] = "2.5"
        config = Config()
        assert config.event_logging_max_latency_ms == 2.5

    def test_strict_mode_override(self, clean_env, clean_config):
        """Test SUBAGENT_STRICT_MODE override."""
        os.environ["SUBAGENT_STRICT_MODE"] = "yes"
        config = Config()
        assert config.strict_mode is True


class TestPathGeneration:
    """Test path generation methods."""

    def test_activity_log_path(self, temp_dir, clean_config):
        """Test activity log path generation."""
        config = Config()
        config.project_root = temp_dir
        config.claude_dir = temp_dir / ".claude"
        config._update_tracking_dirs()
        config._ensure_directories()

        log_path = config.activity_log_path
        assert log_path.parent == config.logs_dir
        assert log_path.suffix == ".jsonl"
        assert "session_" in log_path.stem

    def test_analytics_db_path(self, temp_dir, clean_config):
        """Test analytics database path."""
        config = Config()
        config.project_root = temp_dir
        config.claude_dir = temp_dir / ".claude"
        config._update_tracking_dirs()
        config._ensure_directories()

        db_path = config.analytics_db_path
        assert db_path == config.analytics_dir / "tracking.db"

    def test_snapshot_path(self, temp_dir, clean_config):
        """Test snapshot path generation."""
        config = Config()
        config.project_root = temp_dir
        config.claude_dir = temp_dir / ".claude"
        config._update_tracking_dirs()
        config._ensure_directories()

        session_id = "session_20251102_153000"
        snapshot_path = config.get_snapshot_path(session_id, 1)
        assert snapshot_path == config.state_dir / "session_20251102_153000_snap001.json"

        snapshot_path_10 = config.get_snapshot_path(session_id, 10)
        assert snapshot_path_10 == config.state_dir / "session_20251102_153000_snap010.json"

    def test_handoff_path(self, temp_dir, clean_config):
        """Test handoff summary path generation."""
        config = Config()
        config.project_root = temp_dir
        config.claude_dir = temp_dir / ".claude"
        config._update_tracking_dirs()
        config._ensure_directories()

        session_id = "session_20251102_153000"
        handoff_path = config.get_handoff_path(session_id)
        assert handoff_path == config.handoffs_dir / "session_20251102_153000_handoff.md"

    def test_credentials_path(self, temp_dir, clean_config):
        """Test credentials path generation."""
        config = Config()
        config.project_root = temp_dir
        config.claude_dir = temp_dir / ".claude"
        config._update_tracking_dirs()
        config._ensure_directories()

        creds_path = config.get_credentials_path("google_drive")
        assert creds_path == config.credentials_dir / "google_drive_credentials.json"

    def test_token_path(self, temp_dir, clean_config):
        """Test token path generation."""
        config = Config()
        config.project_root = temp_dir
        config.claude_dir = temp_dir / ".claude"
        config._update_tracking_dirs()
        config._ensure_directories()

        token_path = config.get_token_path("google_drive")
        assert token_path == config.credentials_dir / "google_drive_token.json"


class TestValidation:
    """Test configuration validation."""

    def test_valid_configuration(self, temp_dir, clean_config):
        """Test that default configuration is valid."""
        config = Config()
        config.project_root = temp_dir
        config.claude_dir = temp_dir / ".claude"
        config._update_tracking_dirs()
        config._ensure_directories()

        is_valid, errors = config.validate()
        assert is_valid is True
        assert len(errors) == 0

    def test_invalid_snapshot_agent_count(self, temp_dir, clean_config):
        """Test validation with invalid snapshot agent count."""
        config = Config()
        config.project_root = temp_dir
        config.claude_dir = temp_dir / ".claude"
        config._update_tracking_dirs()
        config._ensure_directories()
        config.snapshot_trigger_agent_count = 0

        is_valid, errors = config.validate()
        assert is_valid is False
        assert any("snapshot_trigger_agent_count" in error for error in errors)

    def test_invalid_snapshot_token_count(self, temp_dir, clean_config):
        """Test validation with invalid snapshot token count."""
        config = Config()
        config.project_root = temp_dir
        config.claude_dir = temp_dir / ".claude"
        config._update_tracking_dirs()
        config._ensure_directories()
        config.snapshot_trigger_token_count = 500

        is_valid, errors = config.validate()
        assert is_valid is False
        assert any("snapshot_trigger_token_count" in error for error in errors)

    def test_invalid_latency_budget(self, temp_dir, clean_config):
        """Test validation with invalid latency budget."""
        config = Config()
        config.project_root = temp_dir
        config.claude_dir = temp_dir / ".claude"
        config._update_tracking_dirs()
        config._ensure_directories()
        config.event_logging_max_latency_ms = 0.05

        is_valid, errors = config.validate()
        assert is_valid is False
        assert any("event_logging_max_latency_ms" in error for error in errors)

    def test_invalid_token_threshold(self, temp_dir, clean_config):
        """Test validation with invalid token threshold."""
        config = Config()
        config.project_root = temp_dir
        config.claude_dir = temp_dir / ".claude"
        config._update_tracking_dirs()
        config._ensure_directories()
        config.token_limit_warning_threshold = 1.5

        is_valid, errors = config.validate()
        assert is_valid is False
        assert any("token_limit_warning_threshold" in error for error in errors)

    def test_strict_mode_raises_on_invalid(self, temp_dir, clean_config):
        """Test that strict mode raises ValueError on invalid config."""
        config = Config()
        config.project_root = temp_dir
        config.claude_dir = temp_dir / ".claude"
        config._update_tracking_dirs()
        config._ensure_directories()
        config.strict_mode = True
        config.snapshot_trigger_agent_count = 0

        with pytest.raises(ValueError):
            config.validate()
            if not config.validate()[0]:
                raise ValueError("Invalid configuration")


class TestConfigurationDict:
    """Test configuration dictionary conversion."""

    def test_to_dict(self, temp_dir, clean_config):
        """Test conversion to dictionary."""
        config = Config()
        config.project_root = temp_dir
        config.claude_dir = temp_dir / ".claude"
        config._update_tracking_dirs()
        config._ensure_directories()

        config_dict = config.to_dict()

        assert isinstance(config_dict, dict)
        assert "project_root" in config_dict
        assert "activity_log_enabled" in config_dict
        assert "snapshot_trigger_agent_count" in config_dict
        assert isinstance(config_dict["project_root"], str)

    def test_dict_contains_all_settings(self, temp_dir, clean_config):
        """Test that dictionary contains all important settings."""
        config = Config()
        config.project_root = temp_dir
        config.claude_dir = temp_dir / ".claude"
        config._update_tracking_dirs()
        config._ensure_directories()

        config_dict = config.to_dict()

        required_keys = [
            "logs_dir",
            "state_dir",
            "analytics_dir",
            "snapshot_trigger_agent_count",
            "snapshot_trigger_token_count",
            "event_logging_max_latency_ms",
            "backup_enabled",
        ]

        for key in required_keys:
            assert key in config_dict


class TestSingletonPattern:
    """Test global configuration singleton."""

    def test_get_config_returns_same_instance(self, clean_config):
        """Test that get_config returns the same instance."""
        config1 = get_config()
        config2 = get_config()
        assert config1 is config2

    def test_reset_config(self, clean_config):
        """Test that reset_config creates new instance."""
        config1 = get_config()
        reset_config()
        config2 = get_config()
        assert config1 is not config2

    def test_reload_config(self, clean_env, clean_config):
        """Test that reload=True reloads from environment."""
        config1 = get_config()
        assert config1.snapshot_trigger_agent_count == 10

        os.environ["SUBAGENT_SNAPSHOT_AGENT_COUNT"] = "25"
        config2 = get_config(reload=True)
        assert config2.snapshot_trigger_agent_count == 25


class TestConvenienceFunctions:
    """Test convenience functions."""

    def test_is_backup_enabled(self, clean_config):
        """Test is_backup_enabled function."""
        assert is_backup_enabled() is False  # Default is disabled

    def test_is_analytics_enabled(self, clean_config):
        """Test is_analytics_enabled function."""
        assert is_analytics_enabled() is True  # Default is enabled

    def test_get_snapshot_triggers(self, clean_config):
        """Test get_snapshot_triggers function."""
        agent_count, token_count = get_snapshot_triggers()
        assert agent_count == 10
        assert token_count == 20000

    def test_get_performance_budgets(self, clean_config):
        """Test get_performance_budgets function."""
        budgets = get_performance_budgets()
        assert "event_logging_ms" in budgets
        assert "snapshot_creation_ms" in budgets
        assert budgets["event_logging_ms"] == 1.0
        assert budgets["snapshot_creation_ms"] == 100.0


class TestDirectoryCreation:
    """Test automatic directory creation."""

    def test_directories_created_automatically(self, temp_dir, clean_config):
        """Test that directories are created automatically."""
        config = Config()
        config.project_root = temp_dir
        config.claude_dir = temp_dir / ".claude"
        config._update_tracking_dirs()
        config._ensure_directories()

        assert config.logs_dir.exists()
        assert config.state_dir.exists()
        assert config.analytics_dir.exists()
        assert config.credentials_dir.exists()
        assert config.handoffs_dir.exists()

    def test_gitkeep_files_created(self, temp_dir, clean_config):
        """Test that .gitkeep files are created in empty directories."""
        config = Config()
        config.project_root = temp_dir
        config.claude_dir = temp_dir / ".claude"
        config._update_tracking_dirs()
        config._ensure_directories()

        assert (config.logs_dir / ".gitkeep").exists()
        assert (config.state_dir / ".gitkeep").exists()
        assert (config.analytics_dir / ".gitkeep").exists()
        assert (config.credentials_dir / ".gitkeep").exists()
        assert (config.handoffs_dir / ".gitkeep").exists()
