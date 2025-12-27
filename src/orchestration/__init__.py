"""
Orchestration Layer - Multi-Agent Coordination with Cost Optimization

This module provides the complete orchestration infrastructure for the
SubAgentTracking platform, including:

- Model Router: Intelligent model tier selection (Weak/Base/Strong)
- Agent Coordinator: Scout-Plan-Build workflow orchestration
- Context Optimizer: R&D Framework for 30-50% token reduction
- Model Router Subscriber: Event-driven automatic routing

Links Back To: Main Plan → Phase 2 (Complete)

Usage:
    >>> from src.orchestration import initialize_orchestration, shutdown_orchestration
    >>> initialize_orchestration()
    >>> # Use coordinated workflows with automatic cost optimization
    >>> shutdown_orchestration()

Cost Optimization Targets:
- Model routing: 40-60% cost reduction via smart tier selection
- Context optimization: 30-50% token savings
- Combined: Up to 70-80% cost reduction on appropriate tasks
"""

from typing import Optional
import logging

from src.orchestration.model_router import (
    ModelRouter,
    initialize_model_router,
    get_model_router,
    shutdown_model_router
)
from src.orchestration.agent_coordinator import (
    AgentCoordinator,
    initialize_agent_coordinator,
    get_agent_coordinator,
    shutdown_agent_coordinator,
    WorkflowPhase,
    AgentTask,
    AgentStatus
)
from src.orchestration.context_optimizer import (
    ContextOptimizer,
    initialize_context_optimizer,
    get_context_optimizer,
    shutdown_context_optimizer
)
from src.orchestration.model_router_subscriber import (
    ModelRouterSubscriber,
    initialize_model_router_subscriber,
    get_model_router_subscriber,
    shutdown_model_router_subscriber
)
from src.orchestration.agent_spawner import AgentSpawner
from src.orchestration.agent_monitor import AgentMonitor
from src.orchestration.agent_lifecycle import AgentLifecycle
from src.orchestration.agent_executor import AgentExecutor
from src.orchestration.agent_runtime import AgentRuntimeManager, get_agent_runtime_manager
from src.orchestration.permissions import PermissionManager, PermissionProfile, PermissionDecision
from src.orchestration.tool_proxy import ToolProxy, ToolResult
from src.orchestration.file_tools import FileToolProxy
from src.orchestration.test_protection import (
    is_test_path,
    detect_test_modifications,
    list_modified_paths,
    assert_tests_unmodified,
)

logger = logging.getLogger(__name__)

__all__ = [
    # Model Router
    'ModelRouter',
    'initialize_model_router',
    'get_model_router',
    'shutdown_model_router',

    # Agent Coordinator
    'AgentCoordinator',
    'initialize_agent_coordinator',
    'get_agent_coordinator',
    'shutdown_agent_coordinator',
    'WorkflowPhase',
    'AgentTask',
    'AgentStatus',

    # Context Optimizer
    'ContextOptimizer',
    'initialize_context_optimizer',
    'get_context_optimizer',
    'shutdown_context_optimizer',

    # Model Router Subscriber
    'ModelRouterSubscriber',
    'initialize_model_router_subscriber',
    'get_model_router_subscriber',
    'shutdown_model_router_subscriber',

    # Agent lifecycle helpers
    'AgentSpawner',
    'AgentMonitor',
    'AgentLifecycle',
    'AgentExecutor',
    'AgentRuntimeManager',
    'get_agent_runtime_manager',
    'PermissionManager',
    'PermissionProfile',
    'PermissionDecision',
    'ToolProxy',
    'ToolResult',
    'FileToolProxy',
    'is_test_path',
    'detect_test_modifications',
    'list_modified_paths',
    'assert_tests_unmodified',

    # Unified initialization
    'initialize_orchestration',
    'shutdown_orchestration',
    'get_orchestration_stats'
]


def initialize_orchestration() -> dict:
    """
    Initialize all orchestration components.

    This is the recommended way to set up the orchestration layer.
    It initializes:
    1. Model Router (intelligent tier selection)
    2. Agent Coordinator (Scout-Plan-Build workflows)
    3. Context Optimizer (R&D framework)
    4. Model Router Subscriber (event-driven routing)

    Returns:
        Dictionary with all initialized components

    Example:
        >>> components = initialize_orchestration()
        >>> router = components['router']
        >>> coordinator = components['coordinator']
    """
    logger.info("Initializing orchestration layer...")

    # Initialize model router
    router = initialize_model_router()
    logger.info("✓ Model router initialized")

    # Initialize agent coordinator
    coordinator = initialize_agent_coordinator()
    logger.info("✓ Agent coordinator initialized")

    # Initialize context optimizer
    optimizer = initialize_context_optimizer()
    logger.info("✓ Context optimizer initialized")

    # Initialize model router subscriber (event integration)
    subscriber = initialize_model_router_subscriber(router=router)
    logger.info("✓ Model router subscriber initialized")

    logger.info("Orchestration layer initialization complete")

    return {
        'router': router,
        'coordinator': coordinator,
        'optimizer': optimizer,
        'subscriber': subscriber
    }


def shutdown_orchestration() -> None:
    """
    Shutdown all orchestration components.

    Cleans up all global instances and resources.

    Example:
        >>> shutdown_orchestration()
    """
    logger.info("Shutting down orchestration layer...")

    shutdown_model_router_subscriber()
    logger.info("✓ Model router subscriber shutdown")

    shutdown_context_optimizer()
    logger.info("✓ Context optimizer shutdown")

    shutdown_agent_coordinator()
    logger.info("✓ Agent coordinator shutdown")

    shutdown_model_router()
    logger.info("✓ Model router shutdown")

    logger.info("Orchestration layer shutdown complete")


def get_orchestration_stats() -> dict:
    """
    Get comprehensive statistics from all orchestration components.

    Returns:
        Dictionary with statistics from:
        - Model router (routing decisions, tier distribution)
        - Agent coordinator (workflows executed, phase times)
        - Context optimizer (token savings, optimization times)
        - Model router subscriber (session routing stats)

    Example:
        >>> stats = get_orchestration_stats()
        >>> print(f"Cost savings: {stats['estimated_cost_savings_percent']:.1f}%")
    """
    stats = {
        'router': None,
        'coordinator': None,
        'optimizer': None,
        'subscriber': None,
        'estimated_cost_savings_percent': 0.0
    }

    # Get router stats
    router = get_model_router()
    if router:
        stats['router'] = router.get_stats()

    # Get coordinator stats
    coordinator = get_agent_coordinator()
    if coordinator:
        stats['coordinator'] = coordinator.get_stats()

    # Get optimizer stats
    optimizer = get_context_optimizer()
    if optimizer:
        stats['optimizer'] = optimizer.get_stats()

    # Calculate estimated cost savings
    if stats['router'] and stats['optimizer']:
        # Model routing saves 40-60% via tier selection
        router_savings = stats['router'].get('free_tier_percentage', 0.0) * 50  # Conservative estimate

        # Context optimization saves 30-50% on tokens
        optimizer_savings = stats['optimizer'].get('avg_savings_percent', 0.0)

        # Combined savings (not simply additive due to compounding)
        # If we save 50% on model costs and 40% on tokens, total savings:
        # Original cost: C
        # After model routing: 0.5C
        # After context optimization on remaining: 0.5C * 0.6 = 0.3C
        # Total savings: 70%
        combined_savings = 100 * (1 - (1 - router_savings/100) * (1 - optimizer_savings/100))

        stats['estimated_cost_savings_percent'] = combined_savings

    return stats
