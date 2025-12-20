"""
PRD State Manager - Persistence and Updates for PRD Documents

This module handles loading, saving, and updating PRD documents including:
- Loading PRD from .subagent/requirements/PRD.md
- Atomic saves with optional backup
- Marking items complete with status propagation
- Getting incomplete items and coverage reports

Usage:
    from src.core.prd_state import load_prd, save_prd, mark_item_complete

    # Load existing PRD
    prd = load_prd()
    if prd:
        print(f"Loaded PRD with {len(prd.features)} features")

    # Mark item complete
    prd = mark_item_complete("AC001", "orchestrator-agent")

    # Get remaining work
    incomplete = get_incomplete_items()
"""

import logging
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict, Any, Union

from src.core import config
from src.core.prd_schemas import (
    PRDDocument,
    Feature,
    UserStory,
    AcceptanceCriterion,
    Task,
    RequirementStatus,
)
from src.core.prd_parser import parse_prd_markdown, generate_prd_markdown

logger = logging.getLogger(__name__)


# ============================================================================
# Global State
# ============================================================================

_prd_cache: Optional[PRDDocument] = None


# ============================================================================
# Load and Save Operations
# ============================================================================


def load_prd(
    force_reload: bool = False,
    session_id: Optional[str] = None,
) -> Optional[PRDDocument]:
    """
    Load PRD from .subagent/requirements/PRD.md

    Args:
        force_reload: Force reload from disk (ignore cache)
        session_id: Optional session ID for logging

    Returns:
        PRDDocument if file exists, None otherwise

    Example:
        >>> prd = load_prd()
        >>> if prd:
        ...     print(f"Loaded {len(prd.features)} features")
    """
    global _prd_cache

    if _prd_cache is not None and not force_reload:
        return _prd_cache

    cfg = config.get_config()
    prd_path = cfg.get_prd_path()

    if not prd_path.exists():
        logger.debug("No PRD file found at %s", prd_path)
        return None

    try:
        content = prd_path.read_text(encoding="utf-8")
        prd = parse_prd_markdown(content)
        _prd_cache = prd
        logger.info("Loaded PRD from %s with %d features", prd_path, len(prd.features))
        return prd
    except Exception as e:
        logger.error("Failed to load PRD from %s: %s", prd_path, e, exc_info=True)
        return None


def save_prd(
    prd: PRDDocument,
    create_backup: Optional[bool] = None,
) -> Path:
    """
    Save PRD to .subagent/requirements/PRD.md

    Performs atomic write with optional backup of previous version.

    Args:
        prd: PRDDocument to save
        create_backup: Create backup of previous version (default: from config)

    Returns:
        Path to saved PRD file

    Example:
        >>> path = save_prd(prd)
        >>> print(f"Saved to {path}")
    """
    global _prd_cache

    cfg = config.get_config()
    prd_path = cfg.get_prd_path()

    # Determine if we should create backup
    if create_backup is None:
        create_backup = cfg.prd_auto_create_backup

    # Create backup of existing file
    if create_backup and prd_path.exists():
        backup_path = cfg.get_prd_backup_path()
        try:
            shutil.copy2(prd_path, backup_path)
            logger.debug("Created PRD backup at %s", backup_path)
        except Exception as e:
            logger.warning("Failed to create PRD backup: %s", e, exc_info=True)

    # Update last_updated timestamp
    prd.last_updated = datetime.now(timezone.utc)

    # Generate markdown
    markdown = generate_prd_markdown(prd)

    # Atomic write: write to temp file, then rename
    temp_path = prd_path.with_suffix(".md.tmp")
    try:
        # Ensure directory exists
        prd_path.parent.mkdir(parents=True, exist_ok=True)

        # Write to temp file
        temp_path.write_text(markdown, encoding="utf-8")

        # Atomic rename
        temp_path.replace(prd_path)

        # Update cache
        _prd_cache = prd

        logger.info("Saved PRD to %s", prd_path)
        return prd_path

    except Exception as e:
        # Clean up temp file on failure
        if temp_path.exists():
            temp_path.unlink()
        logger.error("Failed to save PRD to %s: %s", prd_path, e, exc_info=True)
        raise


def clear_prd_cache():
    """Clear the PRD cache (for testing or force reload)."""
    global _prd_cache
    _prd_cache = None


# ============================================================================
# Item Completion
# ============================================================================


