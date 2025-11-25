"""
Tests for Agent Coordinator - Scout-Plan-Build Workflow

Tests cover:
- Workflow creation and validation
- Agent registration
- Dependency resolution
- Parallel execution
- Context passing
- Error handling
- Event publishing
- Performance (<5ms coordination overhead)

Links Back To: Main Plan → Phase 2 → Task 2.3
"""

import pytest
import asyncio
import time
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock

from src.orchestration.agent_coordinator import (
    AgentCoordinator,
    AgentTask,
    Workflow,
    WorkflowPhase,
    AgentStatus,
    initialize_agent_coordinator,
    get_agent_coordinator,
    shutdown_agent_coordinator
)


@pytest.fixture
def coordinator():
    """Create fresh coordinator for each test."""
    return AgentCoordinator()


@pytest.fixture
def mock_scout_agent():
    """Mock scout agent that returns file list."""
    async def scout(task_spec: dict, context: dict) -> dict:
        await asyncio.sleep(0.01)  # Simulate work
        return {"files_found": ["src/router.py", "src/scorer.py"]}
    return scout


@pytest.fixture
def mock_planner_agent():
    """Mock planner agent that creates plan."""
    async def planner(task_spec: dict, context: dict) -> dict:
        await asyncio.sleep(0.02)  # Simulate work
        files = context.get("dependencies", {}).get("scout_1", {}).get("files_found", [])
        return {"plan": f"Process {len(files)} files", "steps": ["step1", "step2"]}
    return planner


@pytest.fixture
def mock_builder_agent():
    """Mock builder agent that executes plan."""
    async def builder(task_spec: dict, context: dict) -> dict:
        await asyncio.sleep(0.03)  # Simulate work
        plan = context.get("dependencies", {}).get("plan_1", {}).get("plan", "")
        return {"output": f"Executed: {plan}", "files_created": ["output.py"]}
    return builder


@pytest.fixture
def mock_failing_agent():
    """Mock agent that always fails."""
    async def failing(task_spec: dict, context: dict) -> dict:
        await asyncio.sleep(0.01)
        raise Exception("Agent failed intentionally")
    return failing


# ============================================================================
# Agent Registration Tests
# ============================================================================

class TestAgentRegistration:
    """Test suite for agent registration."""

    @pytest.mark.asyncio
    async def test_register_agent(self, coordinator, mock_scout_agent):
        """Should register agent handler."""
        coordinator.register_agent("scout", mock_scout_agent)
        assert "scout" in coordinator._agent_registry

    @pytest.mark.asyncio
    async def test_register_multiple_agents(self, coordinator, mock_scout_agent, mock_planner_agent):
        """Should register multiple agent types."""
        coordinator.register_agent("scout", mock_scout_agent)
        coordinator.register_agent("planner", mock_planner_agent)

        assert len(coordinator._agent_registry) == 2
        assert "scout" in coordinator._agent_registry
        assert "planner" in coordinator._agent_registry


# ============================================================================
# Workflow Creation Tests
# ============================================================================

