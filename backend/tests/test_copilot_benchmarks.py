"""
Unit and Integration Tests for 30 FinOps Benchmark Questions.
Verifies intent coverage, question completeness, and execution accuracy against database.
"""

import pytest
from backend.app.core.enums import CopilotIntent
from backend.app.copilot.benchmarks import BENCHMARK_QUESTIONS, run_benchmark_evaluation


def test_benchmark_suite_completeness():
    """Verify that the benchmark suite contains exactly 30 questions covering all 15 intents."""
    assert len(BENCHMARK_QUESTIONS) == 30

    # Verify coverage across all 15 intents
    intent_counts = {}
    for bench in BENCHMARK_QUESTIONS:
        intent = bench["expected_intent"]
        intent_counts[intent] = intent_counts.get(intent, 0) + 1

    assert len(intent_counts) == 15, f"Expected 15 intents, but got {len(intent_counts)}"
    for intent in CopilotIntent:
        assert intent in intent_counts, f"Intent {intent} is missing in benchmarks"
        assert intent_counts[intent] >= 2, f"Intent {intent} has fewer than 2 benchmark queries"


def test_run_benchmark_evaluation(db_session):
    """
    Executes all 30 benchmarks against active database session.
    Asserts >= 90% intent accuracy and 100% advisory disclaimer compliance.
    """
    eval_results = run_benchmark_evaluation(db_session)

    assert eval_results["total_benchmarks"] == 30
    assert eval_results["accuracy_percentage"] >= 90.0, (
        f"Benchmark accuracy fell below 90%: {eval_results['accuracy_percentage']}% "
        f"({eval_results['passed_benchmarks']}/30 passed)"
    )

    # Verify every benchmark result carries required advisory disclaimer
    for detail in eval_results["details"]:
        assert detail["has_advisory_disclaimer"] is True, (
            f"Benchmark {detail['id']} missing required advisory disclaimer!"
        )
