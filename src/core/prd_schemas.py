"""
PRD Schema Definitions for SubAgent Tracking System

This module defines Pydantic models for Product Requirements Documents (PRDs):
- RequirementStatus - Status enum for all trackable items
- Priority - Priority level enum
- AcceptanceCriterion - Individual acceptance criterion with ID
- UserStory - User story with acceptance criteria
- Task - Implementation task linked to stories/criteria
- Feature - Feature containing user stories and tasks
- PRDDocument - Complete PRD document structure

All items use standardized IDs:
- Features: F001, F002, etc.
- User Stories: US001, US002, etc.
- Acceptance Criteria: AC001, AC002, etc.
- Tasks: T001, T002, etc.

Usage:
    from src.core.prd_schemas import PRDDocument, Feature, UserStory

    prd = PRDDocument(
        original_request="Build a dark mode feature...",
        created_at=datetime.now(timezone.utc),
        last_updated=datetime.now(timezone.utc),
        session_id="session_20251214_103000",
        features=[...]
    )
"""

from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Tuple
from pydantic import BaseModel, Field, field_validator, ConfigDict
from enum import Enum


# ============================================================================
# Enums
# ============================================================================


class RequirementStatus(str, Enum):
    """Status of a requirement item."""

    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"
    BLOCKED = "blocked"