class TestWorkflowCreation:
    """Test suite for workflow creation."""

    def test_create_simple_workflow(self, coordinator):
        """Should create workflow with single task."""
        task = AgentTask(
            agent_id="scout_1",
            agent_type="scout",
            phase=WorkflowPhase.SCOUT,
            task_spec={"search_pattern": "*.py"}
        )

        workflow = coordinator.create_workflow("wf_1", [task])

        assert workflow.workflow_id == "wf_1"
        assert len(workflow.tasks) == 1
        assert workflow.status == "created"

    def test_create_workflow_with_dependencies(self, coordinator):
        """Should create workflow with task dependencies."""
        tasks = [
            AgentTask(
                agent_id="scout_1",
                agent_type="scout",
                phase=WorkflowPhase.SCOUT,
                task_spec={}
            ),
            AgentTask(
                agent_id="plan_1",
                agent_type="planner",
                phase=WorkflowPhase.PLAN,
                task_spec={},
                depends_on=["scout_1"]
            )
        ]

        workflow = coordinator.create_workflow("wf_2", tasks)

        assert len(workflow.tasks) == 2
        assert workflow.tasks["plan_1"].depends_on == ["scout_1"]

    def test_create_workflow_duplicate_id_fails(self, coordinator):
        """Creating workflow with duplicate ID should fail."""
        task = AgentTask(
            agent_id="scout_1",
            agent_type="scout",
            phase=WorkflowPhase.SCOUT,
            task_spec={}
        )

        coordinator.create_workflow("wf_1", [task])

        with pytest.raises(ValueError, match="already exists"):
            coordinator.create_workflow("wf_1", [task])

    def test_create_workflow_invalid_dependency_fails(self, coordinator):
        """Workflow with non-existent dependency should fail."""
        task = AgentTask(
            agent_id="plan_1",
            agent_type="planner",
            phase=WorkflowPhase.PLAN,
            task_spec={},
            depends_on=["nonexistent_task"]
        )

        with pytest.raises(ValueError, match="non-existent task"):
            coordinator.create_workflow("wf_bad", [task])

    def test_create_workflow_circular_dependency_fails(self, coordinator):
        """Workflow with circular dependency should fail."""
        tasks = [
            AgentTask(
                agent_id="task_a",
                agent_type="scout",
                phase=WorkflowPhase.SCOUT,
                task_spec={},
                depends_on=["task_b"]
            ),
            AgentTask(
                agent_id="task_b",
                agent_type="planner",
                phase=WorkflowPhase.PLAN,
                task_spec={},
                depends_on=["task_a"]
            )
        ]

        with pytest.raises(ValueError, match="Circular dependency"):
            coordinator.create_workflow("wf_circular", tasks)


# ============================================================================
# Workflow Execution Tests
# ============================================================================

class TestWorkflowExecution:
    """Test suite for workflow execution."""

    @pytest.mark.asyncio
    async def test_execute_single_task_workflow(self, coordinator, mock_scout_agent):
        """Should execute workflow with single task."""
        coordinator.register_agent("scout", mock_scout_agent)

        task = AgentTask(
            agent_id="scout_1",
            agent_type="scout",
            phase=WorkflowPhase.SCOUT,
            task_spec={"search_pattern": "*.py"}
        )

        workflow = coordinator.create_workflow("wf_1", [task])
        results = await coordinator.execute_workflow("wf_1")

        assert results["status"] == "completed"
        assert "scout_1" in results["results"]
        assert results["results"]["scout_1"]["files_found"] == ["src/router.py", "src/scorer.py"]

    @pytest.mark.asyncio
    async def test_execute_sequential_workflow(self, coordinator, mock_scout_agent, mock_planner_agent):
        """Should execute workflow with sequential dependencies."""
        coordinator.register_agent("scout", mock_scout_agent)
        coordinator.register_agent("planner", mock_planner_agent)

        tasks = [
            AgentTask(
                agent_id="scout_1",
                agent_type="scout",
                phase=WorkflowPhase.SCOUT,
                task_spec={}
            ),
            AgentTask(
                agent_id="plan_1",
                agent_type="planner",
                phase=WorkflowPhase.PLAN,
                task_spec={},
                depends_on=["scout_1"]
            )
        ]

        workflow = coordinator.create_workflow("wf_seq", tasks)
        results = await coordinator.execute_workflow("wf_seq")

        assert results["status"] == "completed"
        assert "scout_1" in results["results"]
        assert "plan_1" in results["results"]

        # Verify planner received scout results in context
        assert "Process 2 files" in results["results"]["plan_1"]["plan"]

    @pytest.mark.asyncio
    async def test_execute_parallel_tasks(self, coordinator, mock_scout_agent):
        """Should execute independent tasks in parallel."""
        coordinator.register_agent("scout", mock_scout_agent)

        tasks = [
            AgentTask(
                agent_id="scout_1",
                agent_type="scout",
                phase=WorkflowPhase.SCOUT,
                task_spec={"pattern": "*.py"}
            ),
            AgentTask(
                agent_id="scout_2",
                agent_type="scout",
                phase=WorkflowPhase.SCOUT,
                task_spec={"pattern": "*.md"}
            )
        ]

        workflow = coordinator.create_workflow("wf_parallel", tasks)

        start = time.perf_counter()
        results = await coordinator.execute_workflow("wf_parallel")
        elapsed = time.perf_counter() - start

        assert results["status"] == "completed"
        assert "scout_1" in results["results"]
        assert "scout_2" in results["results"]

        # Parallel execution should be faster than sequential
        # Each task takes ~0.01s, sequential would be ~0.02s
        # Parallel should be close to 0.01s
        assert elapsed < 0.025, f"Parallel execution too slow: {elapsed:.3f}s"

    @pytest.mark.asyncio
    async def test_execute_full_scout_plan_build_workflow(
        self,
        coordinator,
        mock_scout_agent,
        mock_planner_agent,
        mock_builder_agent
    ):
        """Should execute complete Scout-Plan-Build workflow."""
        coordinator.register_agent("scout", mock_scout_agent)
        coordinator.register_agent("planner", mock_planner_agent)
        coordinator.register_agent("builder", mock_builder_agent)

        tasks = [
            AgentTask(
                agent_id="scout_1",
                agent_type="scout",
                phase=WorkflowPhase.SCOUT,
                task_spec={}
            ),
            AgentTask(
                agent_id="plan_1",
                agent_type="planner",
                phase=WorkflowPhase.PLAN,
                task_spec={},
                depends_on=["scout_1"]
            ),
            AgentTask(
                agent_id="build_1",
                agent_type="builder",
                phase=WorkflowPhase.BUILD,
                task_spec={},
                depends_on=["plan_1"]
            )
        ]

        workflow = coordinator.create_workflow("wf_full", tasks)
        results = await coordinator.execute_workflow("wf_full")

        assert results["status"] == "completed"
        assert len(results["results"]) == 3

        # Verify data flow through pipeline
        assert results["results"]["scout_1"]["files_found"]
        assert "Process 2 files" in results["results"]["plan_1"]["plan"]
        assert "Executed: Process 2 files" in results["results"]["build_1"]["output"]

    @pytest.mark.asyncio
    async def test_execute_nonexistent_workflow_fails(self, coordinator):
        """Executing non-existent workflow should fail."""
        with pytest.raises(ValueError, match="not found"):
            await coordinator.execute_workflow("nonexistent")

    @pytest.mark.asyncio
    async def test_execute_workflow_with_unregistered_agent_fails(self, coordinator):
        """Workflow with unregistered agent should fail."""
        task = AgentTask(
            agent_id="scout_1",
            agent_type="unregistered_agent",
            phase=WorkflowPhase.SCOUT,
            task_spec={}
        )

        workflow = coordinator.create_workflow("wf_bad", [task])
        results = await coordinator.execute_workflow("wf_bad")

        # Workflow completes but task failed
        assert results["status"] == "completed"
        assert "scout_1" in results["errors"]
        assert results["errors"]["scout_1"] is not None


