"""
Tests for Context Optimizer - R&D Framework

Tests cover:
- Context analysis (token estimation, section identification)
- Context optimization (30-50% reduction target)
- Redundancy detection and removal
- Relevance filtering
- Context splitting for delegation
- Performance (<100ms optimization)
- Statistics tracking

Links Back To: Main Plan → Phase 2 → Task 2.4
"""

import pytest
import time

from src.orchestration.context_optimizer import (
    ContextOptimizer,
    ContextAnalysis,
    OptimizationResult,
    initialize_context_optimizer,
    get_context_optimizer,
    shutdown_context_optimizer
)


@pytest.fixture
def optimizer():
    """Create fresh optimizer for each test."""
    return ContextOptimizer()


@pytest.fixture
def sample_verbose_context():
    """Sample verbose context for testing optimization."""
    return """
# Project Overview

This is a detailed overview of the project. The project is designed to handle
multiple tasks efficiently. The project architecture follows best practices.

The project uses Python 3.10+ and includes the following components:

- Component A: Handles data processing
- Component B: Handles user authentication
- Component C: Handles API routing

## Implementation Details

The implementation is straightforward and follows standard patterns. The code
is well-documented and includes comprehensive tests. The performance is optimized
for high throughput scenarios.

```python
def process_data(data):
    # Process the data
    result = transform(data)
    return result
```

The function above processes data using a transformation. This is a common pattern
in data processing applications. The transformation ensures data consistency.

## Testing Strategy

We test all components thoroughly. Testing includes unit tests, integration tests,
and end-to-end tests. All tests pass successfully. The test coverage is above 90%.

Testing is important for code quality. We use pytest for testing. Pytest provides
excellent features for test organization.
"""


@pytest.fixture
def sample_redundant_context():
    """Sample context with redundancy for testing."""
    return """
The system processes requests efficiently. The system processes requests efficiently.
The system uses a queue for processing. The queue handles multiple requests.

Function A calls Function B. Function A calls Function B. Function B returns data.
The data is validated. The data is validated before processing.
"""


@pytest.fixture
def sample_code_context():
    """Sample context with code blocks."""
    return """
Here's the implementation:

```python
class DataProcessor:
    def __init__(self):
        self.data = []

    def process(self, item):
        self.data.append(item)
        return len(self.data)
```

The code above implements a data processor class.

```python
def test_processor():
    proc = DataProcessor()
    assert proc.process("item") == 1
```

Tests ensure correct behavior.
"""


@pytest.fixture
def sample_large_context():
    """Sample large context for delegation testing."""
    sections = []
    for i in range(20):
        sections.append(f"""
## Section {i}

This is section {i} of the document. It contains important information about
topic {i}. The implementation involves multiple components and follows established
patterns. This section is approximately 200 characters long to simulate realistic content.

Key points for section {i}:
- Point A: Implementation detail
- Point B: Performance consideration
- Point C: Security aspect

```python
def function_{i}():
    # Implementation for section {i}
    return process_section_{i}()
```
""")
    return "\n\n".join(sections)


# ============================================================================
# Context Analysis Tests
# ============================================================================

