"""
Dashboard HTTP Server - Serves static dashboard files

Simple HTTP server to serve the WebSocket dashboard files.
Runs alongside the RealtimeMonitor WebSocket server.

Links Back To: Main Plan → Phase 3 → Task 3.2

Usage:
    >>> from src.observability.dashboard_server import start_dashboard_server
    >>> server = start_dashboard_server(port=8080)
    >>> # Dashboard available at http://localhost:8080
    >>> # Stop with: server.shutdown()
"""

import os
import logging
from http.server import HTTPServer, SimpleHTTPRequestHandler
from threading import Thread
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


# ============================================================================
# Dashboard Request Handler
# ============================================================================

class DashboardRequestHandler(SimpleHTTPRequestHandler):
    """Custom request handler for dashboard files."""

    def __init__(self, *args, **kwargs):
        # Get dashboard directory
        dashboard_dir = Path(__file__).parent / "dashboard"
        super().__init__(*args, directory=str(dashboard_dir), **kwargs)

    def log_message(self, format, *args):
        """Override to use Python logging instead of stderr."""
        logger.info(f"{self.address_string()} - {format % args}")

    def end_headers(self):
        """Add CORS headers for development."""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

    def do_OPTIONS(self):
        """Handle OPTIONS request for CORS."""
        self.send_response(200)
        self.end_headers()


# ============================================================================
# Dashboard Server
# ============================================================================

class DashboardServer:
    """
    HTTP server for dashboard static files.

    Serves the dashboard HTML, CSS, and JavaScript files on a configurable port.
    Runs in a separate thread to avoid blocking.

    Attributes:
        host: Server host (default: "localhost")
        port: Server port (default: 8080)
        server: HTTPServer instance
        thread: Background thread running server
    """

    def __init__(self, host: str = "localhost", port: int = 8080):
        """
        Initialize dashboard server.

        Args:
            host: Server host (default: "localhost")
            port: Server port (default: 8080)
        """
        self.host = host
        self.port = port
        self.server: Optional[HTTPServer] = None
        self.thread: Optional[Thread] = None
        self.running = False

        logger.info(f"DashboardServer initialized: {host}:{port}")

    def start(self) -> None:
        """
        Start HTTP server in background thread.

        The server runs in a separate thread to avoid blocking the main thread.
        Dashboard will be available at http://{host}:{port}
        """
        if self.running:
            logger.warning("Dashboard server already running")
            return

        try:
            # Create HTTP server
            self.server = HTTPServer(
                (self.host, self.port),
                DashboardRequestHandler
            )

            # Start in background thread
            self.thread = Thread(target=self._run_server, daemon=True)
            self.thread.start()

            self.running = True

            logger.info(
                f"Dashboard server started: http://{self.host}:{self.port}"
            )
            logger.info(
                f"Open http://{self.host}:{self.port} in your browser to view dashboard"
            )

        except Exception as e:
            logger.error(f"Failed to start dashboard server: {e}")
            raise

    def _run_server(self) -> None:
        """Run server loop (called in background thread)."""
        try:
            logger.info("Dashboard server thread started")
            self.server.serve_forever()
        except Exception as e:
            logger.error(f"Dashboard server error: {e}")
        finally:
            logger.info("Dashboard server thread stopped")

    def stop(self) -> None:
        """
        Stop HTTP server and clean up resources.

        Shuts down the server gracefully and waits for the background thread
        to complete.
        """
        if not self.running:
            logger.warning("Dashboard server not running")
            return

        try:
            if self.server:
                logger.info("Stopping dashboard server...")
                self.server.shutdown()
                self.server.server_close()

            if self.thread and self.thread.is_alive():
                self.thread.join(timeout=5.0)

            self.running = False
            self.server = None
            self.thread = None

            logger.info("Dashboard server stopped")

        except Exception as e:
            logger.error(f"Error stopping dashboard server: {e}")

    def get_url(self) -> str:
        """Get dashboard URL."""
        return f"http://{self.host}:{self.port}"

    def is_running(self) -> bool:
        """Check if server is running."""
        return self.running and self.server is not None


# ============================================================================
# Global Instance Management
# ============================================================================

_server_instance: Optional[DashboardServer] = None


def start_dashboard_server(
    host: str = "localhost",
    port: int = 8080
) -> DashboardServer:
    """
    Start global dashboard server instance.

    Args:
        host: Server host (default: "localhost")
        port: Server port (default: 8080)

    Returns:
        DashboardServer instance

    Example:
        >>> server = start_dashboard_server(port=8080)
        >>> print(f"Dashboard: {server.get_url()}")
        >>> # Later: server.stop()
    """
    global _server_instance

    if _server_instance is not None and _server_instance.is_running():
        logger.warning("Dashboard server already running")
        return _server_instance

    _server_instance = DashboardServer(host=host, port=port)
    _server_instance.start()

    return _server_instance


def get_dashboard_server() -> Optional[DashboardServer]:
    """Get global dashboard server instance."""
    return _server_instance


def stop_dashboard_server() -> None:
    """Stop global dashboard server instance."""
    global _server_instance

    if _server_instance:
        _server_instance.stop()
        _server_instance = None


# ============================================================================
# CLI Entry Point
# ============================================================================

def main():
    """
    CLI entry point for dashboard server.

    Run standalone dashboard server:
        python -m src.observability.dashboard_server
    """
    import sys
    import argparse

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Parse arguments
    parser = argparse.ArgumentParser(
        description='SubAgent Tracking Dashboard Server'
    )
    parser.add_argument(
        '--host',
        default='localhost',
        help='Server host (default: localhost)'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=8080,
        help='Server port (default: 8080)'
    )
    parser.add_argument(
        '--ws-port',
        type=int,
        default=8765,
        help='WebSocket server port (default: 8765)'
    )

    args = parser.parse_args()

    # Start server
    try:
        server = start_dashboard_server(host=args.host, port=args.port)

        print("\n" + "="*70)
        print("SubAgent Tracking Dashboard Server")
        print("="*70)
        print(f"\nDashboard URL: {server.get_url()}")
        print(f"WebSocket URL: ws://{args.host}:{args.ws_port}")
        print("\nPress Ctrl+C to stop server\n")

        # Keep running until interrupted
        import time
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n\nShutting down server...")
        stop_dashboard_server()
        print("Server stopped")
        sys.exit(0)

    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