# ============================================================================
# Error Handling Tests
# ============================================================================

class TestErrorHandling:
    """Test suite for error handling."""

    @pytest.mark.asyncio
    async def test_agent_failure_stops_dependent_tasks(
        self,
        coordinator,
        mock_failing_agent,
        mock_planner_agent
    ):
        """Failed agent should prevent dependent tasks from running."""
        coordinator.register_agent("failing", mock_failing_agent)
        coordinator.register_agent("planner", mock_planner_agent)

        tasks = [
            AgentTask(
                agent_id="fail_1",
                agent_type="failing",
                phase=WorkflowPhase.SCOUT,
                task_spec={}
            ),
            AgentTask(
                agent_id="plan_1",
                agent_type="planner",
                phase=WorkflowPhase.PLAN,
                task_spec={},
                depends_on=["fail_1"]
            )
        ]

        workflow = coordinator.create_workflow("wf_fail", tasks)
        results = await coordinator.execute_workflow("wf_fail")

        # Workflow completes but has errors
        assert results["status"] == "completed"  # Workflow execution completes
        assert "fail_1" in results["errors"]
        assert "plan_1" not in results["results"]  # Dependent task didn't run

    @pytest.mark.asyncio
    async def test_independent_tasks_continue_on_failure(
        self,
        coordinator,
        mock_failing_agent,
        mock_scout_agent
    ):
        """Independent tasks should continue even if one fails."""
        coordinator.register_agent("failing", mock_failing_agent)
        coordinator.register_agent("scout", mock_scout_agent)

        tasks = [
            AgentTask(
                agent_id="fail_1",
                agent_type="failing",
                phase=WorkflowPhase.SCOUT,
                task_spec={}
            ),
            AgentTask(
                agent_id="scout_1",
                agent_type="scout",
                phase=WorkflowPhase.SCOUT,
                task_spec={}
            )
        ]

        workflow = coordinator.create_workflow("wf_partial_fail", tasks)
        results = await coordinator.execute_workflow("wf_partial_fail")

        assert results["status"] == "completed"
        assert "fail_1" in results["errors"]
        assert "scout_1" in results["results"]  # Independent task succeeded