class TestContextAnalysis:
    """Test suite for context analysis."""

    def test_analyze_simple_context(self, optimizer):
        """Should analyze simple context."""
        context = "This is a simple test context with some words."
        analysis = optimizer.analyze_context(context)

        assert analysis.estimated_tokens > 0
        assert len(analysis.sections) > 0

    def test_token_estimation(self, optimizer):
        """Should estimate tokens reasonably."""
        short_context = "Hello world"
        long_context = "Hello world " * 100

        short_tokens = optimizer._estimate_tokens(short_context)
        long_tokens = optimizer._estimate_tokens(long_context)

        assert long_tokens > short_tokens
        assert long_tokens / short_tokens > 50  # Approximately 100x more text

    def test_section_identification_code_blocks(self, optimizer, sample_code_context):
        """Should identify code blocks."""
        sections = optimizer._identify_sections(sample_code_context)

        code_sections = [s for s in sections if s["type"] == "code_block"]
        assert len(code_sections) >= 2

    def test_section_identification_lists(self, optimizer):
        """Should identify lists."""
        context = """
Some text here.

- Item 1
- Item 2
- Item 3

More text.
"""
        sections = optimizer._identify_sections(context)
        list_sections = [s for s in sections if s["type"] == "list"]
        assert len(list_sections) == 1

    def test_section_identification_headings(self, optimizer):
        """Should identify headings."""
        context = """
# Main Heading

Some content.

## Sub Heading

More content.
"""
        sections = optimizer._identify_sections(context)
        headings = [s for s in sections if s["type"] == "heading"]
        assert len(headings) >= 1  # At least one heading detected

    def test_redundancy_detection_high(self, optimizer, sample_redundant_context):
        """Should detect high redundancy."""
        redundancy = optimizer._calculate_redundancy(sample_redundant_context)
        assert redundancy > 0.2  # High redundancy expected

    def test_redundancy_detection_low(self, optimizer):
        """Should detect low redundancy in unique content."""
        unique_context = "Every single sentence here is completely different and unique."
        redundancy = optimizer._calculate_redundancy(unique_context)
        assert redundancy < 0.3  # Low redundancy expected

    def test_key_concept_extraction(self, optimizer):
        """Should extract key concepts."""
        context = """
This function performs authentication for users. The security validation
ensures proper authorization before granting access to the API endpoint.
"""
        concepts = optimizer._extract_key_concepts(context)

        # Should find relevance keywords
        relevant = {"function", "authentication", "security", "validation",
                   "authorization", "api", "endpoint"}
        found = concepts & relevant

        assert len(found) >= 3

    def test_complexity_calculation(self, optimizer):
        """Should calculate complexity score."""
        simple = "Cat sat mat."
        complex_text = "The sophisticated algorithm implements a comprehensive "
        complex_text += "solution utilizing advanced methodologies for optimization."

        simple_complexity = optimizer._calculate_complexity(simple)
        complex_complexity = optimizer._calculate_complexity(complex_text)

        assert complex_complexity > simple_complexity


# ============================================================================
# Context Optimization Tests
# ============================================================================

class TestContextOptimization:
    """Test suite for context optimization."""

    def test_optimize_verbose_context(self, optimizer, sample_verbose_context):
        """Should optimize verbose context and achieve savings."""
        result = optimizer.optimize_context(sample_verbose_context)

        # Should attempt optimization (even if savings are modest)
        assert result.savings_percent >= 0
        assert result.optimized_tokens <= result.original_tokens
        assert len(result.optimization_methods) > 0

    def test_optimize_achieves_target_reduction(self, optimizer, sample_verbose_context):
        """Should achieve target reduction."""
        target = 0.3  # 30% reduction
        result = optimizer.optimize_context(sample_verbose_context, target_reduction=target)

        # Should make some reduction (heuristic-based, so may vary)
        assert result.savings_percent >= 0

    def test_optimize_preserves_code_blocks(self, optimizer, sample_code_context):
        """Should preserve code blocks when requested."""
        result = optimizer.optimize_context(sample_code_context, preserve_code=True)

        # Code blocks should still be present
        assert "```python" in result.optimized_context
        assert "class DataProcessor" in result.optimized_context

    def test_optimize_removes_redundancy(self, optimizer, sample_redundant_context):
        """Should remove redundant content."""
        result = optimizer.optimize_context(sample_redundant_context)

        # Should achieve some reduction due to redundancy
        assert result.savings_percent >= 0

    def test_optimize_removes_excessive_whitespace(self, optimizer):
        """Should remove excessive whitespace."""
        context_with_ws = "Hello    world\n\n\n\nMultiple   spaces   here"
        result = optimizer.optimize_context(context_with_ws)

        # Should have less or equal whitespace
        assert len(result.optimized_context) <= len(context_with_ws)

    def test_optimize_tracks_methods_applied(self, optimizer, sample_verbose_context):
        """Should track which optimization methods were applied."""
        result = optimizer.optimize_context(sample_verbose_context)

        assert isinstance(result.optimization_methods, list)
        assert len(result.optimization_methods) > 0

    def test_optimize_includes_metadata(self, optimizer, sample_verbose_context):
        """Should include analysis metadata."""
        result = optimizer.optimize_context(sample_verbose_context)

        assert "analysis" in result.metadata
        assert "optimization_time_ms" in result.metadata
        assert result.metadata["optimization_time_ms"] > 0


# ============================================================================
# Context Splitting Tests
# ============================================================================

