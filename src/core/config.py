"""
Configuration Management for SubAgent Tracking System

Provides centralized configuration with environment variable support,
validation, and sensible defaults.

Usage:
    from src.core.config import get_config

    config = get_config()
    print(config.activity_log_path)
"""

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass, field


@dataclass
class Config:
    """
    Configuration settings for SubAgent Tracking System.

    All paths are configurable via environment variables with sensible defaults.
    """

    # Base paths
    project_root: Path = field(default_factory=lambda: Path.cwd())
    claude_dir: Path = field(default_factory=lambda: Path.cwd() / ".claude")

    # Tracking directories
    logs_dir: Path = field(default_factory=lambda: Path.cwd() / ".claude" / "logs")
    state_dir: Path = field(default_factory=lambda: Path.cwd() / ".claude" / "state")
    analytics_dir: Path = field(default_factory=lambda: Path.cwd() / ".claude" / "analytics")
    credentials_dir: Path = field(default_factory=lambda: Path.cwd() / ".claude" / "credentials")
    handoffs_dir: Path = field(default_factory=lambda: Path.cwd() / ".claude" / "handoffs")

    # Activity log settings
    activity_log_enabled: bool = True
    activity_log_compression: bool = True
    activity_log_retention_count: int = 2  # Keep current + previous session

    # Snapshot settings
    snapshot_enabled: bool = True
    snapshot_trigger_agent_count: int = 10  # Snapshot every N agent invocations
    snapshot_trigger_token_count: int = 20000  # Snapshot every N tokens
    snapshot_compression: bool = True
    snapshot_retention_days: int = 7  # Keep intermediate snapshots for 7 days

    # Backup settings
    backup_enabled: bool = False  # Disabled by default until OAuth setup
    backup_on_handoff: bool = True
    backup_on_token_limit: bool = True
    backup_async: bool = True
    google_drive_folder_name: str = "SubAgentTracking"

    # Analytics settings
    analytics_enabled: bool = True
    analytics_db_name: str = "tracking.db"
    analytics_batch_size: int = 100  # Batch inserts for performance

    # Performance budgets
    event_logging_max_latency_ms: float = 1.0
    snapshot_creation_max_latency_ms: float = 100.0
    query_max_latency_ms: float = 10.0
    backup_max_duration_minutes: float = 2.0

    # Session settings
    token_limit_warning_threshold: float = 0.9  # Warn at 90% token usage
    default_token_budget: int = 200000  # Default token budget per session
    session_id_format: str = "session_%Y%m%d_%H%M%S"

    # Storage limits (local)
    max_local_storage_mb: int = 20
    max_log_file_size_mb: int = 10
    max_snapshot_size_mb: int = 5

    # Validation
    validate_event_schemas: bool = True
    strict_mode: bool = False  # Raise errors vs warnings

    def __post_init__(self):
        """Load configuration from environment variables if available."""
        self._load_from_env()
        self._ensure_directories()

    def _load_from_env(self):
        """Override defaults with environment variables."""
        # Base paths
        data_dir_override = os.getenv("SUBAGENT_DATA_DIR")
        root_override = os.getenv("SUBAGENT_TRACKING_ROOT")

        if data_dir_override:
            self.claude_dir = Path(data_dir_override)
            self._update_tracking_dirs()
        elif root_override:
            self.project_root = Path(root_override)
            self.claude_dir = self.project_root / ".claude"
            self._update_tracking_dirs()

        # Snapshot triggers
        if env_agent_count := os.getenv("SUBAGENT_SNAPSHOT_AGENT_COUNT"):
            self.snapshot_trigger_agent_count = int(env_agent_count)

        if env_token_count := os.getenv("SUBAGENT_SNAPSHOT_TOKEN_COUNT"):
            self.snapshot_trigger_token_count = int(env_token_count)

        # Backup settings
        if env_backup := os.getenv("SUBAGENT_BACKUP_ENABLED"):
            self.backup_enabled = env_backup.lower() in ("true", "1", "yes")

        # Analytics settings
        if env_analytics := os.getenv("SUBAGENT_ANALYTICS_ENABLED"):
            self.analytics_enabled = env_analytics.lower() in ("true", "1", "yes")

        # Performance budgets
        if env_log_latency := os.getenv("SUBAGENT_LOG_LATENCY_MS"):
            self.event_logging_max_latency_ms = float(env_log_latency)

        # Token budget
        if env_token_budget := os.getenv("SUBAGENT_TOKEN_BUDGET"):
            self.default_token_budget = int(env_token_budget)

        # Strict mode
        if env_strict := os.getenv("SUBAGENT_STRICT_MODE"):
            self.strict_mode = env_strict.lower() in ("true", "1", "yes")

    def _update_tracking_dirs(self):
        """Update all tracking directories based on claude_dir."""
        self.logs_dir = self.claude_dir / "logs"
        self.state_dir = self.claude_dir / "state"
        self.analytics_dir = self.claude_dir / "analytics"
        self.credentials_dir = self.claude_dir / "credentials"
        self.handoffs_dir = self.claude_dir / "handoffs"

    def _ensure_directories(self):
        """Create tracking directories if they don't exist."""
        for directory in [
            self.logs_dir,
            self.state_dir,
            self.analytics_dir,
            self.credentials_dir,
            self.handoffs_dir,
        ]:
            directory.mkdir(parents=True, exist_ok=True)

            # Create .gitkeep if directory is empty
            gitkeep = directory / ".gitkeep"
            if not gitkeep.exists() and not any(directory.iterdir()):
                gitkeep.touch()

    @property
    def activity_log_path(self) -> Path:
        """Get path for current session's activity log."""
        session_id = datetime.now(timezone.utc).strftime(self.session_id_format)
        return self.logs_dir / f"{session_id}.jsonl"

    @property
    def analytics_db_path(self) -> Path:
        """Get path for analytics database."""
        return self.analytics_dir / self.analytics_db_name

    def get_snapshot_path(self, session_id: str, snapshot_number: int) -> Path:
        """
        Get path for a specific snapshot.

        Args:
            session_id: Session identifier (e.g., 'session_20251102_153000')
            snapshot_number: Snapshot sequence number

        Returns:
            Path to snapshot file
        """
        return self.state_dir / f"{session_id}_snap{snapshot_number:03d}.json"

    def get_handoff_path(self, session_id: str) -> Path:
        """
        Get path for session handoff summary.

        Args:
            session_id: Session identifier

        Returns:
            Path to handoff markdown file
        """
        return self.handoffs_dir / f"{session_id}_handoff.md"

    def get_credentials_path(self, service: str) -> Path:
        """
        Get path for service credentials.

        Args:
            service: Service name (e.g., 'google_drive')

        Returns:
            Path to credentials file
        """
        return self.credentials_dir / f"{service}_credentials.json"

    def get_token_path(self, service: str) -> Path:
        """
        Get path for service token.

        Args:
            service: Service name (e.g., 'google_drive')

        Returns:
            Path to token file
        """
        return self.credentials_dir / f"{service}_token.json"

    def validate(self) -> tuple[bool, list[str]]:
        """
        Validate configuration settings.

        Returns:
            Tuple of (is_valid, list of validation errors)
        """
        errors = []

        # Check snapshot triggers are reasonable
        if self.snapshot_trigger_agent_count < 1:
            errors.append("snapshot_trigger_agent_count must be >= 1")

        if self.snapshot_trigger_token_count < 1000:
            errors.append("snapshot_trigger_token_count must be >= 1000")

        # Check performance budgets are reasonable
        if self.event_logging_max_latency_ms < 0.1:
            errors.append("event_logging_max_latency_ms must be >= 0.1")

        if self.snapshot_creation_max_latency_ms < 1.0:
            errors.append("snapshot_creation_max_latency_ms must be >= 1.0")

        # Check retention settings
        if self.activity_log_retention_count < 1:
            errors.append("activity_log_retention_count must be >= 1")

        if self.snapshot_retention_days < 1:
            errors.append("snapshot_retention_days must be >= 1")

        # Check storage limits
        if self.max_local_storage_mb < 1:
            errors.append("max_local_storage_mb must be >= 1")

        # Check token limit threshold
        if not (0.5 <= self.token_limit_warning_threshold <= 1.0):
            errors.append("token_limit_warning_threshold must be between 0.5 and 1.0")

        # Check directories exist
        for dir_name, directory in [
            ("logs_dir", self.logs_dir),
            ("state_dir", self.state_dir),
            ("analytics_dir", self.analytics_dir),
            ("credentials_dir", self.credentials_dir),
            ("handoffs_dir", self.handoffs_dir),
        ]:
            if not directory.exists():
                errors.append(f"{dir_name} does not exist: {directory}")

        return len(errors) == 0, errors

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert configuration to dictionary.

        Returns:
            Dictionary representation of configuration
        """
        return {
            # Paths (convert to strings)
            "project_root": str(self.project_root),
            "claude_dir": str(self.claude_dir),
            "logs_dir": str(self.logs_dir),
            "state_dir": str(self.state_dir),
            "analytics_dir": str(self.analytics_dir),
            "credentials_dir": str(self.credentials_dir),
            "handoffs_dir": str(self.handoffs_dir),
            # Settings
            "activity_log_enabled": self.activity_log_enabled,
            "activity_log_compression": self.activity_log_compression,
            "activity_log_retention_count": self.activity_log_retention_count,
            "snapshot_enabled": self.snapshot_enabled,
            "snapshot_trigger_agent_count": self.snapshot_trigger_agent_count,
            "snapshot_trigger_token_count": self.snapshot_trigger_token_count,
            "snapshot_compression": self.snapshot_compression,
            "snapshot_retention_days": self.snapshot_retention_days,
            "backup_enabled": self.backup_enabled,
            "backup_on_handoff": self.backup_on_handoff,
            "backup_on_token_limit": self.backup_on_token_limit,
            "backup_async": self.backup_async,
            "google_drive_folder_name": self.google_drive_folder_name,
            "analytics_enabled": self.analytics_enabled,
            "analytics_db_name": self.analytics_db_name,
            "analytics_batch_size": self.analytics_batch_size,
            # Performance budgets
            "event_logging_max_latency_ms": self.event_logging_max_latency_ms,
            "snapshot_creation_max_latency_ms": self.snapshot_creation_max_latency_ms,
            "query_max_latency_ms": self.query_max_latency_ms,
            "backup_max_duration_minutes": self.backup_max_duration_minutes,
            # Session settings
            "token_limit_warning_threshold": self.token_limit_warning_threshold,
            "default_token_budget": self.default_token_budget,
            "session_id_format": self.session_id_format,
            # Storage limits
            "max_local_storage_mb": self.max_local_storage_mb,
            "max_log_file_size_mb": self.max_log_file_size_mb,
            "max_snapshot_size_mb": self.max_snapshot_size_mb,
            # Validation
            "validate_event_schemas": self.validate_event_schemas,
            "strict_mode": self.strict_mode,
        }


# Global configuration instance
_config: Optional[Config] = None


def get_config(reload: bool = False) -> Config:
    """
    Get global configuration instance (singleton pattern).

    Args:
        reload: Force reload configuration from environment

    Returns:
        Global Config instance

    Example:
        >>> config = get_config()
        >>> print(config.activity_log_path)
    """
    global _config

    if _config is None or reload:
        _config = Config()

        # Validate configuration
        is_valid, errors = _config.validate()
        if not is_valid:
            if _config.strict_mode:
                raise ValueError(f"Invalid configuration: {', '.join(errors)}")
            else:
                import warnings

                warnings.warn(f"Configuration validation warnings: {', '.join(errors)}")

    return _config


def reset_config():
    """Reset global configuration (primarily for testing)."""
    global _config
    _config = None


# Convenience functions for common configuration queries
def is_backup_enabled() -> bool:
    """Check if cloud backup is enabled."""
    return get_config().backup_enabled


def is_analytics_enabled() -> bool:
    """Check if analytics database is enabled."""
    return get_config().analytics_enabled


def get_snapshot_triggers() -> tuple[int, int]:
    """
    Get snapshot trigger thresholds.

    Returns:
        Tuple of (agent_count, token_count)
    """
    config = get_config()
    return config.snapshot_trigger_agent_count, config.snapshot_trigger_token_count


def get_performance_budgets() -> Dict[str, float]:
    """
    Get performance budget targets.

    Returns:
        Dictionary of performance budgets
    """
    config = get_config()
    return {
        "event_logging_ms": config.event_logging_max_latency_ms,
        "snapshot_creation_ms": config.snapshot_creation_max_latency_ms,
        "query_ms": config.query_max_latency_ms,
        "backup_minutes": config.backup_max_duration_minutes,
    }
