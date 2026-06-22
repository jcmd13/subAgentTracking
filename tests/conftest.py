"""Pytest configuration shared by the whole test suite.

Why this file exists
--------------------
A number of tests assert *absolute* performance numbers — raw throughput
(events/sec) and per-operation latency (ms). Those numbers depend entirely on
the speed of the machine running them, so on shared CI runners they flake:
e.g. an ingestion test demanding ">1000 events/sec" can measure 977/sec on a
busy VM and fail a build that has no actual regression.

To keep CI meaningful we separate *correctness* from *benchmarks*:

* The CI gate runs the functional suite with ``-m "not performance"``.
* Benchmarks run in a separate, non-blocking step (``-m performance``) so the
  numbers are still produced and visible, but a slow runner never reds the build.

Rather than scatter ``@pytest.mark.performance`` across a dozen files, the
hardware-sensitive tests are enumerated here by node-id pattern and marked at
collection time. This list is the single source of truth for "what is a
benchmark"; add to it if a new timing/throughput assertion is introduced.
"""

import pytest

# Node-id substrings identifying hardware-sensitive timing/throughput tests.
# Class patterns (``::TestX::``) cover every method in that benchmark class.
_PERFORMANCE_NODE_PATTERNS = (
    "test_performance.py",                 # entire dedicated benchmark module
    "::TestPerformance::",                 # perf classes across several modules
    "::TestModelRouterPerformance::",
    "::TestPerformanceAndScale::",
    "test_high_throughput_10k_events",
    "test_dispatch_latency_under_5ms",
    "test_ingestion_performance_target",
    "test_restore_performance_target",
    "test_handoff_performance_target",
)


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "performance: hardware-sensitive timing/throughput benchmark; excluded "
        "from the CI correctness gate (run separately, non-blocking).",
    )


def pytest_collection_modifyitems(config, items):
    for item in items:
        if any(pattern in item.nodeid for pattern in _PERFORMANCE_NODE_PATTERNS):
            item.add_marker("performance")