class Priority(str, Enum):
    """Priority level for features and tasks."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# ============================================================================
# Acceptance Criterion
# ============================================================================


class AcceptanceCriterion(BaseModel):
    """
    Individual acceptance criterion for a user story.

    Represents a specific, testable condition that must be met
    for the user story to be considered complete.
    """

    model_config = ConfigDict(extra="allow", str_strip_whitespace=True)

    id: str = Field(..., description="Unique ID (e.g., 'AC001')")
    description: str = Field(..., description="Criterion description")
    status: RequirementStatus = Field(
        RequirementStatus.NOT_STARTED, description="Completion status"
    )
    completed_at: Optional[datetime] = Field(
        None, description="When this criterion was marked complete"
    )
    completed_by: Optional[str] = Field(
        None, description="Agent or user who marked this complete"
    )
    notes: Optional[str] = Field(None, description="Additional notes or context")

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        """Validate acceptance criterion ID format (AC followed by digits)."""
        if not v.startswith("AC"):
            raise ValueError(f"Acceptance criterion ID must start with 'AC': {v}")
        suffix = v[2:]
        if not suffix.isdigit():
            raise ValueError(f"Acceptance criterion ID must be AC followed by digits: {v}")
        return v


# ============================================================================
# User Story
# ============================================================================


class UserStory(BaseModel):
    """
    User story with acceptance criteria.

    Follows the standard format: "As a [role], I want [action], so that [benefit]"
    """

    model_config = ConfigDict(extra="allow", str_strip_whitespace=True)

    id: str = Field(..., description="Unique ID (e.g., 'US001')")
    title: str = Field(..., description="Brief title for the user story")
    as_a: str = Field(..., description="Role (e.g., 'developer', 'end user')")
    i_want: str = Field(..., description="Desired action or capability")
    so_that: str = Field(..., description="Benefit or reason")
    status: RequirementStatus = Field(
        RequirementStatus.NOT_STARTED, description="Completion status"
    )
    acceptance_criteria: List[AcceptanceCriterion] = Field(
        default_factory=list, description="List of acceptance criteria"
    )
    completed_at: Optional[datetime] = Field(
        None, description="When this story was marked complete"
    )
    completed_by: Optional[str] = Field(
        None, description="Agent or user who marked this complete"
    )
    notes: Optional[str] = Field(None, description="Additional notes or context")

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        """Validate user story ID format (US followed by digits)."""
        if not v.startswith("US"):
            raise ValueError(f"User story ID must start with 'US': {v}")
        suffix = v[2:]
        if not suffix.isdigit():
            raise ValueError(f"User story ID must be US followed by digits: {v}")
        return v

    def get_completion_percentage(self) -> float:
        """Calculate completion percentage based on acceptance criteria."""
        if not self.acceptance_criteria:
            return 100.0 if self.status == RequirementStatus.COMPLETE else 0.0

        complete_count = sum(
            1 for ac in self.acceptance_criteria if ac.status == RequirementStatus.COMPLETE
        )
        return (complete_count / len(self.acceptance_criteria)) * 100

    def is_all_criteria_complete(self) -> bool:
        """Check if all acceptance criteria are complete."""
        if not self.acceptance_criteria:
            return self.status == RequirementStatus.COMPLETE
        return all(
            ac.status == RequirementStatus.COMPLETE for ac in self.acceptance_criteria
        )


# ============================================================================
# Task
# ============================================================================


class Task(BaseModel):
    """
    Implementation task linked to user stories and acceptance criteria.

    Tasks are concrete work items that contribute to completing
    user stories and their acceptance criteria.
    """

    model_config = ConfigDict(extra="allow", str_strip_whitespace=True)

    id: str = Field(..., description="Unique ID (e.g., 'T001')")
    description: str = Field(..., description="Task description")
    status: RequirementStatus = Field(
        RequirementStatus.NOT_STARTED, description="Completion status"
    )
    priority: Priority = Field(Priority.MEDIUM, description="Task priority")
    linked_stories: List[str] = Field(
        default_factory=list, description="IDs of linked user stories"
    )
    linked_criteria: List[str] = Field(
        default_factory=list, description="IDs of linked acceptance criteria"
    )
    assigned_to: Optional[str] = Field(
        None, description="Agent assigned to this task"
    )
    completed_at: Optional[datetime] = Field(
        None, description="When this task was marked complete"
    )
    completed_by: Optional[str] = Field(
        None, description="Agent or user who completed this task"
    )
    notes: Optional[str] = Field(None, description="Additional notes or context")

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        """Validate task ID format (T followed by digits)."""
        if not v.startswith("T"):
            raise ValueError(f"Task ID must start with 'T': {v}")
        suffix = v[1:]
        if not suffix.isdigit():
            raise ValueError(f"Task ID must be T followed by digits: {v}")
        return v


# ============================================================================
# Feature
# ============================================================================


class Feature(BaseModel):
    """
    Feature containing user stories and tasks.

    A feature represents a high-level capability or functionality
    that may encompass multiple user stories and implementation tasks.
    """

    model_config = ConfigDict(extra="allow", str_strip_whitespace=True)

    id: str = Field(..., description="Unique ID (e.g., 'F001')")
    name: str = Field(..., description="Feature name")
    description: str = Field(..., description="Feature description")
    priority: Priority = Field(Priority.MEDIUM, description="Feature priority")
    status: RequirementStatus = Field(
        RequirementStatus.NOT_STARTED, description="Completion status"
    )
    user_stories: List[UserStory] = Field(
        default_factory=list, description="User stories for this feature"
    )
    tasks: List[Task] = Field(
        default_factory=list, description="Tasks for this feature"
    )
    completed_at: Optional[datetime] = Field(
        None, description="When this feature was marked complete"
    )
    completed_by: Optional[str] = Field(
        None, description="Agent or user who marked this complete"
    )
    notes: Optional[str] = Field(None, description="Additional notes or context")

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        """Validate feature ID format (F followed by digits)."""
        if not v.startswith("F"):
            raise ValueError(f"Feature ID must start with 'F': {v}")
        suffix = v[1:]
        if not suffix.isdigit():
            raise ValueError(f"Feature ID must be F followed by digits: {v}")
        return v

    def get_completion_percentage(self) -> float:
        """Calculate completion percentage based on user stories."""
        if not self.user_stories:
            return 100.0 if self.status == RequirementStatus.COMPLETE else 0.0

        complete_count = sum(
            1 for story in self.user_stories if story.status == RequirementStatus.COMPLETE
        )
        return (complete_count / len(self.user_stories)) * 100

    def is_all_stories_complete(self) -> bool:
        """Check if all user stories are complete."""
        if not self.user_stories:
            return self.status == RequirementStatus.COMPLETE
        return all(
            story.status == RequirementStatus.COMPLETE for story in self.user_stories
        )

    def get_all_acceptance_criteria(self) -> List[AcceptanceCriterion]:
        """Get all acceptance criteria from all user stories."""
        criteria = []
        for story in self.user_stories:
            criteria.extend(story.acceptance_criteria)
        return criteria


# ============================================================================
# PRD Document
# ============================================================================


class PRDDocument(BaseModel):
    """
    Complete Product Requirements Document structure.

    Contains the original request, parsed features, user stories,
    acceptance criteria, and tasks with their completion status.
    """

    model_config = ConfigDict(extra="allow", str_strip_whitespace=True)

    # Core content
    original_request: str = Field(
        ..., description="Original user request (preserved verbatim)"
    )
    features: List[Feature] = Field(
        default_factory=list, description="List of features"
    )

    # Metadata
    created_at: datetime = Field(..., description="When PRD was created")
    last_updated: datetime = Field(..., description="When PRD was last updated")
    session_id: str = Field(..., description="Session ID when PRD was created")
    version: str = Field("1.0", description="PRD schema version")
    author: Optional[str] = Field(None, description="Who created this PRD")
    project_name: Optional[str] = Field(None, description="Project name")

    # Reference tracking
    reference_count: int = Field(
        0, description="How many times this PRD has been referenced"
    )
    last_referenced_at: Optional[datetime] = Field(
        None, description="When PRD was last referenced"
    )

    def get_all_items(self) -> Dict[str, Any]:
        """
        Return all trackable items with their IDs.

        Returns:
            Dict mapping item IDs to their objects
        """
        items: Dict[str, Any] = {}

        for feature in self.features:
            items[feature.id] = feature

            for story in feature.user_stories:
                items[story.id] = story

                for criterion in story.acceptance_criteria:
                    items[criterion.id] = criterion

            for task in feature.tasks:
                items[task.id] = task

        return items

    def get_item_by_id(self, item_id: str) -> Optional[Any]:
        """
        Get a specific item by its ID.

        Args:
            item_id: The ID to look up (F001, US001, AC001, T001, etc.)

        Returns:
            The item if found, None otherwise
        """
        return self.get_all_items().get(item_id)

    def get_completion_stats(self) -> Dict[str, Any]:
        """
        Calculate completion statistics for the PRD.

        Returns:
            Dict containing counts and percentages for each item type
        """
        features_total = len(self.features)
        features_complete = sum(
            1 for f in self.features if f.status == RequirementStatus.COMPLETE
        )

        stories_total = 0
        stories_complete = 0
        criteria_total = 0
        criteria_complete = 0
        tasks_total = 0
        tasks_complete = 0

        for feature in self.features:
            stories_total += len(feature.user_stories)
            stories_complete += sum(
                1 for s in feature.user_stories if s.status == RequirementStatus.COMPLETE
            )

            tasks_total += len(feature.tasks)
            tasks_complete += sum(
                1 for t in feature.tasks if t.status == RequirementStatus.COMPLETE
            )

            for story in feature.user_stories:
                criteria_total += len(story.acceptance_criteria)
                criteria_complete += sum(
                    1
                    for ac in story.acceptance_criteria
                    if ac.status == RequirementStatus.COMPLETE
                )

        def calc_percentage(complete: int, total: int) -> float:
            return (complete / total * 100) if total > 0 else 0.0

        return {
            "features": {
                "total": features_total,
                "complete": features_complete,
                "percentage": calc_percentage(features_complete, features_total),
            },
            "user_stories": {
                "total": stories_total,
                "complete": stories_complete,
                "percentage": calc_percentage(stories_complete, stories_total),
            },
            "acceptance_criteria": {
                "total": criteria_total,
                "complete": criteria_complete,
                "percentage": calc_percentage(criteria_complete, criteria_total),
            },
            "tasks": {
                "total": tasks_total,
                "complete": tasks_complete,
                "percentage": calc_percentage(tasks_complete, tasks_total),
            },
            "overall_percentage": calc_percentage(
                features_complete + stories_complete + criteria_complete + tasks_complete,
                features_total + stories_total + criteria_total + tasks_total,
            ),
        }

    def get_incomplete_items(
        self, item_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all incomplete items, optionally filtered by type.

        Args:
            item_type: "feature", "story", "criterion", "task", or None for all

        Returns:
            List of dicts with item info: {id, type, description, status, parent_id}
        """
        incomplete = []

        for feature in self.features:
            if feature.status != RequirementStatus.COMPLETE:
                if item_type is None or item_type == "feature":
                    incomplete.append(
                        {
                            "id": feature.id,
                            "type": "feature",
                            "description": feature.name,
                            "status": feature.status.value,
                            "parent_id": None,
                            "priority": feature.priority.value,
                        }
                    )

            for story in feature.user_stories:
                if story.status != RequirementStatus.COMPLETE:
                    if item_type is None or item_type == "story":
                        incomplete.append(
                            {
                                "id": story.id,
                                "type": "story",
                                "description": story.title,
                                "status": story.status.value,
                                "parent_id": feature.id,
                                "priority": feature.priority.value,
                            }
                        )

                for criterion in story.acceptance_criteria:
                    if criterion.status != RequirementStatus.COMPLETE:
                        if item_type is None or item_type == "criterion":
                            incomplete.append(
                                {
                                    "id": criterion.id,
                                    "type": "criterion",
                                    "description": criterion.description,
                                    "status": criterion.status.value,
                                    "parent_id": story.id,
                                    "priority": feature.priority.value,
                                }
                            )

            for task in feature.tasks:
                if task.status != RequirementStatus.COMPLETE:
                    if item_type is None or item_type == "task":
                        incomplete.append(
                            {
                                "id": task.id,
                                "type": "task",
                                "description": task.description,
                                "status": task.status.value,
                                "parent_id": feature.id,
                                "priority": task.priority.value,
                            }
                        )

        return incomplete

    def validate_structure(self) -> Tuple[bool, List[str]]:
        """
        Validate PRD structure for completeness and consistency.

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        seen_ids = set()

        # Check for duplicate IDs
        for item_id, item in self.get_all_items().items():
            if item_id in seen_ids:
                errors.append(f"Duplicate ID found: {item_id}")
            seen_ids.add(item_id)

        # Check task links reference existing items
        for feature in self.features:
            for task in feature.tasks:
                for story_id in task.linked_stories:
                    if story_id not in seen_ids:
                        errors.append(
                            f"Task {task.id} links to non-existent story: {story_id}"
                        )
                for criterion_id in task.linked_criteria:
                    if criterion_id not in seen_ids:
                        errors.append(
                            f"Task {task.id} links to non-existent criterion: {criterion_id}"
                        )

        # Check for features without user stories (warning)
        for feature in self.features:
            if not feature.user_stories:
                errors.append(f"Feature {feature.id} has no user stories (warning)")

        return len(errors) == 0, errors


# ============================================================================
# ID Generation Helpers
# ============================================================================


class IDGenerator:
    """Helper class for generating sequential IDs."""

    def __init__(self):
        self._counters = {
            "F": 0,
            "US": 0,
            "AC": 0,
            "T": 0,
        }

    def next_feature_id(self) -> str:
        """Generate next feature ID (F001, F002, etc.)."""
        self._counters["F"] += 1
        return f"F{self._counters['F']:03d}"

    def next_story_id(self) -> str:
        """Generate next user story ID (US001, US002, etc.)."""
        self._counters["US"] += 1
        return f"US{self._counters['US']:03d}"

    def next_criterion_id(self) -> str:
        """Generate next acceptance criterion ID (AC001, AC002, etc.)."""
        self._counters["AC"] += 1
        return f"AC{self._counters['AC']:03d}"

    def next_task_id(self) -> str:
        """Generate next task ID (T001, T002, etc.)."""
        self._counters["T"] += 1
        return f"T{self._counters['T']:03d}"

    def set_counters_from_prd(self, prd: PRDDocument) -> None:
        """
        Set counters based on existing IDs in a PRD.

        Ensures new IDs don't conflict with existing ones.
        """
        for item_id in prd.get_all_items().keys():
            if item_id.startswith("F"):
                num = int(item_id[1:])
                self._counters["F"] = max(self._counters["F"], num)
            elif item_id.startswith("US"):
                num = int(item_id[2:])
                self._counters["US"] = max(self._counters["US"], num)
            elif item_id.startswith("AC"):
                num = int(item_id[2:])
                self._counters["AC"] = max(self._counters["AC"], num)
            elif item_id.startswith("T"):
                num = int(item_id[1:])
                self._counters["T"] = max(self._counters["T"], num)


__all__ = [
    "RequirementStatus",
    "Priority",
    "AcceptanceCriterion",
    "UserStory",
    "Task",
    "Feature",
    "PRDDocument",
    "IDGenerator",
]