def mark_item_complete(
    item_id: str,
    completed_by: str,
    notes: Optional[str] = None,
    propagate_to_parent: bool = True,
) -> Optional[PRDDocument]:
    """
    Mark a requirement item as complete.

    Updates:
    - Item status to COMPLETE
    - completed_at timestamp
    - completed_by field
    - Parent item status if all children complete (when propagate_to_parent=True)
    - PRD last_updated timestamp

    Args:
        item_id: ID of item to mark complete (F001, US001, AC001, T001)
        completed_by: Agent or user who completed this
        notes: Optional notes about completion
        propagate_to_parent: Auto-complete parent when all children done

    Returns:
        Updated PRDDocument, or None if PRD not found

    Example:
        >>> prd = mark_item_complete("AC001", "orchestrator-agent")
        >>> print(f"Item AC001 marked complete")
    """
    prd = load_prd()
    if prd is None:
        logger.warning("Cannot mark item complete - no PRD loaded")
        return None

    now = datetime.now(timezone.utc)

    # Find and update the item
    item_found = False

    for feature in prd.features:
        # Check if this is the feature
        if feature.id == item_id:
            feature.status = RequirementStatus.COMPLETE
            feature.completed_at = now
            feature.completed_by = completed_by
            if notes:
                feature.notes = notes
            item_found = True
            logger.info("Marked feature %s complete by %s", item_id, completed_by)
            break

        # Check user stories
        for story in feature.user_stories:
            if story.id == item_id:
                story.status = RequirementStatus.COMPLETE
                story.completed_at = now
                story.completed_by = completed_by
                if notes:
                    story.notes = notes
                item_found = True
                logger.info("Marked user story %s complete by %s", item_id, completed_by)

                # Check if feature should be auto-completed
                if propagate_to_parent and feature.is_all_stories_complete():
                    feature.status = RequirementStatus.COMPLETE
                    feature.completed_at = now
                    feature.completed_by = f"auto ({completed_by})"
                    logger.info(
                        "Auto-completed feature %s (all stories complete)", feature.id
                    )
                break

            # Check acceptance criteria
            for criterion in story.acceptance_criteria:
                if criterion.id == item_id:
                    criterion.status = RequirementStatus.COMPLETE
                    criterion.completed_at = now
                    criterion.completed_by = completed_by
                    if notes:
                        criterion.notes = notes
                    item_found = True
                    logger.info(
                        "Marked acceptance criterion %s complete by %s",
                        item_id,
                        completed_by,
                    )

                    # Check if story should be auto-completed
                    if propagate_to_parent and story.is_all_criteria_complete():
                        story.status = RequirementStatus.COMPLETE
                        story.completed_at = now
                        story.completed_by = f"auto ({completed_by})"
                        logger.info(
                            "Auto-completed user story %s (all criteria complete)",
                            story.id,
                        )

                        # Check if feature should be auto-completed
                        if feature.is_all_stories_complete():
                            feature.status = RequirementStatus.COMPLETE
                            feature.completed_at = now
                            feature.completed_by = f"auto ({completed_by})"
                            logger.info(
                                "Auto-completed feature %s (all stories complete)",
                                feature.id,
                            )
                    break

            if item_found:
                break

        # Check tasks
        for task in feature.tasks:
            if task.id == item_id:
                task.status = RequirementStatus.COMPLETE
                task.completed_at = now
                task.completed_by = completed_by
                if notes:
                    task.notes = notes
                item_found = True
                logger.info("Marked task %s complete by %s", item_id, completed_by)
                break

        if item_found:
            break

    if not item_found:
        logger.warning("Item %s not found in PRD", item_id)
        return prd

    # Save updated PRD
    save_prd(prd)

    # Log completion event if activity logger is available
    try:
        from src.core.activity_logger import log_validation

        log_validation(
            agent=completed_by,
            task=item_id,
            validation_type="requirement_completion",
            checks={item_id: "pass"},
            result="pass",
            metrics={"item_type": _get_item_type(item_id)},
        )
    except ImportError:
        pass  # Activity logger not available

    return prd


def mark_item_in_progress(
    item_id: str,
    assigned_to: Optional[str] = None,
) -> Optional[PRDDocument]:
    """
    Mark a requirement item as in progress.

    Args:
        item_id: ID of item to mark in progress
        assigned_to: Agent assigned to this item

    Returns:
        Updated PRDDocument, or None if PRD not found
    """
    prd = load_prd()
    if prd is None:
        return None

    for feature in prd.features:
        if feature.id == item_id:
            feature.status = RequirementStatus.IN_PROGRESS
            break

        for story in feature.user_stories:
            if story.id == item_id:
                story.status = RequirementStatus.IN_PROGRESS
                break

            for criterion in story.acceptance_criteria:
                if criterion.id == item_id:
                    criterion.status = RequirementStatus.IN_PROGRESS
                    break

        for task in feature.tasks:
            if task.id == item_id:
                task.status = RequirementStatus.IN_PROGRESS
                if assigned_to:
                    task.assigned_to = assigned_to
                break

    save_prd(prd)
    return prd


def _get_item_type(item_id: str) -> str:
    """Get item type from ID prefix."""
    if item_id.startswith("F"):
        return "feature"
    elif item_id.startswith("US"):
        return "story"
    elif item_id.startswith("AC"):
        return "criterion"
    elif item_id.startswith("T"):
        return "task"
    return "unknown"


