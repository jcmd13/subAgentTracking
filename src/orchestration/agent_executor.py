"""Agent execution helpers for running real work."""

from __future__ import annotations

import shlex
import subprocess
import threading
import time
from typing import Any, Dict, Optional, Sequence

from src.core.agent_registry import AgentRegistry
from src.core.cost_tracker import CostTracker
from src.core.providers import (
    BaseProvider,
    ClaudeProvider,
    GeminiProvider,
    OllamaProvider,
    FallbackManager,
    ProviderError,
    build_providers,
)
from src.orchestration.agent_lifecycle import AgentLifecycle
from src.orchestration.agent_runtime import AgentExecutionHandle, get_agent_runtime_manager
from src.orchestration.permissions import PermissionManager
from src.orchestration.tool_proxy import ToolProxy


DEFAULT_OUTPUT_LIMIT = 2000


def _estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return max(1, len(text) // 4)


def _truncate(text: Optional[str], limit: int = DEFAULT_OUTPUT_LIMIT) -> Optional[str]:
    if text is None:
        return None
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "..."


def _infer_provider_name(model: Optional[str]) -> Optional[str]:
    if not model:
        return None
    lowered = model.lower()
    if "claude" in lowered or "anthropic" in lowered:
        return "claude"
    if "gemini" in lowered:
        return "gemini"
    if "ollama" in lowered or "llama" in lowered:
        return "ollama"
    return None


def _build_provider(provider_name: str, model: Optional[str]) -> Optional[BaseProvider]:
    if provider_name == "claude":
        return ClaudeProvider(model=model or "claude-sonnet-3.5")
    if provider_name == "gemini":
        return GeminiProvider(model=model or "gemini-2.0-pro")
    if provider_name == "ollama":
        return OllamaProvider(model=model or "llama3")
    return None


def _resolve_profile(agent: Dict[str, Any]) -> Optional[str]:
    metadata = agent.get("metadata")
    if isinstance(metadata, dict):
        profile = metadata.get("permission_profile")
        if profile:
            return str(profile)
    return None


class AgentExecutor:
    """Runs agent work in-process or via subprocess and updates registry."""

    def __init__(
        self,
        registry: Optional[AgentRegistry] = None,
        lifecycle: Optional[AgentLifecycle] = None,
        cost_tracker: Optional[CostTracker] = None,
        permission_manager: Optional[PermissionManager] = None,
    ) -> None:
        self.registry = registry or AgentRegistry()
        self.lifecycle = lifecycle or AgentLifecycle(registry=self.registry)
        self.cost_tracker = cost_tracker or CostTracker()
        self.permission_manager = permission_manager or PermissionManager()
        self.runtime = get_agent_runtime_manager()

    def start_execution(
        self,
        agent_id: str,
        *,
        mode: str = "in_process",
        prompt: Optional[str] = None,
        command: Optional[Sequence[str] | str] = None,
        provider: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        cwd: Optional[str] = None,
        background: bool = True,
        permission_profile: Optional[str] = None,
        requires_bash: bool = False,
        requires_network: bool = False,
        file_path: Optional[str] = None,
    ) -> AgentExecutionHandle:
        agent = self.registry.get_agent(agent_id)
        if not agent:
            raise ValueError(f"Agent not found: {agent_id}")

        if command and mode != "subprocess":
            actual_mode = "subprocess"
        elif mode == "subprocess" and not command:
            raise ValueError("Subprocess mode requires a command.")
        else:
            actual_mode = mode
        if command:
            requires_bash = True

        handle = AgentExecutionHandle(agent_id=agent_id, mode=actual_mode)
        self.runtime.register(handle)

        if command:
            thread = threading.Thread(
                target=self._run_subprocess,
                args=(
                    handle,
                    agent,
                    command,
                    env,
                    cwd,
                    permission_profile,
                    requires_bash,
                    requires_network,
                    file_path,
                ),
                daemon=True,
            )
        else:
            thread = threading.Thread(
                target=self._run_prompt,
                args=(handle, agent, prompt, provider, permission_profile, requires_network),
                daemon=True,
            )
        handle.thread = thread
        thread.start()

        if not background:
            thread.join()

        return handle

    def _run_prompt(
        self,
        handle: AgentExecutionHandle,
        agent: Dict[str, Any],
        prompt: Optional[str],
        provider_name: Optional[str],
        permission_profile: Optional[str],
        requires_network: bool,
    ) -> None:
        start = time.monotonic()
        model_name = agent.get("model")
        if not prompt:
            self.lifecycle.fail_agent(
                handle.agent_id,
                reason="Prompt missing for execution",
                error="prompt_required",
            )
            self.runtime.unregister(handle.agent_id)
            return

        if not handle.wait_if_paused():
            self.lifecycle.terminate_agent(handle.agent_id, reason="Execution terminated before start")
            self.runtime.unregister(handle.agent_id)
            return

        try:
            provider_key = provider_name or _infer_provider_name(model_name) or ""
            provider = _build_provider(provider_key, model_name)
            profile = permission_profile or _resolve_profile(agent)
            if provider and getattr(provider, "allow_live", False):
                decision = self.permission_manager.validate(
                    tool="provider",
                    requires_network=True,
                    profile_name=profile,
                )
                if not decision.allowed:
                    raise ProviderError(decision.reason or "network_access_denied")
            elif requires_network:
                decision = self.permission_manager.validate(
                    tool="provider",
                    requires_network=True,
                    profile_name=profile,
                )
                if not decision.allowed:
                    raise ProviderError(decision.reason or "network_access_denied")
            if provider:
                output = provider.generate(prompt)
                model_used = provider.model
            else:
                fallback = FallbackManager(build_providers())
                output = fallback.generate(prompt)
                model_used = model_name or "unknown"

            if handle.stop_event.is_set():
                self.lifecycle.terminate_agent(
                    handle.agent_id,
                    reason="Execution terminated during run",
                )
                self.runtime.unregister(handle.agent_id)
                return

            duration_ms = int((time.monotonic() - start) * 1000)
            input_tokens = _estimate_tokens(prompt)
            output_tokens = _estimate_tokens(output)
            tokens_used = input_tokens + output_tokens
            cost_usd = self.cost_tracker.calculate_cost(
                model_used,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            )
            handle.exit_code = 0

            metrics = {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "tokens_used": tokens_used,
                "elapsed_seconds": duration_ms / 1000.0,
                "cost_usd": cost_usd,
            }

            self.lifecycle.complete_agent(
                handle.agent_id,
                reason="Execution completed",
                result={"output": _truncate(output)},
                duration_ms=duration_ms,
                tokens_used=tokens_used,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                metrics=metrics,
            )
        except ProviderError as exc:
            duration_ms = int((time.monotonic() - start) * 1000)
            handle.error = str(exc)
            self.lifecycle.fail_agent(
                handle.agent_id,
                reason="Provider execution failed",
                error=str(exc),
                duration_ms=duration_ms,
                error_type="ProviderError",
            )
        except Exception as exc:
            duration_ms = int((time.monotonic() - start) * 1000)
            handle.error = str(exc)
            self.lifecycle.fail_agent(
                handle.agent_id,
                reason="Execution failed",
                error=str(exc),
                duration_ms=duration_ms,
                error_type="ExecutionError",
            )
        finally:
            handle.completed_at = time.monotonic()
            self.runtime.unregister(handle.agent_id)

    def _run_subprocess(
        self,
        handle: AgentExecutionHandle,
        agent: Dict[str, Any],
        command: Sequence[str] | str,
        env: Optional[Dict[str, str]],
        cwd: Optional[str],
        permission_profile: Optional[str],
        requires_bash: bool,
        requires_network: bool,
        file_path: Optional[str],
    ) -> None:
        start = time.monotonic()
        if not handle.wait_if_paused():
            self.lifecycle.terminate_agent(handle.agent_id, reason="Execution terminated before start")
            self.runtime.unregister(handle.agent_id)
            return

        cmd_list = list(command) if isinstance(command, (list, tuple)) else shlex.split(str(command))

        try:
            profile = permission_profile or _resolve_profile(agent)
            proxy = ToolProxy(
                agent_id=handle.agent_id,
                profile_name=profile,
                permission_manager=self.permission_manager,
            )

            def run_command() -> Dict[str, Any]:
                process = subprocess.Popen(
                    cmd_list,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    env=env,
                    cwd=cwd,
                )
                handle.process = process
                stdout, stderr = process.communicate()
                exit_code = process.returncode or 0
                handle.exit_code = exit_code
                return {
                    "stdout": _truncate(stdout),
                    "stderr": _truncate(stderr),
                    "exit_code": exit_code,
                }

            tool_result = proxy.execute(
                "bash",
                run_command,
                operation="exec",
                parameters={"command": cmd_list, "cwd": cwd},
                file_path=file_path,
                requires_bash=requires_bash,
                requires_network=requires_network,
            )

            if not tool_result.success:
                duration_ms = int((time.monotonic() - start) * 1000)
                handle.error = tool_result.error or "tool_execution_failed"
                self.lifecycle.fail_agent(
                    handle.agent_id,
                    reason="Execution blocked",
                    error=handle.error,
                    duration_ms=duration_ms,
                    error_type="PermissionDenied",
                )
                return

            result = tool_result.result or {"exit_code": 1}
            exit_code = int(result.get("exit_code") or 0)
            handle.exit_code = exit_code

            duration_ms = int((time.monotonic() - start) * 1000)
            metrics = {
                "exit_code": exit_code,
                "elapsed_seconds": duration_ms / 1000.0,
            }

            if handle.stop_event.is_set():
                self.lifecycle.terminate_agent(
                    handle.agent_id,
                    reason="Execution terminated during run",
                    metadata={"execution_result": result},
                )
            elif exit_code == 0:
                self.lifecycle.complete_agent(
                    handle.agent_id,
                    reason="Execution completed",
                    result=result,
                    duration_ms=duration_ms,
                    tokens_used=0,
                    metrics=metrics,
                )
            else:
                handle.error = result.get("stderr") or "Non-zero exit"
                self.lifecycle.fail_agent(
                    handle.agent_id,
                    reason="Execution failed",
                    error=result.get("stderr") or "Non-zero exit",
                    duration_ms=duration_ms,
                    error_type="SubprocessError",
                    metrics=metrics,
                )
        except Exception as exc:
            duration_ms = int((time.monotonic() - start) * 1000)
            handle.error = str(exc)
            self.lifecycle.fail_agent(
                handle.agent_id,
                reason="Execution failed",
                error=str(exc),
                duration_ms=duration_ms,
                error_type="SubprocessError",
            )
        finally:
            handle.completed_at = time.monotonic()
            self.runtime.unregister(handle.agent_id)


__all__ = ["AgentExecutor"]
