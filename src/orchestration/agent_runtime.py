"""Runtime registry for live agent executions."""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
import os
import signal
import subprocess
import threading
import time
from typing import Dict, Optional


logger = logging.getLogger(__name__)


def _signal_process(process: Optional[subprocess.Popen], sig: int) -> bool:
    if process is None or process.poll() is not None:
        return False
    if os.name == "nt":
        logger.debug("Process signaling not supported on Windows.")
        return False
    try:
        os.kill(process.pid, sig)
    except Exception as exc:
        logger.warning("Failed to signal process %s: %s", process.pid, exc, exc_info=True)
        return False
    return True


@dataclass
class AgentExecutionHandle:
    agent_id: str
    mode: str
    thread: Optional[threading.Thread] = None
    process: Optional[subprocess.Popen] = None
    pause_event: threading.Event = field(default_factory=threading.Event)
    stop_event: threading.Event = field(default_factory=threading.Event)
    started_at: float = field(default_factory=time.monotonic)
    completed_at: Optional[float] = None
    exit_code: Optional[int] = None
    error: Optional[str] = None

    def is_active(self) -> bool:
        if self.thread and self.thread.is_alive():
            return True
        if self.process and self.process.poll() is None:
            return True
        return False

    def pause(self) -> bool:
        self.pause_event.set()
        if self.mode == "subprocess":
            if not hasattr(signal, "SIGSTOP"):
                return False
            return _signal_process(self.process, signal.SIGSTOP)
        return True

    def resume(self) -> bool:
        self.pause_event.clear()
        if self.mode == "subprocess":
            if not hasattr(signal, "SIGCONT"):
                return False
            return _signal_process(self.process, signal.SIGCONT)
        return True

    def terminate(self) -> bool:
        self.stop_event.set()
        if self.mode == "subprocess" and self.process and self.process.poll() is None:
            try:
                self.process.terminate()
                return True
            except Exception as exc:
                logger.warning("Failed to terminate process %s: %s", self.process.pid, exc, exc_info=True)
                return False
        return True

    def wait_if_paused(self, *, check_interval: float = 0.2) -> bool:
        while self.pause_event.is_set():
            if self.stop_event.is_set():
                return False
            time.sleep(check_interval)
        return not self.stop_event.is_set()


class AgentRuntimeManager:
    """Tracks live agent execution handles for pause/resume/terminate."""

    def __init__(self) -> None:
        self._handles: Dict[str, AgentExecutionHandle] = {}
        self._lock = threading.Lock()

    def register(self, handle: AgentExecutionHandle) -> None:
        with self._lock:
            self._handles[handle.agent_id] = handle

    def unregister(self, agent_id: str) -> None:
        with self._lock:
            self._handles.pop(agent_id, None)

    def get(self, agent_id: str) -> Optional[AgentExecutionHandle]:
        with self._lock:
            return self._handles.get(agent_id)

    def pause(self, agent_id: str) -> bool:
        handle = self.get(agent_id)
        if not handle:
            return False
        return handle.pause()

    def resume(self, agent_id: str) -> bool:
        handle = self.get(agent_id)
        if not handle:
            return False
        return handle.resume()

    def terminate(self, agent_id: str) -> bool:
        handle = self.get(agent_id)
        if not handle:
            return False
        return handle.terminate()


_runtime_manager: Optional[AgentRuntimeManager] = None


def get_agent_runtime_manager() -> AgentRuntimeManager:
    global _runtime_manager
    if _runtime_manager is None:
        _runtime_manager = AgentRuntimeManager()
    return _runtime_manager


__all__ = [
    "AgentExecutionHandle",
    "AgentRuntimeManager",
    "get_agent_runtime_manager",
]
