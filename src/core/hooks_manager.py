"""
Hooks Manager - Event-Driven Automation System

Enables pre/post hooks for event interception and automation.
Hooks are Python scripts in `.subagent/hooks/` that can execute custom logic (legacy `.claude/hooks/` still supported)
before or after events.

Links Back To: Main Plan → Phase 1 → Task 1.6

Hook Types:
- Pre-hooks: Execute before event (can block event with DENY)
- Post-hooks: Execute after event (for side effects)
- On-error hooks: Execute when errors occur

Performance Target: <100ms total hook execution time
"""

import asyncio
import importlib.util
import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any, List, Callable
from enum import Enum
from datetime import datetime
import logging

from src.core.event_bus import Event, EventHandler, get_event_bus
from src.core.event_types import ALL_EVENT_TYPES, AGENT_INVOKED, AGENT_FAILED
from src.core.config import get_config

logger = logging.getLogger(__name__)


class HookResult(Enum):
    """Result of hook execution"""
    ALLOW = "allow"      # Allow event to proceed
    DENY = "deny"        # Block event (pre-hooks only)
    WARN = "warn"        # Log warning but allow


class HookContext:
    """
    Context object passed to hooks.

    Provides access to event data and helper functions.
    """

    def __init__(self, event: Event, config: Dict[str, Any]):
        """
        Initialize hook context.

        Args:
            event: The triggering event
            config: Project configuration
        """
        self.event = event
        self.config = config
        self.logger = logging.getLogger(f"hook.{event.event_type}")

    def get_token_usage(self) -> int:
        """
        Get current token usage from event payload.

        Returns:
            Token count (0 if not available)
        """
        return self.event.payload.get("tokens_used", 0) or self.event.payload.get("tokens_consumed", 0)

    def get_cost_total(self) -> float:
        """
        Get total cost from event payload.

        Returns:
            Cost in USD (0.0 if not available)
        """
        return self.event.payload.get("session_total", 0.0) or self.event.payload.get("cost_usd", 0.0)

    def create_snapshot(self, trigger: str) -> str:
        """
        Create a snapshot (helper for hooks).

        Args:
            trigger: Reason for snapshot

        Returns:
            Snapshot ID
        """
        try:
            from src.core.snapshot_manager import take_snapshot
            return take_snapshot(trigger=trigger)
        except Exception as e:
            self.logger.error("Failed to create snapshot from hook: %s", e, exc_info=True)
            return ""

    def send_notification(self, message: str, channel: str = "log"):
        """
        Send notification (helper for hooks).

        Args:
            message: Notification message
            channel: Channel to send to (log, slack, email, etc.)
        """
        if channel == "log":
            self.logger.info(f"[NOTIFICATION] {message}")
        else:
            # Future: Integrate with Slack, email, etc.
            self.logger.warning(f"Notification channel '{channel}' not implemented")


class HookModule:
    """
    Wrapper for a loaded hook module.
    """

    def __init__(self, execute_fn: Callable, hook_path: str):
        """
        Initialize hook module wrapper.

        Args:
            execute_fn: The execute() function from hook
            hook_path: Path to hook file
        """
        self.execute = execute_fn
        self.hook_path = hook_path
        self.hook_name = Path(hook_path).stem


