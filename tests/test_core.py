"""Tests for AgentBench core functionality."""

from __future__ import annotations

import json

import pytest

from agentbench import AgentBench, BenchmarkTask, EvalResult


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def bench() -> AgentBench:
    b = AgentBench(name="test-suite")
    b.register_task(name="greeting", expected="hello")
    b.register_task(name="math", expected="4")
    b.register_task(
        name="custom-eval",
        expected=42,
        evaluator=lambda actual, expected: actual == expected,
    )
    return b


def _perfect_agent(task: BenchmarkTask) -> str | int:
    answers = {"greeting": "hello", "math": "4", "custom-eval": 42}
    return answers[task.name]


def _bad_agent(task: BenchmarkTask) -> str:
    return "wrong"


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestRegisterTask:
    def test_register_adds_task(self, bench: AgentBench) -> None:
        assert len(bench.tasks) == 3
        names = [t.name for t in bench.tasks]
        assert "greeting" in names
        assert "math" in names

    def test_register_returns_task(self) -> None:
        b = AgentBench(name="t")
        task = b.register_task(name="x", expected="y")
        assert isinstance(task, BenchmarkTask)
        assert task.name == "x"


class TestRunEvaluation:
    def test_perfect_agent_all_correct(self, bench: AgentBench) -> None:
        results = bench.run_evaluation(_perfect_agent)
        assert all(r.correct for r in results)
        assert len(results) == 3

    def test_bad_agent_failures(self, bench: AgentBench) -> None:
        results = bench.run_evaluation(_bad_agent)
        assert not any(r.correct for r in results)

    def test_agent_exception_captured(self) -> None:
        b = AgentBench(name="err")
        b.register_task(name="boom", expected="ok")

        def exploding_agent(task: BenchmarkTask) -> str:
            raise RuntimeError("kaboom")

        results = b.run_evaluation(exploding_agent)
        assert len(results) == 1
        assert results[0].error == "kaboom"
        assert not results[0].correct


class TestScoring:
    def test_accuracy_perfect(self, bench: AgentBench) -> None:
        results = bench.run_evaluation(_perfect_agent)
        assert bench.score_accuracy(results) == pytest.approx(1.0)

    def test_accuracy_zero(self, bench: AgentBench) -> None:
        results = bench.run_evaluation(_bad_agent)
        assert bench.score_accuracy(results) == pytest.approx(0.0)

    def test_efficiency_score(self, bench: AgentBench) -> None:
        results = bench.run_evaluation(_perfect_agent)
        eff = bench.score_efficiency(results, max_steps=10)
        # Each task defaults to 1 step, so efficiency = 1 - (1/10) = 0.9
        assert eff == pytest.approx(0.9)


class TestReportAndExport:
    def test_generate_report_contains_summary(self, bench: AgentBench) -> None:
        results = bench.run_evaluation(_perfect_agent)
        report = bench.generate_report(results)
        assert "AgentBench Report" in report
        assert "100.00%" in report

    def test_export_json(self, bench: AgentBench) -> None:
        results = bench.run_evaluation(_perfect_agent)
        content = bench.export_results(results, format="json")
        data = json.loads(content)
        assert isinstance(data, list)
        assert len(data) == 3

    def test_export_csv(self, bench: AgentBench) -> None:
        results = bench.run_evaluation(_perfect_agent)
        content = bench.export_results(results, format="csv")
        assert "task_name" in content
        assert "greeting" in content

    def test_export_markdown(self, bench: AgentBench) -> None:
        results = bench.run_evaluation(_perfect_agent)
        content = bench.export_results(results, format="markdown")
        assert "| Task |" in content


class TestCompareAgents:
    def test_comparison_table(self, bench: AgentBench) -> None:
        table = bench.compare_agents(
            {"Perfect": _perfect_agent, "Bad": _bad_agent},
        )
        assert "Perfect" in table
        assert "Bad" in table
        assert "100.00%" in table
        assert "0.00%" in table
