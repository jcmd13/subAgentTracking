"""
Observability Platform - Real-Time Monitoring and Analytics

This module provides the unified API for the observability platform,
including real-time event streaming, metrics aggregation, and analytics.

Links Back To: Main Plan � Phase 3 (Observability Platform)

Usage:
    >>> from src.observability import initialize_observability, get_observability_stats
    >>>
    >>> # Initialize all observability components
    >>> components = initialize_observability()
    >>> #  Real-time monitor initialized (WebSocket on localhost:8765)
    >>> #  Metrics aggregator initialized (1min, 5min, 15min windows)
    >>>
    >>> # Get current statistics
    >>> stats = get_observability_stats()
    >>> print(f"Active connections: {stats['monitor']['active_connections']}")
    >>> print(f"Events/sec: {stats['metrics']['1min']['events_per_second']}")
    >>>
    >>> # Cleanup
    >>> shutdown_observability()

Components:
- RealTimeMonitor: WebSocket server for event streaming
- MetricsAggregator: Rolling window statistics
- (Future) AnalyticsEngine: Pattern detection and insights
- (Future) FleetMonitor: Multi-agent visualization
"""

import logging
from typing import Optional, Dict, Any

# Real-time monitoring
from src.observability.realtime_monitor import (
    RealtimeMonitor,
    FilterType,
    EventFilter,
    initialize_realtime_monitor,
    get_realtime_monitor,
    shutdown_realtime_monitor
)

# Metrics aggregation
from src.observability.metrics_aggregator import (
    MetricsAggregator,
    WindowSize,
    MetricsSnapshot,
    initialize_metrics_aggregator,
    get_metrics_aggregator,
    shutdown_metrics_aggregator
)

# Dashboard server
from src.observability.dashboard_server import (
    DashboardServer,
    start_dashboard_server,
    get_dashboard_server,
    stop_dashboard_server
)

# Analytics and insights
from src.observability.analytics_engine import (
    AnalyticsEngine,
    get_analytics_engine,
    reset_analytics_engine
)

from src.observability.insight_engine import (
    InsightEngine,
    get_insight_engine,
    reset_insight_engine
)

# Fleet monitoring
from src.observability.fleet_monitor import (
    FleetMonitor,
    get_fleet_monitor,
    initialize_fleet_monitor,
    shutdown_fleet_monitor
)

logger = logging.getLogger(__name__)


__all__ = [
    # Real-time monitoring
    'RealtimeMonitor',
    'FilterType',
    'EventFilter',
    'initialize_realtime_monitor',
    'get_realtime_monitor',
    'shutdown_realtime_monitor',

    # Metrics aggregation
    'MetricsAggregator',
    'WindowSize',
    'MetricsSnapshot',
    'initialize_metrics_aggregator',
    'get_metrics_aggregator',
    'shutdown_metrics_aggregator',

    # Dashboard server
    'DashboardServer',
    'start_dashboard_server',
    'get_dashboard_server',
    'stop_dashboard_server',

    # Unified API
    'initialize_observability',
    'shutdown_observability',
    'get_observability_stats',
]


# ============================================================================
# Unified Observability API
# ============================================================================

def initialize_observability(
    # Real-time monitor config
    websocket_host: str = "localhost",
    websocket_port: int = 8765,
    max_connections: int = 100,

    # Metrics aggregator config
    window_sizes: Optional[list] = None,
    max_records: int = 10000,

    # Dashboard server config
    dashboard_port: int = 8080,
    start_dashboard: bool = False,

    # Control flags
    start_websocket: bool = False,  # Don't auto-start WebSocket (requires await)
    auto_subscribe: bool = True
) -> Dict[str, Any]:
    """
    Initialize all observability components.

    This is the recommended way to set up the observability platform.
    It initializes:
    1. Real-time monitor (WebSocket server for event streaming)
    2. Metrics aggregator (Rolling window statistics)
    3. Dashboard server (HTTP server for web UI)

    Args:
        websocket_host: WebSocket server host (default: "localhost")
        websocket_port: WebSocket server port (default: 8765)
        max_connections: Maximum concurrent WebSocket connections (default: 100)
        window_sizes: Time windows for metrics (default: [60, 300, 900])
        max_records: Maximum records per window (default: 10000)
        dashboard_port: Dashboard HTTP server port (default: 8080)
        start_dashboard: Auto-start dashboard server (default: False)
        start_websocket: Auto-start WebSocket server (default: False, requires async)
        auto_subscribe: Auto-subscribe to event bus (default: True)

    Returns:
        Dictionary with initialized components:
        {
            'monitor': RealtimeMonitor instance,
            'aggregator': MetricsAggregator instance,
            'dashboard': DashboardServer instance (if start_dashboard=True)
        }

    Example:
        >>> # Initialize with dashboard
        >>> components = initialize_observability(start_dashboard=True)
        >>> # Dashboard: http://localhost:8080
        >>>
        >>> # Start WebSocket server (async)
        >>> import asyncio
        >>> asyncio.run(components['monitor'].start())
        >>>
        >>> # Get stats
        >>> stats = get_observability_stats()
        >>>
        >>> # Cleanup
        >>> asyncio.run(components['monitor'].stop())
        >>> shutdown_observability()
    """
    logger.info("Initializing observability platform...")

    # Initialize metrics aggregator (with event bus subscription)
    aggregator = initialize_metrics_aggregator(
        window_sizes=window_sizes,
        max_records=max_records
    )
    logger.info(" Metrics aggregator initialized")

    # Initialize real-time monitor (WebSocket server)
    monitor = initialize_realtime_monitor(
        host=websocket_host,
        port=websocket_port,
        max_connections=max_connections,
        auto_subscribe=auto_subscribe
    )
    logger.info(f" Real-time monitor initialized (ws://{websocket_host}:{websocket_port})")

    if start_websocket:
        logger.warning(
            "start_websocket=True requires async context. "
            "Call await components['monitor'].start() manually."
        )

    logger.info("Observability platform initialization complete")

    # Initialize dashboard server (optional)
    result = {
        'monitor': monitor,
        'aggregator': aggregator
    }

    if start_dashboard:
        dashboard = start_dashboard_server(
            host=websocket_host,
            port=dashboard_port
        )
        result['dashboard'] = dashboard
        logger.info(f" Dashboard server started (http://{websocket_host}:{dashboard_port})")

    return result