class HooksManager:
    """
    Manages hook discovery, registration, and execution.

    Hooks are discovered from `.subagent/hooks/` directory and executed (legacy `.claude/hooks/` supported)
    based on event type.
    """

    def __init__(self, hooks_dir: Optional[Path] = None):
        """
        Initialize hooks manager.

        Args:
            hooks_dir: Directory containing hook scripts (default: .subagent/hooks/; legacy .claude/ supported)
        """
        config = get_config()
        self.hooks_dir = hooks_dir or (config.claude_dir / "hooks")
        self.hooks_registry: Dict[str, List[HookModule]] = {}
        self._initialized = False

    def discover_hooks(self) -> None:
        """
        Discover and load all hooks from hooks directory.

        Hooks are organized in subdirectories:
        - pre-agent-invocation/
        - post-agent-invocation/
        - on-error/
        """
        if not self.hooks_dir.exists():
            logger.info(f"Hooks directory not found: {self.hooks_dir}")
            return

        # Hook types to discover
        hook_types = [
            "pre-agent-invocation",
            "post-agent-invocation",
            "on-error"
        ]

        for hook_type in hook_types:
            hook_type_dir = self.hooks_dir / hook_type

            if not hook_type_dir.exists():
                continue

            # Find all .py files in this directory
            hook_files = sorted(hook_type_dir.glob("*.py"))

            for hook_file in hook_files:
                try:
                    hook_module = self._load_hook(str(hook_file))
                    if hook_module:
                        if hook_type not in self.hooks_registry:
                            self.hooks_registry[hook_type] = []
                        self.hooks_registry[hook_type].append(hook_module)
                        logger.info(f"Loaded hook: {hook_type}/{hook_file.name}")
                except Exception as e:
                    logger.error("Failed to load hook %s: %s", hook_file, e, exc_info=True)

        self._initialized = True

    def _load_hook(self, hook_path: str) -> Optional[HookModule]:
        """
        Dynamically load a hook Python file.

        Args:
            hook_path: Path to hook .py file

        Returns:
            HookModule or None if load failed
        """
        try:
            # Load module from file
            spec = importlib.util.spec_from_file_location("hook_module", hook_path)
            if spec is None or spec.loader is None:
                logger.error(f"Failed to load spec for {hook_path}")
                return None

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Check if module has execute() function
            if not hasattr(module, "execute"):
                logger.error(f"Hook {hook_path} missing execute() function")
                return None

            execute_fn = getattr(module, "execute")

            # Validate function signature (should accept HookContext)
            import inspect
            sig = inspect.signature(execute_fn)
            if len(sig.parameters) < 1:
                logger.error(f"Hook {hook_path} execute() must accept HookContext parameter")
                return None

            return HookModule(execute_fn, hook_path)

        except Exception as e:
            logger.error(f"Error loading hook from {hook_path}: {e}", exc_info=True)
            return None

    async def execute_hooks(self, hook_type: str, context: HookContext) -> HookResult:
        """
        Execute all hooks for a given type.

        Args:
            hook_type: Type of hooks to execute
            context: Hook context with event data

        Returns:
            HookResult (DENY if any hook denies, ALLOW otherwise)
        """
        if hook_type not in self.hooks_registry:
            return HookResult.ALLOW

        hooks = self.hooks_registry[hook_type]

        for hook in hooks:
            try:
                # Execute hook with timeout
                result = await asyncio.wait_for(
                    self._execute_single_hook(hook, context),
                    timeout=1.0  # 1 second timeout per hook
                )

                # If any hook denies, stop and return DENY
                if result == HookResult.DENY:
                    logger.warning(f"Hook {hook.hook_name} denied event")
                    return HookResult.DENY

            except asyncio.TimeoutError:
                logger.error("Hook %s timed out (>1s)", hook.hook_name)
            except Exception as e:
                logger.error("Hook %s failed: %s", hook.hook_name, e, exc_info=True)

        return HookResult.ALLOW

    async def _execute_single_hook(self, hook: HookModule, context: HookContext) -> HookResult:
        """
        Execute a single hook.

        Args:
            hook: Hook module to execute
            context: Hook context

        Returns:
            HookResult from hook execution
        """
        loop = asyncio.get_event_loop()

        # Run hook in executor (may be sync function)
        def run_hook():
            try:
                result = hook.execute(context)
                # Convert result to HookResult enum
                if isinstance(result, HookResult):
                    return result
                elif isinstance(result, str):
                    return HookResult(result.lower())
                else:
                    return HookResult.ALLOW
            except Exception as e:
                logger.error("Hook execution error in %s: %s", hook.hook_name, e, exc_info=True)
                return HookResult.ALLOW

        result = await loop.run_in_executor(None, run_hook)
        return result

    def get_stats(self) -> dict:
        """
        Get hooks manager statistics.

        Returns:
            Dict with hook counts by type
        """
        return {
            "initialized": self._initialized,
            "hooks_by_type": {
                hook_type: len(hooks)
                for hook_type, hooks in self.hooks_registry.items()
            },
            "total_hooks": sum(len(hooks) for hooks in self.hooks_registry.values())
        }