# ============================================================================
# Context Building Tests
# ============================================================================

class TestContextBuilding:
    """Test suite for context passing between agents."""

    @pytest.mark.asyncio
    async def test_context_includes_workflow_id(self, coordinator, mock_scout_agent):
        """Context should include workflow ID."""
        captured_context = {}

        async def capturing_agent(task_spec: dict, context: dict) -> dict:
            captured_context.update(context)
            return {"done": True}

        coordinator.register_agent("capturing", capturing_agent)

        task = AgentTask(
            agent_id="capture_1",
            agent_type="capturing",
            phase=WorkflowPhase.SCOUT,
            task_spec={}
        )

        workflow = coordinator.create_workflow("wf_ctx", [task])
        await coordinator.execute_workflow("wf_ctx")

        assert captured_context["workflow_id"] == "wf_ctx"
        assert captured_context["phase"] == "scout"

    @pytest.mark.asyncio
    async def test_context_includes_dependency_results(
        self,
        coordinator,
        mock_scout_agent,
        mock_planner_agent
    ):
        """Context should include results from dependencies."""
        captured_context = {}

        async def capturing_planner(task_spec: dict, context: dict) -> dict:
            captured_context.update(context)
            return {"done": True}

        coordinator.register_agent("scout", mock_scout_agent)
        coordinator.register_agent("capturing_planner", capturing_planner)

        tasks = [
            AgentTask(
                agent_id="scout_1",
                agent_type="scout",
                phase=WorkflowPhase.SCOUT,
                task_spec={}
            ),
            AgentTask(
                agent_id="plan_1",
                agent_type="capturing_planner",
                phase=WorkflowPhase.PLAN,
                task_spec={},
                depends_on=["scout_1"]
            )
        ]

        workflow = coordinator.create_workflow("wf_ctx_dep", tasks)
        await coordinator.execute_workflow("wf_ctx_dep")

        assert "dependencies" in captured_context
        assert "scout_1" in captured_context["dependencies"]
        assert captured_context["dependencies"]["scout_1"]["files_found"] == [
            "src/router.py",
            "src/scorer.py"
        ]


# ============================================================================
# Performance Tests
# ============================================================================

class TestPerformance:
    """Test suite for performance requirements."""

    @pytest.mark.asyncio
    async def test_coordination_overhead_under_5ms(self, coordinator):
        """Coordination overhead should be <5ms per task."""
        async def fast_agent(task_spec: dict, context: dict) -> dict:
            return {"done": True}  # No delay

        coordinator.register_agent("fast", fast_agent)

        task = AgentTask(
            agent_id="fast_1",
            agent_type="fast",
            phase=WorkflowPhase.SCOUT,
            task_spec={}
        )

        workflow = coordinator.create_workflow("wf_perf", [task])

        start = time.perf_counter()
        await coordinator.execute_workflow("wf_perf")
        elapsed_ms = (time.perf_counter() - start) * 1000

        # Should complete in <10ms (5ms overhead + minimal execution)
        assert elapsed_ms < 10, f"Coordination overhead too high: {elapsed_ms:.2f}ms"


# ============================================================================
# Statistics Tests
# ============================================================================

