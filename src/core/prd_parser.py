"""
PRD Parser - Markdown Parsing and Generation for PRD Documents

This module handles parsing PRD markdown files into structured PRDDocument
objects and generating markdown from PRDDocument structures.

Key Functions:
- parse_prd_markdown(text) -> PRDDocument - Parse markdown into structured data
- generate_prd_markdown(prd) -> str - Generate markdown from structure
- extract_requirements_from_text(raw) -> PRDDocument - Helper for parsing raw requests
- validate_prd_structure(prd) -> (bool, errors) - Validate PRD completeness

Usage:
    from src.core.prd_parser import parse_prd_markdown, generate_prd_markdown

    # Parse existing PRD
    with open(".subagent/requirements/PRD.md") as f:
        prd = parse_prd_markdown(f.read())

    # Generate markdown from PRD
    markdown = generate_prd_markdown(prd)
"""

import re
import logging
from datetime import datetime, timezone
from typing import List, Tuple, Optional, Dict, Any

from src.core.prd_schemas import (
    PRDDocument,
    Feature,
    UserStory,
    AcceptanceCriterion,
    Task,
    RequirementStatus,
    Priority,
    IDGenerator,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Markdown Parsing
# ============================================================================


def _extract_verbatim_request(text: str) -> str:
    """
    Extract the original request from verbatim markers.

    Looks for content between <!-- VERBATIM_START --> and <!-- VERBATIM_END -->
    """
    pattern = r"<!--\s*VERBATIM_START\s*-->\s*(.*?)\s*<!--\s*VERBATIM_END\s*-->"
    match = re.search(pattern, text, re.DOTALL)
    if match:
        return match.group(1).strip()

    # Fallback: look for "## Original Request" section
    pattern = r"##\s*Original Request\s*\n(.*?)(?=\n##|\Z)"
    match = re.search(pattern, text, re.DOTALL)
    if match:
        content = match.group(1).strip()
        # Remove verbatim markers if present but not matched above
        content = re.sub(r"<!--\s*VERBATIM_\w+\s*-->", "", content).strip()
        return content

    return ""


def _extract_metadata(text: str) -> Dict[str, Any]:
    """Extract metadata section from PRD markdown."""
    metadata = {}

    # Look for metadata section
    pattern = r"##\s*Metadata\s*\n(.*?)(?=\n##|\n---|\Z)"
    match = re.search(pattern, text, re.DOTALL)
    if not match:
        return metadata

    content = match.group(1)

    # Extract key-value pairs
    for line in content.split("\n"):
        line = line.strip()
        if line.startswith("- **") and "**:" in line:
            # Parse "- **Key**: Value" format
            key_match = re.match(r"-\s*\*\*(.+?)\*\*:\s*(.+)", line)
            if key_match:
                key = key_match.group(1).lower().replace(" ", "_")
                value = key_match.group(2).strip()
                metadata[key] = value

    return metadata


def _parse_status_checkbox(text: str) -> RequirementStatus:
    """Parse status from checkbox notation."""
    if "[x]" in text.lower() or "[X]" in text:
        return RequirementStatus.COMPLETE
    elif "[ ]" in text:
        return RequirementStatus.NOT_STARTED
    elif "blocked" in text.lower():
        return RequirementStatus.BLOCKED
    elif "in progress" in text.lower() or "in_progress" in text.lower():
        return RequirementStatus.IN_PROGRESS
    return RequirementStatus.NOT_STARTED


def _parse_priority(text: str) -> Priority:
    """Parse priority from text."""
    text_lower = text.lower()
    if "high" in text_lower:
        return Priority.HIGH
    elif "low" in text_lower:
        return Priority.LOW
    return Priority.MEDIUM


def _parse_acceptance_criteria(text: str, id_gen: IDGenerator) -> List[AcceptanceCriterion]:
    """Parse acceptance criteria from a section of text."""
    criteria = []

    # Pattern for "- AC001: [ ] Description" or "- AC001: [x] Description"
    pattern = r"-\s*(AC\d{3}):\s*(\[[ xX]\])\s*(.+)"
    matches = re.findall(pattern, text)

    for match in matches:
        ac_id, checkbox, description = match
        criteria.append(
            AcceptanceCriterion(
                id=ac_id,
                description=description.strip(),
                status=_parse_status_checkbox(checkbox),
            )
        )

    # Also look for criteria without IDs and assign them
    # Pattern for "- [ ] Description" (no ID)
    pattern_no_id = r"-\s*(\[[ xX]\])\s*(?!AC\d{3})(.+)"
    matches_no_id = re.findall(pattern_no_id, text)

    for match in matches_no_id:
        checkbox, description = match
        # Skip if this looks like it's already been captured
        if any(c.description == description.strip() for c in criteria):
            continue
        criteria.append(
            AcceptanceCriterion(
                id=id_gen.next_criterion_id(),
                description=description.strip(),
                status=_parse_status_checkbox(checkbox),
            )
        )

    return criteria


def _parse_user_story(text: str, story_id: str, id_gen: IDGenerator) -> Optional[UserStory]:
    """Parse a user story from text."""
    # Extract title from header - match only until end of line
    title_match = re.search(r"#####\s*" + re.escape(story_id) + r":\s*([^\n]+)", text)
    if not title_match:
        title_match = re.search(r"#####\s*([^\n]+)", text)

    title = title_match.group(1).strip() if title_match else "Untitled Story"

    # Extract as_a, i_want, so_that
    as_a = ""
    i_want = ""
    so_that = ""

    as_a_match = re.search(r"-\s*\*\*As a\*\*:\s*(.+)", text, re.IGNORECASE)
    if as_a_match:
        as_a = as_a_match.group(1).strip()

    i_want_match = re.search(r"-\s*\*\*I want\*\*:\s*(.+)", text, re.IGNORECASE)
    if i_want_match:
        i_want = i_want_match.group(1).strip()

    so_that_match = re.search(r"-\s*\*\*So that\*\*:\s*(.+)", text, re.IGNORECASE)
    if so_that_match:
        so_that = so_that_match.group(1).strip()

    # Extract status
    status = RequirementStatus.NOT_STARTED
    status_match = re.search(r"-\s*\*\*Status\*\*:\s*(.+)", text, re.IGNORECASE)
    if status_match:
        status = _parse_status_checkbox(status_match.group(1))

    # Extract acceptance criteria section
    ac_section_match = re.search(
        r"######\s*Acceptance Criteria\s*\n(.*?)(?=\n#####|\n####|\n###|\Z)",
        text,
        re.DOTALL | re.IGNORECASE,
    )
    acceptance_criteria = []
    if ac_section_match:
        acceptance_criteria = _parse_acceptance_criteria(ac_section_match.group(1), id_gen)

    return UserStory(
        id=story_id,
        title=title,
        as_a=as_a or "user",
        i_want=i_want or title,
        so_that=so_that or "the feature works as expected",
        status=status,
        acceptance_criteria=acceptance_criteria,
    )


def _parse_tasks(text: str, id_gen: IDGenerator) -> List[Task]:
    """Parse tasks from a section of text."""
    tasks = []

    # Pattern for "- T001: [ ] Description (Linked to: US001, AC001)"
    # Use [^(\n]+ to capture description (everything except '(' or newline)
    # then optionally match the linked section
    pattern = r"-\s*(T\d{3}):\s*(\[[ xX]\])\s*([^(\n]+)(?:\(Linked to:\s*([^)]+)\))?"
    matches = re.findall(pattern, text)

    for match in matches:
        task_id, checkbox, description, links = match
        linked_stories = []
        linked_criteria = []

        if links:
            # Parse linked items
            link_items = [l.strip() for l in links.split(",")]
            for item in link_items:
                if item.startswith("US"):
                    linked_stories.append(item)
                elif item.startswith("AC"):
                    linked_criteria.append(item)

        tasks.append(
            Task(
                id=task_id,
                description=description.strip(),
                status=_parse_status_checkbox(checkbox),
                linked_stories=linked_stories,
                linked_criteria=linked_criteria,
            )
        )

    # Also look for tasks without IDs
    # Use [^(\n]+ to capture description (everything except '(' or newline)
    pattern_no_id = r"-\s*(\[[ xX]\])\s*(?!T\d{3})([^(\n]+)(?:\(Linked to:\s*([^)]+)\))?"
    matches_no_id = re.findall(pattern_no_id, text)

    for match in matches_no_id:
        checkbox, description, links = match
        # Skip if already captured
        if any(t.description == description.strip() for t in tasks):
            continue

        linked_stories = []
        linked_criteria = []
        if links:
            link_items = [l.strip() for l in links.split(",")]
            for item in link_items:
                if item.startswith("US"):
                    linked_stories.append(item)
                elif item.startswith("AC"):
                    linked_criteria.append(item)

        tasks.append(
            Task(
                id=id_gen.next_task_id(),
                description=description.strip(),
                status=_parse_status_checkbox(checkbox),
                linked_stories=linked_stories,
                linked_criteria=linked_criteria,
            )
        )

    return tasks


def _parse_feature(text: str, feature_id: str, id_gen: IDGenerator) -> Optional[Feature]:
    """Parse a feature from text."""
    # Extract name from header - match only until end of line
    name_match = re.search(r"###\s*" + re.escape(feature_id) + r":\s*([^\n]+)", text)
    if not name_match:
        name_match = re.search(r"###\s*([^\n]+)", text)

    name = name_match.group(1).strip() if name_match else "Untitled Feature"

    # Extract status
    status = RequirementStatus.NOT_STARTED
    status_match = re.search(r"-\s*\*\*Status\*\*:\s*(.+)", text, re.IGNORECASE)
    if status_match:
        status = _parse_status_checkbox(status_match.group(1))

    # Extract priority
    priority = Priority.MEDIUM
    priority_match = re.search(r"-\s*\*\*Priority\*\*:\s*(.+)", text, re.IGNORECASE)
    if priority_match:
        priority = _parse_priority(priority_match.group(1))

    # Extract description
    description = ""
    desc_match = re.search(r"-\s*\*\*Description\*\*:\s*(.+)", text, re.IGNORECASE)
    if desc_match:
        description = desc_match.group(1).strip()

    # Parse user stories
    user_stories = []
    # Find all user story sections (##### US001: Title\n...) - capture ID, Title, and Body
    # Stop at next story (#####), tasks section (#### Tasks), or next feature (### F)
    # Note: Use \n###\s*F to avoid matching ###### (6 hashes) for Acceptance Criteria
    story_pattern = r"#####\s*(US\d{3}):\s*([^\n]+)\n(.*?)(?=\n#####\s*US|\n####\s*Tasks|\n###\s*F|\Z)"
    story_matches = re.findall(story_pattern, text, re.DOTALL)

    for story_id, story_title, story_text in story_matches:
        # Reconstruct the full story text with the header
        full_story_text = f"##### {story_id}: {story_title}\n{story_text}"
        story = _parse_user_story(full_story_text, story_id, id_gen)
        if story:
            user_stories.append(story)

    # Parse tasks section
    tasks = []
    tasks_section_match = re.search(
        r"####\s*Tasks\s*\n(.*?)(?=\n###|\Z)", text, re.DOTALL | re.IGNORECASE
    )
    if tasks_section_match:
        tasks = _parse_tasks(tasks_section_match.group(1), id_gen)

    return Feature(
        id=feature_id,
        name=name,
        description=description or name,
        priority=priority,
        status=status,
        user_stories=user_stories,
        tasks=tasks,
    )


def parse_prd_markdown(markdown_text: str) -> PRDDocument:
    """
    Parse PRD markdown into structured PRDDocument.

    Args:
        markdown_text: Full PRD markdown content

    Returns:
        PRDDocument with parsed features, stories, criteria, tasks

    Example:
        >>> with open("PRD.md") as f:
        ...     prd = parse_prd_markdown(f.read())
        >>> print(f"Found {len(prd.features)} features")
    """
    id_gen = IDGenerator()

    # Extract original request
    original_request = _extract_verbatim_request(markdown_text)

    # Extract metadata
    metadata = _extract_metadata(markdown_text)

    # Parse created_at and last_updated
    created_at = datetime.now(timezone.utc)
    last_updated = datetime.now(timezone.utc)

    if "created" in metadata:
        try:
            created_at = datetime.fromisoformat(
                metadata["created"].replace("Z", "+00:00")
            )
        except (ValueError, TypeError):
            pass

    if "last_updated" in metadata:
        try:
            last_updated = datetime.fromisoformat(
                metadata["last_updated"].replace("Z", "+00:00")
            )
        except (ValueError, TypeError):
            pass

    session_id = metadata.get("session", f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}")

    # Parse features
    features = []
    # Find all feature sections (### F001: Name\n...) - capture ID, Name, and Body separately
    feature_pattern = r"###\s*(F\d{3}):\s*([^\n]+)\n(.*?)(?=\n###\s*F\d{3}:|\n##\s*Progress|\n---\s*\n##|\Z)"
    feature_matches = re.findall(feature_pattern, markdown_text, re.DOTALL)

    for feature_id, feature_name, feature_text in feature_matches:
        # Reconstruct the full feature text with the header
        full_feature_text = f"### {feature_id}: {feature_name}\n{feature_text}"
        feature = _parse_feature(full_feature_text, feature_id, id_gen)
        if feature:
            features.append(feature)

    # If no features found with IDs, try to find any ### headers under ## Features
    if not features:
        features_section = re.search(
            r"##\s*Features\s*\n(.*?)(?=\n##\s*Progress|\Z)", markdown_text, re.DOTALL
        )
        if features_section:
            # Find features without standard IDs
            feature_headers = re.findall(
                r"###\s*([^:\n]+?)(?::\s*([^\n]+))?\n", features_section.group(1)
            )
            for header_match in feature_headers:
                feature_name = header_match[0].strip()
                if not feature_name.startswith("F") or not feature_name[1:4].isdigit():
                    # Generate ID for this feature
                    new_id = id_gen.next_feature_id()
                    # Find the feature content
                    feature_content_match = re.search(
                        r"###\s*" + re.escape(feature_name) + r"[^\n]*\n(.*?)(?=\n###|\n##|\Z)",
                        features_section.group(1),
                        re.DOTALL,
                    )
                    if feature_content_match:
                        feature = Feature(
                            id=new_id,
                            name=feature_name,
                            description=feature_name,
                            priority=Priority.MEDIUM,
                            status=RequirementStatus.NOT_STARTED,
                        )
                        features.append(feature)

    return PRDDocument(
        original_request=original_request,
        features=features,
        created_at=created_at,
        last_updated=last_updated,
        session_id=session_id,
        author=metadata.get("author"),
        project_name=metadata.get("project"),
    )


# ============================================================================
# Markdown Generation
# ============================================================================


def _generate_status_checkbox(status: RequirementStatus) -> str:
    """Generate checkbox notation for status."""
    if status == RequirementStatus.COMPLETE:
        return "[x]"
    return "[ ]"


def _generate_status_text(status: RequirementStatus) -> str:
    """Generate human-readable status text."""
    status_map = {
        RequirementStatus.NOT_STARTED: "Not Started",
        RequirementStatus.IN_PROGRESS: "In Progress",
        RequirementStatus.COMPLETE: "Complete",
        RequirementStatus.BLOCKED: "Blocked",
    }
    return status_map.get(status, "Not Started")


def generate_prd_markdown(prd: PRDDocument) -> str:
    """
    Generate markdown from PRDDocument structure.

    Args:
        prd: PRDDocument to convert to markdown

    Returns:
        Formatted markdown string

    Example:
        >>> markdown = generate_prd_markdown(prd)
        >>> with open("PRD.md", "w") as f:
        ...     f.write(markdown)
    """
    lines = []

    # Header
    lines.append("# Product Requirements Document")
    lines.append("")

    # Original Request
    lines.append("## Original Request")
    lines.append("<!-- VERBATIM_START -->")
    lines.append(prd.original_request)
    lines.append("<!-- VERBATIM_END -->")
    lines.append("")

    # Metadata
    lines.append("## Metadata")
    lines.append(f"- **Created**: {prd.created_at.isoformat()}")
    lines.append(f"- **Last Updated**: {prd.last_updated.isoformat()}")
    lines.append(f"- **Session**: {prd.session_id}")

    stats = prd.get_completion_stats()
    status_text = "Complete" if stats["overall_percentage"] >= 100 else "In Progress"
    lines.append(f"- **Status**: {status_text}")

    if prd.project_name:
        lines.append(f"- **Project**: {prd.project_name}")
    if prd.author:
        lines.append(f"- **Author**: {prd.author}")

    lines.append("")
    lines.append("---")
    lines.append("")

    # Features
    lines.append("## Features")
    lines.append("")

    for feature in prd.features:
        lines.append(f"### {feature.id}: {feature.name}")
        lines.append(f"- **Status**: {_generate_status_checkbox(feature.status)} {_generate_status_text(feature.status)}")
        lines.append(f"- **Priority**: {feature.priority.value.title()}")
        if feature.description and feature.description != feature.name:
            lines.append(f"- **Description**: {feature.description}")
        lines.append("")

        # User Stories
        if feature.user_stories:
            lines.append("#### User Stories")
            lines.append("")

            for story in feature.user_stories:
                lines.append(f"##### {story.id}: {story.title}")
                lines.append(f"- **Status**: {_generate_status_checkbox(story.status)} {_generate_status_text(story.status)}")
                lines.append(f"- **As a**: {story.as_a}")
                lines.append(f"- **I want**: {story.i_want}")
                lines.append(f"- **So that**: {story.so_that}")
                lines.append("")

                # Acceptance Criteria
                if story.acceptance_criteria:
                    lines.append("###### Acceptance Criteria")
                    lines.append("")
                    for criterion in story.acceptance_criteria:
                        checkbox = _generate_status_checkbox(criterion.status)
                        lines.append(f"- {criterion.id}: {checkbox} {criterion.description}")
                    lines.append("")

        # Tasks
        if feature.tasks:
            lines.append("#### Tasks")
            lines.append("")
            for task in feature.tasks:
                checkbox = _generate_status_checkbox(task.status)
                links = []
                if task.linked_stories:
                    links.extend(task.linked_stories)
                if task.linked_criteria:
                    links.extend(task.linked_criteria)

                link_text = f" (Linked to: {', '.join(links)})" if links else ""
                lines.append(f"- {task.id}: {checkbox} {task.description}{link_text}")
            lines.append("")

    # Progress Summary
    lines.append("---")
    lines.append("")
    lines.append("## Progress Summary")

    stats = prd.get_completion_stats()
    lines.append(
        f"- **Features**: {stats['features']['complete']}/{stats['features']['total']} "
        f"({stats['features']['percentage']:.0f}%)"
    )
    lines.append(
        f"- **User Stories**: {stats['user_stories']['complete']}/{stats['user_stories']['total']} "
        f"({stats['user_stories']['percentage']:.0f}%)"
    )
    lines.append(
        f"- **Acceptance Criteria**: {stats['acceptance_criteria']['complete']}/{stats['acceptance_criteria']['total']} "
        f"({stats['acceptance_criteria']['percentage']:.0f}%)"
    )
    lines.append(
        f"- **Tasks**: {stats['tasks']['complete']}/{stats['tasks']['total']} "
        f"({stats['tasks']['percentage']:.0f}%)"
    )
    lines.append("")

    return "\n".join(lines)


# ============================================================================
# Requirement Extraction from Raw Text
# ============================================================================


def extract_requirements_from_text(
    raw_text: str,
    project_name: Optional[str] = None,
    session_id: Optional[str] = None,
) -> PRDDocument:
    """
    Extract requirements from unstructured text.

    This is a helper for the PM agent to use when initially
    parsing a user's request into structured requirements.

    The function uses heuristics to identify features, user stories,
    and tasks from natural language descriptions.

    Args:
        raw_text: Unstructured requirements text
        project_name: Optional project name
        session_id: Optional session ID

    Returns:
        PRDDocument with auto-generated IDs

    Example:
        >>> text = '''
        ... Build a dark mode feature for the app.
        ... Users should be able to toggle between light and dark themes.
        ... The preference should persist across sessions.
        ... '''
        >>> prd = extract_requirements_from_text(text)
    """
    id_gen = IDGenerator()
    features = []

    # Split into paragraphs or sentences for analysis
    paragraphs = [p.strip() for p in raw_text.split("\n\n") if p.strip()]

    # If text is short, treat it as a single feature
    if len(raw_text) < 500 or len(paragraphs) <= 2:
        # Create a single feature from the text
        feature = Feature(
            id=id_gen.next_feature_id(),
            name=_extract_feature_name(raw_text),
            description=raw_text.strip(),
            priority=Priority.HIGH,
            status=RequirementStatus.NOT_STARTED,
        )

        # Try to extract user stories from the text
        stories = _extract_user_stories_from_text(raw_text, id_gen)
        if stories:
            feature.user_stories = stories
        else:
            # Create a default user story
            story = UserStory(
                id=id_gen.next_story_id(),
                title=feature.name,
                as_a="user",
                i_want=feature.description[:100] + "..." if len(feature.description) > 100 else feature.description,
                so_that="the feature works as expected",
                status=RequirementStatus.NOT_STARTED,
            )
            # Add default acceptance criterion
            story.acceptance_criteria.append(
                AcceptanceCriterion(
                    id=id_gen.next_criterion_id(),
                    description="Feature is implemented and tested",
                    status=RequirementStatus.NOT_STARTED,
                )
            )
            feature.user_stories.append(story)

        features.append(feature)
    else:
        # Try to identify multiple features
        for para in paragraphs:
            if len(para) < 20:
                continue

            feature = Feature(
                id=id_gen.next_feature_id(),
                name=_extract_feature_name(para),
                description=para,
                priority=Priority.MEDIUM,
                status=RequirementStatus.NOT_STARTED,
            )

            # Create a user story for this paragraph
            story = UserStory(
                id=id_gen.next_story_id(),
                title=feature.name,
                as_a="user",
                i_want=para[:100] + "..." if len(para) > 100 else para,
                so_that="the requirement is satisfied",
                status=RequirementStatus.NOT_STARTED,
            )
            story.acceptance_criteria.append(
                AcceptanceCriterion(
                    id=id_gen.next_criterion_id(),
                    description="Requirement is implemented and verified",
                    status=RequirementStatus.NOT_STARTED,
                )
            )
            feature.user_stories.append(story)
            features.append(feature)

    now = datetime.now(timezone.utc)

    return PRDDocument(
        original_request=raw_text,
        features=features,
        created_at=now,
        last_updated=now,
        session_id=session_id or f"session_{now.strftime('%Y%m%d_%H%M%S')}",
        project_name=project_name,
    )


def _extract_feature_name(text: str) -> str:
    """Extract a feature name from text."""
    # Take first sentence or first 50 chars
    first_sentence = re.split(r"[.!?]", text)[0].strip()

    # Clean up common prefixes
    prefixes_to_remove = [
        "I want to",
        "I need to",
        "Please",
        "Can you",
        "We need to",
        "Add a",
        "Add",
        "Create a",
        "Create",
        "Build a",
        "Build",
        "Implement a",
        "Implement",
    ]

    result = first_sentence
    for prefix in prefixes_to_remove:
        if result.lower().startswith(prefix.lower()):
            result = result[len(prefix) :].strip()
            break

    # Capitalize first letter
    if result:
        result = result[0].upper() + result[1:]

    # Truncate if too long
    if len(result) > 60:
        result = result[:57] + "..."

    return result or "Feature"


def _extract_user_stories_from_text(text: str, id_gen: IDGenerator) -> List[UserStory]:
    """Try to extract user stories from text using common patterns."""
    stories = []

    # Look for "As a... I want... so that..." patterns
    pattern = r"[Aa]s\s+a[n]?\s+([^,]+),?\s+[Ii]\s+want\s+(?:to\s+)?([^,]+),?\s+so\s+that\s+([^.]+)"
    matches = re.findall(pattern, text)

    for match in matches:
        role, want, benefit = match
        story = UserStory(
            id=id_gen.next_story_id(),
            title=want[:50].strip(),
            as_a=role.strip(),
            i_want=want.strip(),
            so_that=benefit.strip(),
            status=RequirementStatus.NOT_STARTED,
        )
        story.acceptance_criteria.append(
            AcceptanceCriterion(
                id=id_gen.next_criterion_id(),
                description=f"User can {want.strip().lower()}",
                status=RequirementStatus.NOT_STARTED,
            )
        )
        stories.append(story)

    return stories


# ============================================================================
# Validation
# ============================================================================


def validate_prd_structure(prd: PRDDocument) -> Tuple[bool, List[str]]:
    """
    Validate PRD structure for completeness and consistency.

    Args:
        prd: PRDDocument to validate

    Returns:
        Tuple of (is_valid, list_of_error_messages)

    Example:
        >>> is_valid, errors = validate_prd_structure(prd)
        >>> if not is_valid:
        ...     for error in errors:
        ...         print(f"Error: {error}")
    """
    return prd.validate_structure()


__all__ = [
    "parse_prd_markdown",
    "generate_prd_markdown",
    "extract_requirements_from_text",
    "validate_prd_structure",
]
