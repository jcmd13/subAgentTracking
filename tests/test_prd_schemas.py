"""
Tests for PRD Schema Definitions

Tests the Pydantic models for PRD items including:
- RequirementStatus and Priority enums
- AcceptanceCriterion, UserStory, Task, Feature models
- PRDDocument with completion stats and validation
- IDGenerator for sequential ID generation
"""

import pytest
from datetime import datetime, timezone

from src.core.prd_schemas import (
    RequirementStatus,
    Priority,
    AcceptanceCriterion,
    UserStory,
    Task,
    Feature,
    PRDDocument,
    IDGenerator,
)


class TestRequirementStatus:
    """Tests for RequirementStatus enum."""

    def test_status_values(self):
        """Test all status values exist."""
        assert RequirementStatus.NOT_STARTED == "not_started"
        assert RequirementStatus.IN_PROGRESS == "in_progress"
        assert RequirementStatus.COMPLETE == "complete"
        assert RequirementStatus.BLOCKED == "blocked"


class TestPriority:
    """Tests for Priority enum."""

    def test_priority_values(self):
        """Test all priority values exist."""
        assert Priority.HIGH == "high"
        assert Priority.MEDIUM == "medium"
        assert Priority.LOW == "low"


class TestAcceptanceCriterion:
    """Tests for AcceptanceCriterion model."""

    def test_create_basic_criterion(self):
        """Test creating a basic acceptance criterion."""
        ac = AcceptanceCriterion(
            id="AC001",
            description="User can toggle dark mode",
        )
        assert ac.id == "AC001"
        assert ac.description == "User can toggle dark mode"
        assert ac.status == RequirementStatus.NOT_STARTED
        assert ac.completed_at is None
        assert ac.completed_by is None

    def test_criterion_with_complete_status(self):
        """Test criterion with complete status."""
        now = datetime.now(timezone.utc)
        ac = AcceptanceCriterion(
            id="AC002",
            description="Theme persists across sessions",
            status=RequirementStatus.COMPLETE,
            completed_at=now,
            completed_by="orchestrator-agent",
        )
        assert ac.status == RequirementStatus.COMPLETE
        assert ac.completed_at == now
        assert ac.completed_by == "orchestrator-agent"

    def test_invalid_criterion_id(self):
        """Test that invalid criterion IDs are rejected."""
        with pytest.raises(ValueError, match="must start with 'AC'"):
            AcceptanceCriterion(id="US001", description="Wrong prefix")

        with pytest.raises(ValueError, match="must be AC followed by digits"):
            AcceptanceCriterion(id="ACXYZ", description="Not digits")


class TestUserStory:
    """Tests for UserStory model."""

    def test_create_basic_story(self):
        """Test creating a basic user story."""
        story = UserStory(
            id="US001",
            title="Toggle Dark Mode",
            as_a="user",
            i_want="to toggle between light and dark themes",
            so_that="I can use the app comfortably in different lighting",
        )
        assert story.id == "US001"
        assert story.title == "Toggle Dark Mode"
        assert story.as_a == "user"
        assert story.status == RequirementStatus.NOT_STARTED
        assert len(story.acceptance_criteria) == 0

    def test_story_with_criteria(self):
        """Test story with acceptance criteria."""
        story = UserStory(
            id="US001",
            title="Toggle Dark Mode",
            as_a="user",
            i_want="to toggle themes",
            so_that="comfort",
            acceptance_criteria=[
                AcceptanceCriterion(id="AC001", description="Toggle visible"),
                AcceptanceCriterion(id="AC002", description="Theme persists"),
            ],
        )
        assert len(story.acceptance_criteria) == 2
        assert story.acceptance_criteria[0].id == "AC001"

    def test_story_completion_percentage(self):
        """Test completion percentage calculation."""
        story = UserStory(
            id="US001",
            title="Test Story",
            as_a="user",
            i_want="test",
            so_that="testing",
            acceptance_criteria=[
                AcceptanceCriterion(id="AC001", description="First", status=RequirementStatus.COMPLETE),
                AcceptanceCriterion(id="AC002", description="Second", status=RequirementStatus.NOT_STARTED),
            ],
        )
        assert story.get_completion_percentage() == 50.0

    def test_story_all_criteria_complete(self):
        """Test checking if all criteria are complete."""
        story = UserStory(
            id="US001",
            title="Test Story",
            as_a="user",
            i_want="test",
            so_that="testing",
            acceptance_criteria=[
                AcceptanceCriterion(id="AC001", description="First", status=RequirementStatus.COMPLETE),
                AcceptanceCriterion(id="AC002", description="Second", status=RequirementStatus.COMPLETE),
            ],
        )
        assert story.is_all_criteria_complete() is True

    def test_invalid_story_id(self):
        """Test that invalid story IDs are rejected."""
        with pytest.raises(ValueError, match="must start with 'US'"):
            UserStory(id="AC001", title="Wrong", as_a="user", i_want="x", so_that="y")


