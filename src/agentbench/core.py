"""Core module — AgentBench class, BenchmarkTask, and EvalResult."""

from __future__ import annotations

import time
import logging
from typing import Any, Callable, Optional

from pydantic import BaseModel, Field

from agentbench.config import BenchConfig
from agentbench.utils import (
    calculate_accuracy,
    calculate_efficiency_score,
    format_duration,
    format_comparison_table,
    default_evaluator,
    results_to_csv,
    results_to_markdown_table,
    results_to_dicts,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

class BenchmarkTask(BaseModel):
    """A single benchmark task with an expected output and optional evaluator."""

    name: str = Field(..., description="Unique task identifier")
    expected: Any = Field(..., description="Expected output from the agent")
    evaluator: Optional[Callable[[Any, Any], bool]] = Field(
        default=None,
        description="Custom evaluator function(actual, expected) -> bool",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Arbitrary metadata attached to the task",
    )

    model_config = {"arbitrary_types_allowed": True}


class EvalResult(BaseModel):
    """Result of evaluating a single task."""

    task_name: str = Field(..., description="Name of the task that was evaluated")
    expected: Any = Field(..., description="Expected output")
    actual: Any = Field(default=None, description="Actual output from the agent")
    correct: bool = Field(default=False, description="Whether the result is correct")
    steps: int = Field(default=0, description="Number of steps the agent took")
    duration_seconds: float = Field(
        default=0.0, description="Wall-clock time in seconds"
    )
    error: Optional[str] = Field(
        default=None, description="Error message if the agent raised an exception"
    )
    tool_calls: list[str] = Field(
        default_factory=list,
        description="List of tool names the agent invoked during execution",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata from the evaluation run",
    )


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------

class AgentBench:
    """Evaluation and benchmarking suite for AI agents.

    Workflow
    --------
    1. Create an ``AgentBench`` instance.
    2. Register tasks via ``register_task``.
    3. Run one or more agents with ``run_evaluation`` / ``compare_agents``.
    4. Inspect results with ``score_accuracy``, ``score_efficiency``,
       ``generate_report``, and ``export_results``.
    """

    def __init__(
        self,
        name: str = "agentbench",
        config: BenchConfig | None = None,
    ) -> None:
        self.config = config or BenchConfig(name=name)
        self.tasks: list[BenchmarkTask] = []
        logging.basicConfig(level=getattr(logging, self.config.log_level, logging.INFO))
        logger.info("AgentBench '%s' initialised", self.config.name)

    # ------------------------------------------------------------------
    # Task registration
    # ------------------------------------------------------------------

    def register_task(
        self,
        name: str,
        expected: Any,
        evaluator: Callable[[Any, Any], bool] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> BenchmarkTask:
        """Register a new benchmark task.

        Parameters
        ----------
        name:
            Unique task identifier.
        expected:
            The expected output the agent should produce.
        evaluator:
            Optional custom evaluator ``(actual, expected) -> bool``.
            Falls back to exact-match if not provided.
        metadata:
            Optional dict of extra information about the task.

        Returns
        -------
        BenchmarkTask
            The newly created task.
        """
        task = BenchmarkTask(
            name=name,
            expected=expected,
            evaluator=evaluator,
            metadata=metadata or {},
        )
        self.tasks.append(task)
        logger.info("Registered task '%s'", name)
        return task

    # ------------------------------------------------------------------
    # Evaluation
    # ------------------------------------------------------------------

    def run_evaluation(
        self,
        agent_fn: Callable[[BenchmarkTask], Any],
        tasks: list[BenchmarkTask] | None = None,
    ) -> list[EvalResult]:
        """Run *agent_fn* on each task and collect results.

        The agent function receives a ``BenchmarkTask`` and must return
        the answer.  It may optionally return a ``dict`` with keys
        ``answer``, ``steps``, and ``tool_calls`` for richer reporting.
        """
        target_tasks = tasks if tasks is not None else self.tasks
        results: list[EvalResult] = []

        for task in target_tasks:
            start = time.perf_counter()
            error: str | None = None
            actual: Any = None
            steps = 1
            tool_calls: list[str] = []

            try:
                raw = agent_fn(task)
                if isinstance(raw, dict):
                    actual = raw.get("answer", raw)
                    steps = raw.get("steps", 1)
                    tool_calls = raw.get("tool_calls", [])
                else:
                    actual = raw
            except Exception as exc:  # noqa: BLE001
                error = str(exc)
                logger.warning("Task '%s' raised: %s", task.name, error)

            elapsed = time.perf_counter() - start
            eval_fn = task.evaluator or default_evaluator
            correct = False if error else eval_fn(actual, task.expected)

            result = EvalResult(
                task_name=task.name,
                expected=task.expected,
                actual=actual,
                correct=correct,
                steps=steps,
                duration_seconds=round(elapsed, 6),
                error=error,
                tool_calls=tool_calls,
            )
            results.append(result)
            logger.info(
                "Task '%s': correct=%s  time=%.4fs",
                task.name,
                correct,
                elapsed,
            )

        return results

    # ------------------------------------------------------------------
    # Scoring
    # ------------------------------------------------------------------

    def score_accuracy(self, results: list[EvalResult]) -> float:
        """Return accuracy as a float in [0.0, 1.0]."""
        return calculate_accuracy(results)

    def score_efficiency(
        self,
        results: list[EvalResult],
        max_steps: int | None = None,
    ) -> float:
        """Return an efficiency score in [0.0, 1.0].

        Efficiency is computed as ``1 - (avg_steps / max_steps)`` clamped
        to [0, 1].  Lower step counts yield higher scores.
        """
        limit = max_steps or self.config.max_steps
        return calculate_efficiency_score(results, limit)

    # ------------------------------------------------------------------
    # Comparison
    # ------------------------------------------------------------------

    def compare_agents(
        self,
        agent_fns: dict[str, Callable[[BenchmarkTask], Any]],
        tasks: list[BenchmarkTask] | None = None,
    ) -> str:
        """Evaluate multiple agents and return a formatted comparison table.

        Parameters
        ----------
        agent_fns:
            Mapping of agent name to callable.
        tasks:
            Tasks to evaluate on; defaults to ``self.tasks``.

        Returns
        -------
        str
            A human-readable Markdown comparison table.
        """
        all_results: dict[str, list[EvalResult]] = {}
        for agent_name, fn in agent_fns.items():
            logger.info("Evaluating agent '%s' ...", agent_name)
            all_results[agent_name] = self.run_evaluation(fn, tasks)

        return format_comparison_table(all_results, self.config.max_steps)

    # ------------------------------------------------------------------
    # Reporting & export
    # ------------------------------------------------------------------

    def generate_report(self, results: list[EvalResult]) -> str:
        """Generate a human-readable Markdown report for *results*."""
        accuracy = self.score_accuracy(results)
        efficiency = self.score_efficiency(results)
        total_time = sum(r.duration_seconds for r in results)
        passed = sum(1 for r in results if r.correct)
        failed = len(results) - passed
        errors = sum(1 for r in results if r.error)

        lines = [
            f"# AgentBench Report — {self.config.name}",
            "",
            "## Summary",
            "",
            f"| Metric         | Value            |",
            f"|----------------|------------------|",
            f"| Tasks          | {len(results)}   |",
            f"| Passed         | {passed}         |",
            f"| Failed         | {failed}         |",
            f"| Errors         | {errors}         |",
            f"| Accuracy       | {accuracy:.2%}   |",
            f"| Efficiency     | {efficiency:.2%} |",
            f"| Total time     | {format_duration(total_time)} |",
            "",
            "## Task Details",
            "",
            "| Task | Correct | Steps | Time | Error |",
            "|------|---------|-------|------|-------|",
        ]

        for r in results:
            mark = "PASS" if r.correct else "FAIL"
            err = r.error or "—"
            lines.append(
                f"| {r.task_name} | {mark} | {r.steps} "
                f"| {format_duration(r.duration_seconds)} | {err} |"
            )

        lines.append("")
        return "\n".join(lines)

    def export_results(
        self,
        results: list[EvalResult],
        format: str = "json",  # noqa: A002
        path: str | None = None,
    ) -> str:
        """Export results to a file or return as a string.

        Parameters
        ----------
        results:
            Evaluation results to export.
        format:
            One of ``json``, ``csv``, or ``markdown``.
        path:
            Optional file path.  If provided the content is written to
            disk *and* returned.

        Returns
        -------
        str
            The serialised content.
        """
        import json as json_mod

        if format == "json":
            content = json_mod.dumps(results_to_dicts(results), indent=2)
        elif format == "csv":
            content = results_to_csv(results)
        elif format == "markdown":
            content = results_to_markdown_table(results)
        else:
            raise ValueError(f"Unsupported format: {format!r}")

        if path:
            with open(path, "w") as fh:
                fh.write(content)
            logger.info("Results exported to %s", path)

        return content