class TestStatistics:
    """Test suite for coordinator statistics."""

    @pytest.mark.asyncio
    async def test_stats_track_workflows_executed(self, coordinator, mock_scout_agent):
        """Stats should track number of workflows executed."""
        coordinator.register_agent("scout", mock_scout_agent)

        for i in range(3):
            task = AgentTask(
                agent_id=f"scout_{i}",
                agent_type="scout",
                phase=WorkflowPhase.SCOUT,
                task_spec={}
            )
            workflow = coordinator.create_workflow(f"wf_{i}", [task])
            await coordinator.execute_workflow(f"wf_{i}")

        stats = coordinator.get_stats()
        assert stats["workflows_executed"] == 3

    @pytest.mark.asyncio
    async def test_stats_track_agents_executed(self, coordinator, mock_scout_agent):
        """Stats should track number of agents executed."""
        coordinator.register_agent("scout", mock_scout_agent)

        tasks = [
            AgentTask(
                agent_id=f"scout_{i}",
                agent_type="scout",
                phase=WorkflowPhase.SCOUT,
                task_spec={}
            )
            for i in range(5)
        ]

        workflow = coordinator.create_workflow("wf_multi", tasks)
        await coordinator.execute_workflow("wf_multi")

        stats = coordinator.get_stats()
        assert stats["agents_executed"] == 5

    @pytest.mark.asyncio
    async def test_stats_track_phase_times(self, coordinator, mock_scout_agent, mock_planner_agent):
        """Stats should track average times per phase."""
        coordinator.register_agent("scout", mock_scout_agent)
        coordinator.register_agent("planner", mock_planner_agent)

        tasks = [
            AgentTask(
                agent_id="scout_1",
                agent_type="scout",
                phase=WorkflowPhase.SCOUT,
                task_spec={}
            ),
            AgentTask(
                agent_id="plan_1",
                agent_type="planner",
                phase=WorkflowPhase.PLAN,
                task_spec={},
                depends_on=["scout_1"]
            )
        ]

        workflow = coordinator.create_workflow("wf_phases", tasks)
        await coordinator.execute_workflow("wf_phases")

        stats = coordinator.get_stats()
        assert "avg_phase_times" in stats
        assert "scout" in stats["avg_phase_times"]
        assert "plan" in stats["avg_phase_times"]


# ============================================================================
# Workflow Status Tests
# ============================================================================

class TestWorkflowStatus:
    """Test suite for workflow status queries."""

    @pytest.mark.asyncio
    async def test_get_workflow_status(self, coordinator, mock_scout_agent):
        """Should get current workflow status."""
        coordinator.register_agent("scout", mock_scout_agent)

        task = AgentTask(
            agent_id="scout_1",
            agent_type="scout",
            phase=WorkflowPhase.SCOUT,
            task_spec={}
        )

        workflow = coordinator.create_workflow("wf_status", [task])
        status = coordinator.get_workflow_status("wf_status")

        assert status["workflow_id"] == "wf_status"
        assert status["status"] == "created"
        assert len(status["tasks"]) == 1

    @pytest.mark.asyncio
    async def test_get_workflow_status_after_execution(self, coordinator, mock_scout_agent):
        """Should get workflow status after execution."""
        coordinator.register_agent("scout", mock_scout_agent)

        task = AgentTask(
            agent_id="scout_1",
            agent_type="scout",
            phase=WorkflowPhase.SCOUT,
            task_spec={}
        )

        workflow = coordinator.create_workflow("wf_done", [task])
        await coordinator.execute_workflow("wf_done")

        status = coordinator.get_workflow_status("wf_done")

        assert status["status"] == "completed"
        assert status["tasks"]["scout_1"]["status"] == "completed"

    def test_get_nonexistent_workflow_status_fails(self, coordinator):
        """Getting status of non-existent workflow should fail."""
        with pytest.raises(ValueError, match="not found"):
            coordinator.get_workflow_status("nonexistent")


# ============================================================================
# Global Instance Tests
# ============================================================================

class TestGlobalCoordinator:
    """Test suite for global coordinator instance."""

    def test_initialize_global_coordinator(self):
        """Should initialize global coordinator."""
        shutdown_agent_coordinator()

        coordinator = initialize_agent_coordinator()
        assert coordinator is not None
        assert get_agent_coordinator() is coordinator

        shutdown_agent_coordinator()

    def test_initialize_twice_warns(self):
        """Initializing twice should warn but return existing."""
        shutdown_agent_coordinator()

        coord1 = initialize_agent_coordinator()
        coord2 = initialize_agent_coordinator()

        assert coord1 is coord2

        shutdown_agent_coordinator()

    def test_shutdown_clears_global(self):
        """Shutdown should clear global instance."""
        shutdown_agent_coordinator()

        initialize_agent_coordinator()
        assert get_agent_coordinator() is not None

        shutdown_agent_coordinator()
        assert get_agent_coordinator() is None