class TestTask:
    """Tests for Task model."""

    def test_create_basic_task(self):
        """Test creating a basic task."""
        task = Task(
            id="T001",
            description="Create toggle component",
        )
        assert task.id == "T001"
        assert task.description == "Create toggle component"
        assert task.status == RequirementStatus.NOT_STARTED
        assert task.priority == Priority.MEDIUM
        assert len(task.linked_stories) == 0
        assert len(task.linked_criteria) == 0

    def test_task_with_links(self):
        """Test task with linked stories and criteria."""
        task = Task(
            id="T001",
            description="Create toggle component",
            linked_stories=["US001"],
            linked_criteria=["AC001", "AC002"],
        )
        assert task.linked_stories == ["US001"]
        assert task.linked_criteria == ["AC001", "AC002"]

    def test_invalid_task_id(self):
        """Test that invalid task IDs are rejected."""
        with pytest.raises(ValueError, match="must start with 'T'"):
            Task(id="US001", description="Wrong prefix")


class TestFeature:
    """Tests for Feature model."""

    def test_create_basic_feature(self):
        """Test creating a basic feature."""
        feature = Feature(
            id="F001",
            name="Dark Mode",
            description="Add dark mode support to the application",
        )
        assert feature.id == "F001"
        assert feature.name == "Dark Mode"
        assert feature.status == RequirementStatus.NOT_STARTED
        assert feature.priority == Priority.MEDIUM

    def test_feature_with_stories_and_tasks(self):
        """Test feature with user stories and tasks."""
        feature = Feature(
            id="F001",
            name="Dark Mode",
            description="Dark mode support",
            user_stories=[
                UserStory(
                    id="US001",
                    title="Toggle",
                    as_a="user",
                    i_want="toggle",
                    so_that="comfort",
                ),
            ],
            tasks=[
                Task(id="T001", description="Create component"),
            ],
        )
        assert len(feature.user_stories) == 1
        assert len(feature.tasks) == 1

    def test_feature_completion_percentage(self):
        """Test feature completion percentage."""
        feature = Feature(
            id="F001",
            name="Test",
            description="Test feature",
            user_stories=[
                UserStory(
                    id="US001", title="A", as_a="user", i_want="x", so_that="y",
                    status=RequirementStatus.COMPLETE
                ),
                UserStory(
                    id="US002", title="B", as_a="user", i_want="x", so_that="y",
                    status=RequirementStatus.NOT_STARTED
                ),
            ],
        )
        assert feature.get_completion_percentage() == 50.0

    def test_invalid_feature_id(self):
        """Test that invalid feature IDs are rejected."""
        with pytest.raises(ValueError, match="must start with 'F'"):
            Feature(id="US001", name="Wrong", description="Wrong prefix")


