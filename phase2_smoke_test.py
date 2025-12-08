#!/usr/bin/env python3
"""
Phase 2 Smoke Test - Orchestration Layer Validation

Quick validation that all Phase 2 components are working together.
Tests initialization, basic operations, and statistics.
"""

import sys
import asyncio
from pathlib import Path

import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.orchestration import (
    initialize_orchestration,
    shutdown_orchestration,
    get_orchestration_stats,
    get_model_router,
    get_context_optimizer,
    get_agent_coordinator
)
from src.orchestration.agent_coordinator import AgentTask, WorkflowPhase


def test_initialization():
    """Test 1: Verify all components initialize."""
    print("\n=== Test 1: Initialization ===")

    try:
        components = initialize_orchestration()
        assert components['router'] is not None, "Router initialization failed"
        assert components['coordinator'] is not None, "Coordinator initialization failed"
        assert components['optimizer'] is not None, "Optimizer initialization failed"
        assert components['subscriber'] is not None, "Subscriber initialization failed"
        print("✅ All components initialized successfully")
        return True
    except Exception as e:
        print(f"❌ Initialization failed: {e}")
        return False


def test_model_routing():
    """Test 2: Verify model routing works."""
    print("\n=== Test 2: Model Routing ===")

    try:
        router = get_model_router()
        assert router is not None, "Router not initialized"

        # Test simple task
        task = {
            "type": "log_summary",
            "context_tokens": 5000,
            "files": ["test.log"]
        }
        model, tier, metadata = router.select_model(task)

        assert tier == "weak", f"Expected weak tier, got {tier}"
        assert metadata["complexity_score"] <= 3, "Complexity score too high for simple task"
        print(f"✅ Model routing works: {model} ({tier} tier)")
        return True
    except Exception as e:
        print(f"❌ Model routing failed: {e}")
        return False


def test_context_optimization():
    """Test 3: Verify context optimization works."""
    print("\n=== Test 3: Context Optimization ===")

    try:
        optimizer = get_context_optimizer()
        assert optimizer is not None, "Optimizer not initialized"

        # Test optimization
        context = "This is a test context. " * 100
        result = optimizer.optimize_context(context)

        assert result.optimized_tokens <= result.original_tokens, "No optimization occurred"
        print(f"✅ Context optimization works: {result.original_tokens} → {result.optimized_tokens} tokens ({result.savings_percent:.1f}% savings)")
        return True
    except Exception as e:
        print(f"❌ Context optimization failed: {e}")
        return False


@pytest.mark.asyncio
async def test_agent_coordination():
    """Test 4: Verify agent coordination works."""
    print("\n=== Test 4: Agent Coordination ===")

    try:
        coordinator = get_agent_coordinator()
        assert coordinator is not None, "Coordinator not initialized"

        # Define simple agent handlers
        async def test_agent(task_spec, context):
            return {"result": "success"}

        # Register agent
        coordinator.register_agent("test", test_agent)

        # Create simple workflow
        task = AgentTask(
            agent_id="test_1",
            agent_type="test",
            phase=WorkflowPhase.SCOUT,
            task_spec={}
        )

        workflow = coordinator.create_workflow("smoke_test", [task])
        results = await coordinator.execute_workflow("smoke_test")

        assert results["status"] == "completed", f"Workflow failed: {results}"
        assert "test_1" in results["results"], "Agent result not found"
        print(f"✅ Agent coordination works: workflow completed successfully")
        return True
    except Exception as e:
        print(f"❌ Agent coordination failed: {e}")
        return False


def test_statistics():
    """Test 5: Verify statistics collection works."""
    print("\n=== Test 5: Statistics ===")

    try:
        stats = get_orchestration_stats()

        assert 'router' in stats, "Router stats missing"
        assert 'coordinator' in stats, "Coordinator stats missing"
        assert 'optimizer' in stats, "Optimizer stats missing"
        assert 'estimated_cost_savings_percent' in stats, "Cost savings estimate missing"

        print(f"✅ Statistics collection works")
        print(f"   - Router: {stats['router']['total_routes']} routes")
        print(f"   - Optimizer: {stats['optimizer']['optimizations_performed']} optimizations")
        print(f"   - Coordinator: {stats['coordinator']['workflows_executed']} workflows")
        print(f"   - Est. cost savings: {stats['estimated_cost_savings_percent']:.1f}%")
        return True
    except Exception as e:
        print(f"❌ Statistics collection failed: {e}")
        return False


def test_shutdown():
    """Test 6: Verify clean shutdown works."""
    print("\n=== Test 6: Shutdown ===")

    try:
        shutdown_orchestration()

        # Verify components are cleared
        assert get_model_router() is None, "Router not cleared"
        assert get_agent_coordinator() is None, "Coordinator not cleared"
        assert get_context_optimizer() is None, "Optimizer not cleared"

        print("✅ Shutdown works: all components cleared")
        return True
    except Exception as e:
        print(f"❌ Shutdown failed: {e}")
        return False


async def main():
    """Run all smoke tests."""
    print("=" * 60)
    print("Phase 2 Smoke Test - Orchestration Layer")
    print("=" * 60)

    results = []

    # Test 1: Initialization
    results.append(test_initialization())

    # Test 2: Model Routing
    results.append(test_model_routing())

    # Test 3: Context Optimization
    results.append(test_context_optimization())

    # Test 4: Agent Coordination
    results.append(await test_agent_coordination())

    # Test 5: Statistics
    results.append(test_statistics())

    # Test 6: Shutdown
    results.append(test_shutdown())

    # Summary
    print("\n" + "=" * 60)
    passed = sum(results)
    total = len(results)

    if passed == total:
        print(f"✅ ALL TESTS PASSED ({passed}/{total})")
        print("=" * 60)
        print("\nPhase 2 orchestration layer is working correctly!")
        return 0
    else:
        print(f"❌ SOME TESTS FAILED ({passed}/{total})")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
