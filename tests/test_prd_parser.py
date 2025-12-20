"""
Tests for PRD Parser Module

Tests markdown parsing and generation including:
- parse_prd_markdown() - Parse markdown into PRDDocument
- generate_prd_markdown() - Generate markdown from PRDDocument
- extract_requirements_from_text() - Extract requirements from raw text
- validate_prd_structure() - Validate PRD completeness
"""

import pytest
from datetime import datetime, timezone

from src.core.prd_parser import (
    parse_prd_markdown,
    generate_prd_markdown,
    extract_requirements_from_text,
    validate_prd_structure,
)
from src.core.prd_schemas import (
    PRDDocument,
    Feature,
    UserStory,
    AcceptanceCriterion,
    Task,
    RequirementStatus,
    Priority,
)


class TestParsePRDMarkdown:
    """Tests for parse_prd_markdown function."""

    def test_parse_basic_prd(self):
        """Test parsing a basic PRD markdown."""
        markdown = """# Product Requirements Document

## Original Request
<!-- VERBATIM_START -->
Build a dark mode feature for the application.
<!-- VERBATIM_END -->

## Metadata
- **Created**: 2025-12-14T10:30:00Z
- **Last Updated**: 2025-12-14T15:45:00Z
- **Session**: session_20251214_103000
- **Status**: In Progress

---

## Features

### F001: Dark Mode
- **Status**: [ ] Not Started
- **Priority**: High
- **Description**: Add dark mode support

#### User Stories

##### US001: Toggle Theme
- **Status**: [ ] Not Started
- **As a**: user
- **I want**: to toggle between light and dark themes
- **So that**: I can use the app comfortably

###### Acceptance Criteria

- AC001: [ ] Toggle button visible in settings
- AC002: [ ] Theme changes immediately on toggle

#### Tasks

- T001: [ ] Create toggle component (Linked to: US001, AC001)
- T002: [ ] Add theme CSS variables

---

## Progress Summary
- Features: 0/1 (0%)
"""
        prd = parse_prd_markdown(markdown)

        assert prd.original_request == "Build a dark mode feature for the application."
        assert prd.session_id == "session_20251214_103000"
        assert len(prd.features) == 1

        feature = prd.features[0]
        assert feature.id == "F001"
        assert feature.name == "Dark Mode"
        assert feature.priority == Priority.HIGH

        assert len(feature.user_stories) == 1
        story = feature.user_stories[0]
        assert story.id == "US001"
        assert story.as_a == "user"
        assert len(story.acceptance_criteria) == 2

        assert len(feature.tasks) == 2
        task = feature.tasks[0]
        assert task.id == "T001"
        assert "US001" in task.linked_stories
        assert "AC001" in task.linked_criteria

    def test_parse_prd_with_complete_items(self):
        """Test parsing PRD with completed items."""
        markdown = """# Product Requirements Document

## Original Request
<!-- VERBATIM_START -->
Test request
<!-- VERBATIM_END -->

## Features

### F001: Test Feature
- **Status**: [x] Complete
- **Priority**: Medium

#### User Stories

##### US001: Test Story
- **Status**: [x] Complete
- **As a**: developer
- **I want**: to test
- **So that**: it works

###### Acceptance Criteria

- AC001: [x] First criterion done
- AC002: [ ] Second criterion pending
"""
        prd = parse_prd_markdown(markdown)

        feature = prd.features[0]
        assert feature.status == RequirementStatus.COMPLETE

        story = feature.user_stories[0]
        assert story.status == RequirementStatus.COMPLETE

        assert story.acceptance_criteria[0].status == RequirementStatus.COMPLETE
        assert story.acceptance_criteria[1].status == RequirementStatus.NOT_STARTED

    def test_parse_prd_without_verbatim_markers(self):
        """Test parsing PRD without verbatim markers."""
        markdown = """# Product Requirements Document

## Original Request
This is the original request without markers.

## Features

### F001: Test
- **Status**: [ ] Not Started
- **Priority**: Low
"""
        prd = parse_prd_markdown(markdown)
        assert "original request without markers" in prd.original_request.lower()

    def test_parse_empty_prd(self):
        """Test parsing empty/minimal PRD."""
        markdown = """# Product Requirements Document

## Original Request
<!-- VERBATIM_START -->
Empty test
<!-- VERBATIM_END -->
"""
        prd = parse_prd_markdown(markdown)
        assert prd.original_request == "Empty test"
        assert len(prd.features) == 0