class HookEventSubscriber(EventHandler):
    """
    Event bus subscriber that executes hooks around events.

    Wraps event processing with pre/post hooks.
    """

    def __init__(self, hooks_manager: HooksManager):
        """
        Initialize hook event subscriber.

        Args:
            hooks_manager: HooksManager instance
        """
        self.hooks_manager = hooks_manager

        # Ensure hooks are discovered
        if not self.hooks_manager._initialized:
            self.hooks_manager.discover_hooks()

    async def handle(self, event: Event) -> None:
        """
        Handle events by executing appropriate hooks.

        For AGENT_INVOKED: Execute pre-hooks (can block)
        For AGENT_COMPLETED/FAILED: Execute post-hooks
        For AGENT_FAILED: Execute on-error hooks

        Args:
            event: Event to process
        """
        try:
            config = get_config()
            context = HookContext(event=event, config=config.__dict__)

            # Execute pre-hooks for AGENT_INVOKED (can block)
            if event.event_type == AGENT_INVOKED:
                result = await self.hooks_manager.execute_hooks("pre-agent-invocation", context)

                if result == HookResult.DENY:
                    logger.warning(f"Event blocked by pre-hook: {event.event_type}")
                    # TODO: Publish AGENT_BLOCKED event
                    return

            # Execute on-error hooks for AGENT_FAILED
            if event.event_type == AGENT_FAILED:
                await self.hooks_manager.execute_hooks("on-error", context)

            # Execute post-hooks for completed agents
            # (Note: In real system, we'd track AGENT_INVOKED → AGENT_COMPLETED pairing)
            # For now, we execute post-hooks on any agent event
            if event.event_type in [AGENT_INVOKED]:
                # Post-hooks run async (don't block)
                asyncio.create_task(
                    self.hooks_manager.execute_hooks("post-agent-invocation", context)
                )

        except Exception as e:
            logger.error("Error in hook event subscriber: %s", e, exc_info=True)

    def subscribe_to_events(self, event_bus=None) -> None:
        """
        Subscribe to relevant events on the event bus.

        Args:
            event_bus: EventBus instance (default: global bus)
        """
        if event_bus is None:
            event_bus = get_event_bus()

        # Subscribe to agent events
        event_bus.subscribe(AGENT_INVOKED, self.handle)
        event_bus.subscribe(AGENT_FAILED, self.handle)

        logger.info("Hook event subscriber registered")


# Global instances
_global_hooks_manager: Optional[HooksManager] = None
_global_hook_subscriber: Optional[HookEventSubscriber] = None


def get_hooks_manager() -> Optional[HooksManager]:
    """
    Get the global hooks manager instance.

    Returns:
        HooksManager or None if not initialized
    """
    return _global_hooks_manager


def initialize_hooks_manager(hooks_dir: Optional[Path] = None) -> HooksManager:
    """
    Initialize the global hooks manager.

    Creates manager, discovers hooks, and connects to event bus.

    Args:
        hooks_dir: Directory containing hooks (default: .subagent/hooks/; legacy .claude/ supported)

    Returns:
        HooksManager instance
    """
    global _global_hooks_manager, _global_hook_subscriber

    if _global_hooks_manager is not None:
        logger.warning("Hooks manager already initialized")
        return _global_hooks_manager

    # Create hooks manager
    _global_hooks_manager = HooksManager(hooks_dir=hooks_dir)

    # Discover hooks
    _global_hooks_manager.discover_hooks()

    # Create and register event subscriber
    _global_hook_subscriber = HookEventSubscriber(_global_hooks_manager)
    _global_hook_subscriber.subscribe_to_events()

    logger.info("Hooks manager initialized")

    return _global_hooks_manager


def shutdown_hooks_manager() -> None:
    """
    Shutdown the global hooks manager.
    """
    global _global_hooks_manager, _global_hook_subscriber

    _global_hooks_manager = None
    _global_hook_subscriber = None

    logger.info("Hooks manager shutdown complete")