def shutdown_observability() -> None:
    """
    Shutdown all observability components.

    Cleans up all global instances and resources.
    Note: WebSocket server must be stopped separately with await monitor.stop()

    Example:
        >>> # Stop WebSocket if running
        >>> monitor = get_realtime_monitor()
        >>> if monitor and monitor.running:
        >>>     import asyncio
        >>>     asyncio.run(monitor.stop())
        >>>
        >>> # Shutdown all components
        >>> shutdown_observability()
    """
    logger.info("Shutting down observability platform...")

    # Shutdown real-time monitor
    shutdown_realtime_monitor()
    logger.info(" Real-time monitor shutdown")

    # Shutdown metrics aggregator
    shutdown_metrics_aggregator()
    logger.info(" Metrics aggregator shutdown")

    logger.info("Observability platform shutdown complete")


def get_observability_stats() -> Dict[str, Any]:
    """
    Get comprehensive statistics from all observability components.

    Returns:
        Dictionary with statistics from:
        - Real-time monitor (connections, events streamed)
        - Metrics aggregator (per-window statistics)

    Example:
        >>> stats = get_observability_stats()
        >>>
        >>> # Monitor stats
        >>> print(f"Active connections: {stats['monitor']['active_connections']}")
        >>> print(f"Total events streamed: {stats['monitor']['total_events_streamed']}")
        >>>
        >>> # Metrics stats (per window)
        >>> one_min_stats = stats['metrics']['windows']['60']
        >>> print(f"Events/sec (1min): {one_min_stats.events_per_second:.2f}")
        >>> print(f"Agents active: {one_min_stats.agents_active}")
        >>>
        >>> # Cumulative stats
        >>> cumulative = stats['metrics']['cumulative']
        >>> print(f"Total events: {cumulative['total_events']}")
        >>> print(f"Total tokens: {cumulative['total_tokens']}")
    """
    stats = {
        'monitor': None,
        'aggregator': None,
        'metrics': {
            'windows': {},
            'cumulative': {}
        }
    }

    # Get monitor stats
    monitor = get_realtime_monitor()
    if monitor:
        stats['monitor'] = monitor.get_stats()

    # Get aggregator stats
    aggregator = get_metrics_aggregator()
    if aggregator:
        # Get all window stats
        all_stats = aggregator.get_all_stats()
        stats['metrics']['windows'] = {
            str(window_size): {
                'timestamp': snapshot.timestamp,
                'total_events': snapshot.total_events,
                'events_by_type': snapshot.events_by_type,
                'agents_active': snapshot.agents_active,
                'agents_completed': snapshot.agents_completed,
                'agents_failed': snapshot.agents_failed,
                'workflows_active': snapshot.workflows_active,
                'workflows_completed': snapshot.workflows_completed,
                'avg_agent_duration_ms': snapshot.avg_agent_duration_ms,
                'p50_agent_duration_ms': snapshot.p50_agent_duration_ms,
                'p95_agent_duration_ms': snapshot.p95_agent_duration_ms,
                'p99_agent_duration_ms': snapshot.p99_agent_duration_ms,
                'total_tokens': snapshot.total_tokens,
                'total_cost': snapshot.total_cost,
                'events_per_second': snapshot.events_per_second,
                'agents_per_minute': snapshot.agents_per_minute,
                'tokens_per_second': snapshot.tokens_per_second,
                'cost_per_hour': snapshot.cost_per_hour
            }
            for window_size, snapshot in all_stats.items()
        }

        # Get cumulative stats
        stats['metrics']['cumulative'] = aggregator.get_cumulative_stats()

        # Store aggregator reference
        stats['aggregator'] = {
            'window_sizes': aggregator.window_sizes,
            'max_records': aggregator.max_records,
            'total_events': aggregator.cumulative_events,
            'total_tokens': aggregator.cumulative_tokens,
            'total_cost': aggregator.cumulative_cost
        }

    return stats