class TestPRDDocument:
    """Tests for PRDDocument model."""

    def test_create_basic_prd(self):
        """Test creating a basic PRD document."""
        now = datetime.now(timezone.utc)
        prd = PRDDocument(
            original_request="Build a dark mode feature",
            created_at=now,
            last_updated=now,
            session_id="session_20251214_103000",
        )
        assert prd.original_request == "Build a dark mode feature"
        assert prd.session_id == "session_20251214_103000"
        assert len(prd.features) == 0

    def test_prd_with_features(self):
        """Test PRD with features."""
        now = datetime.now(timezone.utc)
        prd = PRDDocument(
            original_request="Build dark mode",
            created_at=now,
            last_updated=now,
            session_id="session_20251214_103000",
            features=[
                Feature(
                    id="F001",
                    name="Dark Mode",
                    description="Dark mode support",
                    user_stories=[
                        UserStory(
                            id="US001",
                            title="Toggle",
                            as_a="user",
                            i_want="toggle",
                            so_that="comfort",
                            acceptance_criteria=[
                                AcceptanceCriterion(id="AC001", description="Toggle visible"),
                            ],
                        ),
                    ],
                    tasks=[
                        Task(id="T001", description="Create component"),
                    ],
                ),
            ],
        )
        assert len(prd.features) == 1
        assert prd.features[0].id == "F001"

    def test_prd_get_all_items(self):
        """Test getting all items from PRD."""
        now = datetime.now(timezone.utc)
        prd = PRDDocument(
            original_request="Test",
            created_at=now,
            last_updated=now,
            session_id="session_test",
            features=[
                Feature(
                    id="F001",
                    name="Test",
                    description="Test",
                    user_stories=[
                        UserStory(
                            id="US001",
                            title="Story",
                            as_a="user",
                            i_want="x",
                            so_that="y",
                            acceptance_criteria=[
                                AcceptanceCriterion(id="AC001", description="Criterion"),
                            ],
                        ),
                    ],
                    tasks=[
                        Task(id="T001", description="Task"),
                    ],
                ),
            ],
        )
        items = prd.get_all_items()
        assert "F001" in items
        assert "US001" in items
        assert "AC001" in items
        assert "T001" in items
        assert len(items) == 4

    def test_prd_get_item_by_id(self):
        """Test getting specific item by ID."""
        now = datetime.now(timezone.utc)
        prd = PRDDocument(
            original_request="Test",
            created_at=now,
            last_updated=now,
            session_id="session_test",
            features=[
                Feature(
                    id="F001",
                    name="Test Feature",
                    description="Test",
                ),
            ],
        )
        item = prd.get_item_by_id("F001")
        assert item is not None
        assert item.name == "Test Feature"

        missing = prd.get_item_by_id("F999")
        assert missing is None

    def test_prd_completion_stats(self):
        """Test completion statistics calculation."""
        now = datetime.now(timezone.utc)
        prd = PRDDocument(
            original_request="Test",
            created_at=now,
            last_updated=now,
            session_id="session_test",
            features=[
                Feature(
                    id="F001",
                    name="Test",
                    description="Test",
                    status=RequirementStatus.COMPLETE,
                    user_stories=[
                        UserStory(
                            id="US001",
                            title="Story",
                            as_a="user",
                            i_want="x",
                            so_that="y",
                            status=RequirementStatus.COMPLETE,
                            acceptance_criteria=[
                                AcceptanceCriterion(
                                    id="AC001",
                                    description="Done",
                                    status=RequirementStatus.COMPLETE
                                ),
                                AcceptanceCriterion(
                                    id="AC002",
                                    description="Not done",
                                    status=RequirementStatus.NOT_STARTED
                                ),
                            ],
                        ),
                    ],
                    tasks=[
                        Task(id="T001", description="Done", status=RequirementStatus.COMPLETE),
                    ],
                ),
            ],
        )
        stats = prd.get_completion_stats()
        assert stats["features"]["total"] == 1
        assert stats["features"]["complete"] == 1
        assert stats["acceptance_criteria"]["total"] == 2
        assert stats["acceptance_criteria"]["complete"] == 1

    def test_prd_incomplete_items(self):
        """Test getting incomplete items."""
        now = datetime.now(timezone.utc)
        prd = PRDDocument(
            original_request="Test",
            created_at=now,
            last_updated=now,
            session_id="session_test",
            features=[
                Feature(
                    id="F001",
                    name="Test",
                    description="Test",
                    status=RequirementStatus.NOT_STARTED,
                ),
            ],
        )
        incomplete = prd.get_incomplete_items()
        assert len(incomplete) == 1
        assert incomplete[0]["id"] == "F001"
        assert incomplete[0]["type"] == "feature"

    def test_prd_validation(self):
        """Test PRD structure validation."""
        now = datetime.now(timezone.utc)
        prd = PRDDocument(
            original_request="Test",
            created_at=now,
            last_updated=now,
            session_id="session_test",
            features=[
                Feature(
                    id="F001",
                    name="Test",
                    description="Test",
                    tasks=[
                        Task(
                            id="T001",
                            description="Task with bad link",
                            linked_stories=["US999"],  # Non-existent
                        ),
                    ],
                ),
            ],
        )
        is_valid, errors = prd.validate_structure()
        assert is_valid is False
        assert any("non-existent story" in e for e in errors)


class TestIDGenerator:
    """Tests for IDGenerator."""

    def test_generate_feature_ids(self):
        """Test generating sequential feature IDs."""
        gen = IDGenerator()
        assert gen.next_feature_id() == "F001"
        assert gen.next_feature_id() == "F002"
        assert gen.next_feature_id() == "F003"

    def test_generate_story_ids(self):
        """Test generating sequential user story IDs."""
        gen = IDGenerator()
        assert gen.next_story_id() == "US001"
        assert gen.next_story_id() == "US002"

    def test_generate_criterion_ids(self):
        """Test generating sequential acceptance criterion IDs."""
        gen = IDGenerator()
        assert gen.next_criterion_id() == "AC001"
        assert gen.next_criterion_id() == "AC002"

    def test_generate_task_ids(self):
        """Test generating sequential task IDs."""
        gen = IDGenerator()
        assert gen.next_task_id() == "T001"
        assert gen.next_task_id() == "T002"

    def test_set_counters_from_prd(self):
        """Test setting counters from existing PRD."""
        now = datetime.now(timezone.utc)
        prd = PRDDocument(
            original_request="Test",
            created_at=now,
            last_updated=now,
            session_id="session_test",
            features=[
                Feature(
                    id="F005",
                    name="Test",
                    description="Test",
                    user_stories=[
                        UserStory(
                            id="US010",
                            title="Story",
                            as_a="user",
                            i_want="x",
                            so_that="y",
                            acceptance_criteria=[
                                AcceptanceCriterion(id="AC020", description="Criterion"),
                            ],
                        ),
                    ],
                    tasks=[
                        Task(id="T015", description="Task"),
                    ],
                ),
            ],
        )

        gen = IDGenerator()
        gen.set_counters_from_prd(prd)

        # Next IDs should be after existing ones
        assert gen.next_feature_id() == "F006"
        assert gen.next_story_id() == "US011"
        assert gen.next_criterion_id() == "AC021"
        assert gen.next_task_id() == "T016"