class TestGeneratePRDMarkdown:
    """Tests for generate_prd_markdown function."""

    def test_generate_basic_prd(self):
        """Test generating markdown from basic PRD."""
        now = datetime.now(timezone.utc)
        prd = PRDDocument(
            original_request="Build a test feature",
            created_at=now,
            last_updated=now,
            session_id="session_20251214_103000",
            features=[
                Feature(
                    id="F001",
                    name="Test Feature",
                    description="A test feature",
                    priority=Priority.HIGH,
                    status=RequirementStatus.NOT_STARTED,
                ),
            ],
        )

        markdown = generate_prd_markdown(prd)

        assert "# Product Requirements Document" in markdown
        assert "Build a test feature" in markdown
        assert "<!-- VERBATIM_START -->" in markdown
        assert "### F001: Test Feature" in markdown
        assert "High" in markdown
        assert "Progress Summary" in markdown

    def test_generate_prd_with_full_structure(self):
        """Test generating markdown with full PRD structure."""
        now = datetime.now(timezone.utc)
        prd = PRDDocument(
            original_request="Full test",
            created_at=now,
            last_updated=now,
            session_id="session_test",
            features=[
                Feature(
                    id="F001",
                    name="Feature One",
                    description="First feature",
                    priority=Priority.HIGH,
                    user_stories=[
                        UserStory(
                            id="US001",
                            title="Story One",
                            as_a="user",
                            i_want="to do something",
                            so_that="I benefit",
                            acceptance_criteria=[
                                AcceptanceCriterion(
                                    id="AC001",
                                    description="First criterion",
                                    status=RequirementStatus.COMPLETE,
                                ),
                                AcceptanceCriterion(
                                    id="AC002",
                                    description="Second criterion",
                                ),
                            ],
                        ),
                    ],
                    tasks=[
                        Task(
                            id="T001",
                            description="First task",
                            linked_stories=["US001"],
                            linked_criteria=["AC001"],
                        ),
                    ],
                ),
            ],
        )

        markdown = generate_prd_markdown(prd)

        assert "### F001: Feature One" in markdown
        assert "##### US001: Story One" in markdown
        assert "- **As a**: user" in markdown
        assert "- AC001: [x] First criterion" in markdown
        assert "- AC002: [ ] Second criterion" in markdown
        assert "- T001: [ ] First task (Linked to: US001, AC001)" in markdown

    def test_roundtrip_parse_generate(self):
        """Test that parse -> generate -> parse produces consistent results."""
        now = datetime.now(timezone.utc)
        original_prd = PRDDocument(
            original_request="Roundtrip test request",
            created_at=now,
            last_updated=now,
            session_id="session_roundtrip",
            features=[
                Feature(
                    id="F001",
                    name="Roundtrip Feature",
                    description="Testing roundtrip",
                    priority=Priority.MEDIUM,
                    user_stories=[
                        UserStory(
                            id="US001",
                            title="Roundtrip Story",
                            as_a="tester",
                            i_want="roundtrip to work",
                            so_that="tests pass",
                            acceptance_criteria=[
                                AcceptanceCriterion(id="AC001", description="Works correctly"),
                            ],
                        ),
                    ],
                ),
            ],
        )

        # Generate markdown
        markdown = generate_prd_markdown(original_prd)

        # Parse it back
        parsed_prd = parse_prd_markdown(markdown)

        # Verify key fields match
        assert parsed_prd.original_request == original_prd.original_request
        assert len(parsed_prd.features) == len(original_prd.features)
        assert parsed_prd.features[0].id == original_prd.features[0].id
        assert parsed_prd.features[0].name == original_prd.features[0].name


class TestExtractRequirementsFromText:
    """Tests for extract_requirements_from_text function."""

    def test_extract_simple_request(self):
        """Test extracting requirements from simple request."""
        text = "Build a dark mode feature with toggle support"
        prd = extract_requirements_from_text(text)

        assert prd.original_request == text
        assert len(prd.features) >= 1
        assert prd.features[0].id == "F001"

    def test_extract_with_user_story_pattern(self):
        """Test extracting when text contains user story pattern."""
        text = """
        As a user, I want to toggle dark mode, so that I can use the app at night.
        As a developer, I want theme variables, so that styling is consistent.
        """
        prd = extract_requirements_from_text(text)

        # Should extract user stories from the text
        assert prd.original_request.strip() == text.strip()
        assert len(prd.features) >= 1

    def test_extract_with_project_name(self):
        """Test extraction with project name."""
        text = "Add authentication to the app"
        prd = extract_requirements_from_text(text, project_name="MyApp")

        assert prd.project_name == "MyApp"

    def test_extract_with_session_id(self):
        """Test extraction with session ID."""
        text = "Simple feature request"
        prd = extract_requirements_from_text(
            text,
            session_id="session_custom_123"
        )

        assert prd.session_id == "session_custom_123"

    def test_extract_multi_paragraph(self):
        """Test extracting from multi-paragraph text."""
        text = """
        First, we need user authentication with login and logout.

        Second, add a dashboard with user statistics.

        Third, implement email notifications for important events.
        """
        prd = extract_requirements_from_text(text)

        # Should create multiple features for distinct paragraphs
        assert len(prd.features) >= 1


class TestValidatePRDStructure:
    """Tests for validate_prd_structure function."""

    def test_validate_valid_prd(self):
        """Test validation of valid PRD."""
        now = datetime.now(timezone.utc)
        prd = PRDDocument(
            original_request="Valid PRD",
            created_at=now,
            last_updated=now,
            session_id="session_valid",
            features=[
                Feature(
                    id="F001",
                    name="Valid Feature",
                    description="Valid",
                    user_stories=[
                        UserStory(
                            id="US001",
                            title="Valid Story",
                            as_a="user",
                            i_want="valid",
                            so_that="valid",
                        ),
                    ],
                ),
            ],
        )

        is_valid, errors = validate_prd_structure(prd)
        # Should be valid (only warning about no criteria)
        assert is_valid or all("warning" in e.lower() for e in errors)

    def test_validate_prd_with_bad_links(self):
        """Test validation catches bad links."""
        now = datetime.now(timezone.utc)
        prd = PRDDocument(
            original_request="Bad links PRD",
            created_at=now,
            last_updated=now,
            session_id="session_bad",
            features=[
                Feature(
                    id="F001",
                    name="Feature",
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

        is_valid, errors = validate_prd_structure(prd)
        assert is_valid is False
        assert any("non-existent" in e.lower() for e in errors)

    def test_validate_prd_without_stories(self):
        """Test validation warns about features without stories."""
        now = datetime.now(timezone.utc)
        prd = PRDDocument(
            original_request="No stories PRD",
            created_at=now,
            last_updated=now,
            session_id="session_nostories",
            features=[
                Feature(
                    id="F001",
                    name="Empty Feature",
                    description="No user stories",
                ),
            ],
        )

        is_valid, errors = validate_prd_structure(prd)
        # Should have warning about no user stories
        assert any("no user stories" in e.lower() for e in errors)