# ============================================================================
# Query Operations
# ============================================================================


def get_incomplete_items(
    item_type: Optional[str] = None,
    priority: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Get all incomplete items, optionally filtered.

    Args:
        item_type: "feature", "story", "criterion", "task", or None for all
        priority: "high", "medium", "low", or None for all

    Returns:
        List of dicts with item info

    Example:
        >>> incomplete = get_incomplete_items(item_type="criterion")
        >>> print(f"Found {len(incomplete)} incomplete acceptance criteria")
    """
    prd = load_prd()
    if prd is None:
        return []

    items = prd.get_incomplete_items(item_type)

    # Filter by priority if specified
    if priority:
        items = [item for item in items if item.get("priority") == priority]

    return items


def get_item_by_id(item_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a specific item by its ID.

    Args:
        item_id: The ID to look up (F001, US001, AC001, T001)

    Returns:
        Dict with item info, or None if not found
    """
    prd = load_prd()
    if prd is None:
        return None

    item = prd.get_item_by_id(item_id)
    if item is None:
        return None

    # Convert to dict representation
    if hasattr(item, "model_dump"):
        return item.model_dump()
    return None


def get_completion_stats() -> Dict[str, Any]:
    """
    Get completion statistics for the current PRD.

    Returns:
        Dict with completion stats, or empty dict if no PRD
    """
    prd = load_prd()
    if prd is None:
        return {}

    return prd.get_completion_stats()


def get_coverage_report() -> Dict[str, Any]:
    """
    Generate coverage report showing requirement reference status.

    Returns:
        Dict containing:
        - total_items: Total trackable items
        - referenced_count: Items that have been referenced
        - unreferenced_items: List of item IDs not yet referenced
        - coverage_percentage: Percentage of items referenced
    """
    prd = load_prd()
    if prd is None:
        return {
            "total_items": 0,
            "referenced_count": 0,
            "unreferenced_items": [],
            "coverage_percentage": 0.0,
        }

    all_items = prd.get_all_items()
    total = len(all_items)

    # For now, track referenced items via reference_count on PRD
    # In the future, this could be tracked per-item
    referenced = prd.reference_count if prd.reference_count > 0 else 0

    return {
        "total_items": total,
        "referenced_count": min(referenced, total),
        "unreferenced_items": list(all_items.keys()) if referenced == 0 else [],
        "coverage_percentage": (min(referenced, total) / total * 100) if total > 0 else 0.0,
        "prd_reference_count": prd.reference_count,
        "last_referenced_at": prd.last_referenced_at.isoformat() if prd.last_referenced_at else None,
    }


# ============================================================================
# PRD Creation
# ============================================================================


def create_prd_from_request(
    request_text: str,
    project_name: Optional[str] = None,
    session_id: Optional[str] = None,
    author: Optional[str] = None,
) -> PRDDocument:
    """
    Create a new PRD from a user request.

    Uses the prd_parser to extract requirements from unstructured text.

    Args:
        request_text: User's original request
        project_name: Optional project name
        session_id: Optional session ID
        author: Optional author name

    Returns:
        Created PRDDocument (also saved to disk)

    Example:
        >>> prd = create_prd_from_request(
        ...     "Build a dark mode feature with toggle support",
        ...     project_name="MyApp"
        ... )
    """
    from src.core.prd_parser import extract_requirements_from_text

    prd = extract_requirements_from_text(
        request_text,
        project_name=project_name,
        session_id=session_id,
    )

    if author:
        prd.author = author

    # Save to disk
    save_prd(prd, create_backup=False)  # No backup for new PRD

    logger.info(
        "Created new PRD with %d features from request",
        len(prd.features),
    )

    return prd


def prd_exists() -> bool:
    """Check if a PRD file exists."""
    cfg = config.get_config()
    return cfg.get_prd_path().exists()


def increment_reference_count() -> Optional[PRDDocument]:
    """
    Increment the PRD reference count and update last_referenced_at.

    Called when a reference check surfaces requirements.

    Returns:
        Updated PRDDocument, or None if no PRD exists
    """
    prd = load_prd()
    if prd is None:
        return None

    prd.reference_count += 1
    prd.last_referenced_at = datetime.now(timezone.utc)

    # Save without creating backup for reference count updates
    save_prd(prd, create_backup=False)

    return prd


__all__ = [
    "load_prd",
    "save_prd",
    "clear_prd_cache",
    "mark_item_complete",
    "mark_item_in_progress",
    "get_incomplete_items",
    "get_item_by_id",
    "get_completion_stats",
    "get_coverage_report",
    "create_prd_from_request",
    "prd_exists",
    "increment_reference_count",
]