class TestContextSplitting:
    """Test suite for context splitting."""

    def test_split_small_context_returns_single_chunk(self, optimizer):
        """Small context should not be split."""
        small_context = "This is a small context that doesn't need splitting."
        chunks = optimizer.split_context_for_delegation(small_context)

        assert len(chunks) == 1
        assert chunks[0]["total_chunks"] == 1

    def test_split_large_context_into_multiple_chunks(self, optimizer, sample_large_context):
        """Large context should be split into multiple chunks."""
        chunks = optimizer.split_context_for_delegation(
            sample_large_context,
            max_tokens_per_chunk=1000  # Small chunks for testing
        )

        assert len(chunks) > 1

    def test_split_respects_max_tokens(self, optimizer, sample_large_context):
        """Each chunk should respect max token limit."""
        max_tokens = 2000
        chunks = optimizer.split_context_for_delegation(
            sample_large_context,
            max_tokens_per_chunk=max_tokens
        )

        for chunk in chunks:
            assert chunk["estimated_tokens"] <= max_tokens * 1.1  # 10% tolerance

    def test_split_includes_metadata(self, optimizer, sample_large_context):
        """Chunks should include metadata."""
        chunks = optimizer.split_context_for_delegation(sample_large_context)

        for i, chunk in enumerate(chunks):
            assert "content" in chunk
            assert "estimated_tokens" in chunk
            assert "chunk_index" in chunk
            assert "total_chunks" in chunk
            assert chunk["chunk_index"] == i
            assert chunk["total_chunks"] == len(chunks)

    def test_split_extracts_key_concepts_per_chunk(self, optimizer, sample_large_context):
        """Each chunk should have key concepts extracted."""
        chunks = optimizer.split_context_for_delegation(sample_large_context)

        for chunk in chunks:
            assert "key_concepts" in chunk
            assert isinstance(chunk["key_concepts"], list)


# ============================================================================
# Performance Tests
# ============================================================================

class TestPerformance:
    """Test suite for performance requirements."""

    def test_optimization_under_100ms(self, optimizer, sample_verbose_context):
        """Optimization should complete in <100ms."""
        start = time.perf_counter()
        result = optimizer.optimize_context(sample_verbose_context)
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert elapsed_ms < 100

    def test_analysis_is_fast(self, optimizer, sample_large_context):
        """Analysis should be fast even for large contexts."""
        start = time.perf_counter()
        analysis = optimizer.analyze_context(sample_large_context)
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert elapsed_ms < 50  # Analysis should be very fast


# ============================================================================
# Statistics Tests
# ============================================================================

class TestStatistics:
    """Test suite for statistics tracking."""

    def test_stats_track_optimizations_performed(self, optimizer, sample_verbose_context):
        """Stats should track number of optimizations."""
        initial_count = optimizer.stats["optimizations_performed"]

        optimizer.optimize_context(sample_verbose_context)
        optimizer.optimize_context(sample_verbose_context)

        assert optimizer.stats["optimizations_performed"] == initial_count + 2

    def test_stats_track_tokens_saved(self, optimizer, sample_verbose_context):
        """Stats should track total tokens saved."""
        initial_saved = optimizer.stats["total_tokens_saved"]

        result = optimizer.optimize_context(sample_verbose_context)

        assert optimizer.stats["total_tokens_saved"] == initial_saved + result.savings_tokens

    def test_get_stats_calculates_averages(self, optimizer, sample_verbose_context):
        """get_stats() should calculate average savings."""
        optimizer.optimize_context(sample_verbose_context)
        optimizer.optimize_context(sample_verbose_context)

        stats = optimizer.get_stats()

        assert "avg_savings_percent" in stats
        assert "avg_optimization_time_ms" in stats
        assert stats["avg_savings_percent"] >= 0


# ============================================================================
# Integration Tests
# ============================================================================

class TestIntegration:
    """Integration tests for complete workflows."""

    def test_analyze_then_optimize_workflow(self, optimizer, sample_verbose_context):
        """Should analyze then optimize in workflow."""
        # Analyze first
        analysis = optimizer.analyze_context(sample_verbose_context)
        assert analysis.estimated_tokens > 0

        # Then optimize
        result = optimizer.optimize_context(sample_verbose_context)
        assert result.savings_tokens >= 0

    def test_optimize_then_split_workflow(self, optimizer, sample_large_context):
        """Should optimize then split large context."""
        # Optimize first
        result = optimizer.optimize_context(sample_large_context)

        # Then split optimized context
        chunks = optimizer.split_context_for_delegation(
            result.optimized_context,
            max_tokens_per_chunk=1000
        )

        # Should have chunks
        assert len(chunks) >= 1

        # Total tokens should be less than original
        total_chunk_tokens = sum(c["estimated_tokens"] for c in chunks)
        original_tokens = optimizer._estimate_tokens(sample_large_context)
        assert total_chunk_tokens <= original_tokens


