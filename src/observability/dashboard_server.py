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

import json
import logging
from http.server import HTTPServer, SimpleHTTPRequestHandler
from threading import Thread
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse, parse_qs

from src.core import activity_logger_compat as activity_logger
from src.core.approval_store import get_approval, list_approvals, record_decision

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
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS, POST')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

    def do_OPTIONS(self):
        """Handle OPTIONS request for CORS."""
        self.send_response(200)
        self.end_headers()

    def _send_json(self, status_code: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _handle_approvals_get(self, path: str, query: dict) -> None:
        parts = path.strip("/").split("/")
        if len(parts) == 2:
            status = None
            if "status" in query:
                status = query["status"][0]
            approvals = list_approvals(status=status)
            self._send_json(200, {"approvals": approvals})
            return
        if len(parts) == 3:
            approval_id = parts[2]
            approval = get_approval(approval_id)
            if not approval:
                self._send_json(404, {"error": "approval_not_found"})
                return
            self._send_json(200, {"approval": approval})
            return
        self._send_json(404, {"error": "not_found"})

    def _handle_approvals_post(self, path: str) -> None:
        parts = path.strip("/").split("/")
        if len(parts) != 4 or parts[3] != "decision":
            self._send_json(404, {"error": "not_found"})
            return

        approval_id = parts[2]
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            content_length = 0

        body = self.rfile.read(content_length) if content_length > 0 else b""
        try:
            payload = json.loads(body.decode("utf-8")) if body else {}
        except json.JSONDecodeError:
            self._send_json(400, {"error": "invalid_json"})
            return

        status = payload.get("status")
        actor = payload.get("actor")
        reason = payload.get("reason")

        try:
            record = record_decision(approval_id, status, actor=actor, reason=reason)
        except ValueError as exc:
            self._send_json(400, {"error": str(exc)})
            return

        if not record:
            self._send_json(404, {"error": "approval_not_found"})
            return

        decision = record.decision or {}
        decided_at = decision.get("decided_at")
        try:
            if record.status == "granted":
                activity_logger.log_approval_granted(
                    approval_id=record.approval_id,
                    actor=actor,
                    reason=reason,
                    tool=record.tool,
                    operation=record.operation,
                    file_path=record.file_path,
                    risk_score=record.risk_score,
                    reasons=record.reasons,
                    summary=record.summary,
                    decided_at=decided_at,
                )
            elif record.status == "denied":
                activity_logger.log_approval_denied(
                    approval_id=record.approval_id,
                    actor=actor,
                    reason=reason,
                    tool=record.tool,
                    operation=record.operation,
                    file_path=record.file_path,
                    risk_score=record.risk_score,
                    reasons=record.reasons,
                    summary=record.summary,
                    decided_at=decided_at,
                )
        except Exception:
            pass

        self._send_json(200, {"approval": record.to_dict()})

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path.startswith("/api/approvals"):
            query = parse_qs(parsed.query)
            self._handle_approvals_get(parsed.path, query)
            return
        return super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path.startswith("/api/approvals"):
            self._handle_approvals_post(parsed.path)
            return
        self._send_json(404, {"error": "not_found"})


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
