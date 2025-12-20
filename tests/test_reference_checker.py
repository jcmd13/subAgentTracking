"""
Tests for Reference Checker Module

Tests the periodic PRD reference checking system including:
- ReferenceChecker class with configurable intervals
- Trigger detection (agent count, token count, manual)
- Relevant requirement selection
- Reference prompt generation
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

from src.core.reference_checker import (
    ReferenceChecker,
    get_reference_checker,
    initialize_reference_checker,
    reset_reference_checker,
)
from src.core.prd_schemas import (
    PRDDocument,
    Feature,
    UserStory,
    AcceptanceCriterion,
    RequirementStatus,
    Priority,
)


@pytest.fixture
def sample_prd():
    """Create a sample PRD for testing."""
    now = datetime.now(timezone.utc)
    return PRDDocument(
        original_request="Build a dark mode feature",
        created_at=now,
        last_updated=now,
        session_id="session_test",
        features=[
            Feature(
                id="F001",
                name="Dark Mode",
                description="Add dark mode support",
                priority=Priority.HIGH,
                status=RequirementStatus.NOT_STARTED,
                user_stories=[
                    UserStory(
                        id="US001",
                        title="Toggle Theme",
                        as_a="user",
                        i_want="toggle themes",
                        so_that="comfort",
                        status=RequirementStatus.NOT_STARTED,
                        acceptance_criteria=[
                            AcceptanceCriterion(
                                id="AC001",
                                description="Toggle visible",
                                status=RequirementStatus.NOT_STARTED,
                            ),
                            AcceptanceCriterion(
                                id="AC002",
                                description="Theme persists",
                                status=RequirementStatus.COMPLETE,
                            ),
                        ],
                    ),
                ],
            ),
            Feature(
                id="F002",
                name="Theme Customization",
                description="Custom themes",
                priority=Priority.MEDIUM,
                status=RequirementStatus.NOT_STARTED,
            ),
        ],
    )


@pytest.fixture
def checker():
    """Create a fresh ReferenceChecker for testing."""
    return ReferenceChecker(agent_interval=5, token_interval=15000)


class TestReferenceChecker:
    """Tests for ReferenceChecker class."""

    def test_init_default_intervals(self):
        """Test initialization with default intervals."""
        checker = ReferenceChecker()
        assert checker.agent_interval == 5
        assert checker.token_interval == 15000

    def test_init_custom_intervals(self):
        """Test initialization with custom intervals."""
        checker = ReferenceChecker(agent_interval=10, token_interval=20000)
        assert checker.agent_interval == 10
        assert checker.token_interval == 20000


class TestShouldReferenceCheck:
    """Tests for should_reference_check method."""

    def test_no_check_when_no_prd(self, checker):
        """Test that no check is triggered when no PRD exists."""
        with patch("src.core.reference_checker.prd_exists", return_value=False):
            should_check, reason = checker.should_reference_check(agent_count=10)
            assert should_check is False
            assert reason == "no_prd"

    def test_check_triggered_by_agent_count(self, checker):
        """Test check triggered by agent count interval."""
        with patch("src.core.reference_checker.prd_exists", return_value=True):
            # First check at count 5
            should_check, reason = checker.should_reference_check(agent_count=5)
            assert should_check is True
            assert "agent_count" in reason

            # Should not trigger again until count 10
            should_check, reason = checker.should_reference_check(agent_count=7)
            assert should_check is False

            # Should trigger at count 10
            should_check, reason = checker.should_reference_check(agent_count=10)
            assert should_check is True

    def test_check_triggered_by_token_count(self, checker):
        """Test check triggered by token count interval."""
        with patch("src.core.reference_checker.prd_exists", return_value=True):
            # First check at 15000 tokens
            should_check, reason = checker.should_reference_check(token_count=15000)
            assert should_check is True
            assert "token_count" in reason

            # Should not trigger again until 30000
            should_check, reason = checker.should_reference_check(token_count=20000)
            assert should_check is False

            # Should trigger at 30000
            should_check, reason = checker.should_reference_check(token_count=30000)
            assert should_check is True

    def test_force_check(self, checker):
        """Test forced reference check."""
        with patch("src.core.reference_checker.prd_exists", return_value=True):
            should_check, reason = checker.should_reference_check(force=True)
            assert should_check is True
            assert reason == "manual"

    def test_not_due_check(self, checker):
        """Test when check is not due."""
        with patch("src.core.reference_checker.prd_exists", return_value=True):
            should_check, reason = checker.should_reference_check(agent_count=2)
            assert should_check is False
            assert reason == "not_due"


class TestGetRelevantRequirements:
    """Tests for get_relevant_requirements method."""

    def test_returns_incomplete_items(self, checker, sample_prd):
        """Test that incomplete items are returned."""
        with patch("src.core.reference_checker.get_incomplete_items") as mock_get:
            mock_get.return_value = [
                {"id": "F001", "type": "feature", "description": "Dark Mode", "priority": "high", "status": "not_started"},
                {"id": "AC001", "type": "criterion", "description": "Toggle visible", "priority": "high", "status": "not_started"},
            ]

            requirements = checker.get_relevant_requirements(max_items=5)

            assert len(requirements) <= 5
            mock_get.assert_called_once()

    def test_prioritizes_high_priority_items(self, checker):
        """Test that high priority items are prioritized."""
        with patch("src.core.reference_checker.get_incomplete_items") as mock_get:
            mock_get.return_value = [
                {"id": "F001", "type": "feature", "description": "High", "priority": "high", "status": "not_started"},
                {"id": "F002", "type": "feature", "description": "Low", "priority": "low", "status": "not_started"},
            ]

            requirements = checker.get_relevant_requirements(max_items=5)

            # High priority should come first
            assert requirements[0]["priority"] == "high"

    def test_limits_results(self, checker):
        """Test that results are limited to max_items."""
        with patch("src.core.reference_checker.get_incomplete_items") as mock_get:
            mock_get.return_value = [
                {"id": f"AC{i:03d}", "type": "criterion", "description": f"Item {i}", "priority": "medium", "status": "not_started"}
                for i in range(10)
            ]

            requirements = checker.get_relevant_requirements(max_items=3)

            assert len(requirements) == 3

    def test_returns_empty_when_no_incomplete(self, checker):
        """Test returns empty list when no incomplete items."""
        with patch("src.core.reference_checker.get_incomplete_items") as mock_get:
            mock_get.return_value = []

            requirements = checker.get_relevant_requirements()

            assert requirements == []


class TestGenerateReferencePrompt:
    """Tests for generate_reference_prompt method."""

    def test_generates_prompt_with_requirements(self, checker):
        """Test generating prompt with requirements."""
        requirements = [
            {"id": "F001", "type": "feature", "description": "Dark Mode", "priority": "high", "status": "not_started"},
            {"id": "AC001", "type": "criterion", "description": "Toggle visible", "priority": "high", "status": "not_started"},
        ]

        with patch("src.core.reference_checker.get_completion_stats") as mock_stats:
            mock_stats.return_value = {"overall_percentage": 42.0}

            prompt = checker.generate_reference_prompt(requirements, "agent_count_5")

            assert "## PRD Reference Check" in prompt
            assert "agent_count_5" in prompt
            assert "F001" in prompt
            assert "AC001" in prompt
            assert "Dark Mode" in prompt
            assert "42%" in prompt

    def test_generates_prompt_without_requirements(self, checker):
        """Test generating prompt when no requirements."""
        with patch("src.core.reference_checker.get_completion_stats") as mock_stats:
            mock_stats.return_value = {"overall_percentage": 100.0}

            prompt = checker.generate_reference_prompt([], "manual")

            assert "project may be complete" in prompt.lower()

    def test_prompt_includes_reminder(self, checker):
        """Test that prompt includes reminder text."""
        requirements = [
            {"id": "F001", "type": "feature", "description": "Test", "priority": "medium", "status": "not_started"},
        ]

        with patch("src.core.reference_checker.get_completion_stats") as mock_stats:
            mock_stats.return_value = {}

            prompt = checker.generate_reference_prompt(requirements, "manual")

            assert "Reminder" in prompt
            assert "guide your current work" in prompt.lower()


class TestLogReference:
    """Tests for log_reference method."""

    def test_updates_reference_history(self, checker):
        """Test that reference history is updated."""
        with patch("src.core.reference_checker.increment_reference_count"):
            with patch("src.core.activity_logger_compat.log_reference_check_completed", return_value="evt_001"):
                checker.log_reference(
                    requirement_ids=["F001", "AC001"],
                    agent="orchestrator",
                    trigger="agent_count_5",
                )

                stats = checker.get_stats()
                assert stats["total_reference_checks"] == 1
                assert stats["recently_referenced_count"] == 2

    def test_handles_missing_activity_logger(self, checker):
        """Test graceful handling when activity logger not available."""
        with patch("src.core.reference_checker.increment_reference_count"):
            with patch.dict("sys.modules", {"src.core.activity_logger_compat": None, "src.core.activity_logger": None}):
                # Should not raise
                result = checker.log_reference(
                    requirement_ids=["F001"],
                    agent="test",
                    trigger="manual",
                )
                # Result may be None if import fails


class TestReferenceCheckerStats:
    """Tests for get_stats method."""

    def test_get_stats(self, checker):
        """Test getting statistics."""
        stats = checker.get_stats()

        assert "agent_interval" in stats
        assert "token_interval" in stats
        assert "last_agent_count" in stats
        assert "last_token_count" in stats
        assert "total_reference_checks" in stats
        assert "recently_referenced_count" in stats

        assert stats["agent_interval"] == 5
        assert stats["token_interval"] == 15000


class TestReferenceCheckerReset:
    """Tests for reset method."""

    def test_reset_clears_state(self, checker):
        """Test that reset clears all state."""
        # Simulate some activity
        checker._last_agent_count = 10
        checker._last_token_count = 20000
        checker._reference_history = ["F001", "AC001"]
        checker._total_reference_checks = 5

        checker.reset()

        stats = checker.get_stats()
        assert stats["last_agent_count"] == 0
        assert stats["last_token_count"] == 0
        assert stats["total_reference_checks"] == 0
        assert stats["recently_referenced_count"] == 0


class TestGlobalReferenceChecker:
    """Tests for global instance management."""

    def test_initialize_reference_checker(self):
        """Test initializing global reference checker."""
        reset_reference_checker()

        with patch("src.core.reference_checker.config.get_config") as mock_config:
            mock_cfg = MagicMock()
            mock_cfg.prd_reference_check_enabled = True
            mock_cfg.prd_reference_agent_interval = 10
            mock_cfg.prd_reference_token_interval = 20000
            mock_config.return_value = mock_cfg

            checker = initialize_reference_checker(agent_interval=10, token_interval=20000)

            assert checker is not None
            assert checker.agent_interval == 10
            assert checker.token_interval == 20000

        reset_reference_checker()

    def test_get_reference_checker_when_disabled(self):
        """Test that get_reference_checker returns None when disabled."""
        reset_reference_checker()

        with patch("src.core.reference_checker.config.get_config") as mock_config:
            mock_cfg = MagicMock()
            mock_cfg.prd_reference_check_enabled = False
            mock_config.return_value = mock_cfg

            checker = get_reference_checker()
            assert checker is None

        reset_reference_checker()