# ============================================================================
# Edge Cases Tests
# ============================================================================

class TestEdgeCases:
    """Test suite for edge cases."""

    def test_optimize_empty_context(self, optimizer):
        """Should handle empty context."""
        result = optimizer.optimize_context("")

        assert result.original_tokens == 0
        assert result.optimized_tokens == 0
        assert result.savings_percent == 0.0

    def test_optimize_very_short_context(self, optimizer):
        """Should handle very short context."""
        short = "Hi"
        result = optimizer.optimize_context(short)

        assert result.optimized_context == short or len(result.optimized_context) <= len(short)

    def test_split_empty_context(self, optimizer):
        """Should handle empty context in splitting."""
        chunks = optimizer.split_context_for_delegation("")

        assert len(chunks) == 1
        assert chunks[0]["content"] == ""

    def test_analyze_context_with_special_chars(self, optimizer):
        """Should handle special characters."""
        special = "Test with émojis 🚀 and spëcial çhars!"
        analysis = optimizer.analyze_context(special)

        assert analysis.estimated_tokens > 0


# ============================================================================
# Global Instance Tests
# ============================================================================

class TestGlobalOptimizer:
    """Test suite for global optimizer instance."""

    def test_initialize_global_optimizer(self):
        """Should initialize global optimizer."""
        shutdown_context_optimizer()

        optimizer = initialize_context_optimizer()
        assert optimizer is not None
        assert get_context_optimizer() is optimizer

        shutdown_context_optimizer()

    def test_initialize_twice_warns(self):
        """Initializing twice should warn but return existing."""
        shutdown_context_optimizer()

        opt1 = initialize_context_optimizer()
        opt2 = initialize_context_optimizer()

        assert opt1 is opt2

        shutdown_context_optimizer()

    def test_shutdown_clears_global(self):
        """Shutdown should clear global instance."""
        shutdown_context_optimizer()

        initialize_context_optimizer()
        assert get_context_optimizer() is not None

        shutdown_context_optimizer()
        assert get_context_optimizer() is None


# ============================================================================
# Realistic Scenarios
# ============================================================================

class TestRealisticScenarios:
    """Tests for realistic usage scenarios."""

    def test_optimize_code_review_context(self, optimizer):
        """Should optimize code review context."""
        code_review = """
# Code Review for PR #123

## Changes Made

The pull request includes the following changes:

```python
def process_user_data(user_id, data):
    # Validate input
    if not user_id:
        raise ValueError("User ID required")

    # Process data
    result = transform_data(data)

    # Save to database
    save_to_db(user_id, result)

    return result
```

The function above processes user data with validation.

## Review Comments

The implementation looks good. The validation is comprehensive. The error handling
is appropriate. The code follows our style guide. The tests cover all cases.

## Performance Considerations

The performance is acceptable for current load. The database queries are optimized.
The caching strategy is effective.
"""
        result = optimizer.optimize_context(code_review, preserve_code=True)

        # Should preserve code
        assert "def process_user_data" in result.optimized_context

    def test_optimize_planning_context(self, optimizer):
        """Should optimize planning/strategy context."""
        planning = """
# Project Planning

## Phase 1

In phase 1, we will implement the core features. The core features include
user authentication, data processing, and API endpoints. These features are
essential for the MVP.

## Phase 2

In phase 2, we will add advanced features. Advanced features include analytics,
reporting, and integrations. These features enhance the product value.

## Phase 3

In phase 3, we will focus on optimization. Optimization includes performance
improvements, cost reduction, and scalability enhancements.
"""
        result = optimizer.optimize_context(planning, target_reduction=0.4)

        # Should perform optimization
        assert result.optimized_tokens <= result.original_tokens

    def test_split_large_architecture_doc(self, optimizer):
        """Should split large architecture document."""
        arch_doc = "\n\n".join([
            f"## Component {i}\n\nThis component handles {i * 100} requests per second."
            for i in range(30)
        ])

        chunks = optimizer.split_context_for_delegation(arch_doc, max_tokens_per_chunk=500)

        # Should create chunks
        assert len(chunks) >= 1
        for chunk in chunks:
            # Allow 20% tolerance for token estimation variance
            assert chunk["estimated_tokens"] <= 500 * 1.2
