"""Utility functions — scoring, comparison helpers, and formatting."""

from __future__ import annotations

import csv
import io
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from agentbench.core import EvalResult


# ---------------------------------------------------------------------------
# Default evaluator
# ---------------------------------------------------------------------------

def default_evaluator(actual: Any, expected: Any) -> bool:
    """Exact-match evaluator with basic normalisation for strings."""
    if isinstance(actual, str) and isinstance(expected, str):
        return actual.strip().lower() == expected.strip().lower()
    return actual == expected


# ---------------------------------------------------------------------------
# Scoring functions
# ---------------------------------------------------------------------------

def calculate_accuracy(results: list[EvalResult]) -> float:
    """Return accuracy as a float in [0.0, 1.0]."""
    if not results:
        return 0.0
    return sum(1 for r in results if r.correct) / len(results)


def calculate_efficiency_score(results: list[EvalResult], max_steps: int) -> float:
    """Return an efficiency score in [0.0, 1.0].

    Computed as ``1 - (avg_steps / max_steps)`` clamped to [0, 1].
    Lower step counts produce higher efficiency scores.
    """
    if not results or max_steps <= 0:
        return 0.0
    avg_steps = sum(r.steps for r in results) / len(results)
    score = 1.0 - (avg_steps / max_steps)
    return max(0.0, min(1.0, score))


def calculate_pass_rate(results: list[EvalResult]) -> dict[str, float]:
    """Return per-task pass rate (useful when a task is run multiple times)."""
    from collections import defaultdict

    counts: dict[str, list[bool]] = defaultdict(list)
    for r in results:
        counts[r.task_name].append(r.correct)
    return {name: sum(v) / len(v) for name, v in counts.items()}


def average_duration(results: list[EvalResult]) -> float:
    """Return average wall-clock duration in seconds."""
    if not results:
        return 0.0
    return sum(r.duration_seconds for r in results) / len(results)


def tool_usage_summary(results: list[EvalResult]) -> dict[str, int]:
    """Return a mapping of tool name to total invocation count."""
    from collections import Counter

    counter: Counter[str] = Counter()
    for r in results:
        counter.update(r.tool_calls)
    return dict(counter)


# ---------------------------------------------------------------------------
# Comparison helpers
# ---------------------------------------------------------------------------

def format_comparison_table(
    all_results: dict[str, list[EvalResult]],
    max_steps: int = 50,
) -> str:
    """Build a Markdown table comparing multiple agents."""
    lines = [
        "| Agent | Accuracy | Efficiency | Avg Time | Passed | Failed |",
        "|-------|----------|------------|----------|--------|--------|",
    ]

    for agent_name, results in all_results.items():
        accuracy = calculate_accuracy(results)
        efficiency = calculate_efficiency_score(results, max_steps)
        avg_time = average_duration(results)
        passed = sum(1 for r in results if r.correct)
        failed = len(results) - passed
        lines.append(
            f"| {agent_name} | {accuracy:.2%} | {efficiency:.2%} "
            f"| {format_duration(avg_time)} | {passed} | {failed} |"
        )

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def format_duration(seconds: float) -> str:
    """Format a duration in seconds to a human-readable string."""
    if seconds < 1.0:
        return f"{seconds * 1000:.1f}ms"
    if seconds < 60.0:
        return f"{seconds:.2f}s"
    minutes = int(seconds // 60)
    secs = seconds % 60
    return f"{minutes}m {secs:.1f}s"


def results_to_dicts(results: list[EvalResult]) -> list[dict[str, Any]]:
    """Convert a list of ``EvalResult`` to plain dicts."""
    return [r.model_dump() for r in results]


def results_to_csv(results: list[EvalResult]) -> str:
    """Serialise results to a CSV string."""
    buf = io.StringIO()
    fieldnames = [
        "task_name",
        "expected",
        "actual",
        "correct",
        "steps",
        "duration_seconds",
        "error",
        "tool_calls",
    ]
    writer = csv.DictWriter(buf, fieldnames=fieldnames)
    writer.writeheader()
    for r in results:
        row = r.model_dump()
        row["tool_calls"] = ";".join(row.get("tool_calls", []))
        writer.writerow({k: row[k] for k in fieldnames})
    return buf.getvalue()


def results_to_markdown_table(results: list[EvalResult]) -> str:
    """Render results as a Markdown table."""
    lines = [
        "| Task | Correct | Steps | Duration | Error |",
        "|------|---------|-------|----------|-------|",
    ]
    for r in results:
        mark = "PASS" if r.correct else "FAIL"
        err = r.error or "—"
        lines.append(
            f"| {r.task_name} | {mark} | {r.steps} "
            f"| {format_duration(r.duration_seconds)} | {err} |"
        )
    return "\n".join(lines)
