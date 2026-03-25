# Architecture

## Overview

AgentBench is a modular Python framework for evaluating AI agent performance. It follows a pipeline architecture: **define tasks, run agents, collect results, score, report**.

## Module Layout

```
src/agentbench/
├── __init__.py    — Public API surface and version
├── core.py        — Central AgentBench class, data models
├── config.py      — Pydantic-based configuration
└── utils.py       — Scoring functions, formatting, serialisation
```

## Data Flow

```
BenchmarkTask (input)
        │
        ▼
  agent_fn(task)        ← user-supplied callable
        │
        ▼
  EvalResult (output)   ← includes correctness, steps, time, errors
        │
        ▼
  Scoring & Reporting   ← accuracy, efficiency, comparison tables
        │
        ▼
  Export (json/csv/md)
```

## Key Components

### BenchmarkTask

A Pydantic model representing a single evaluation task. Fields:

| Field       | Type                          | Description                             |
|-------------|-------------------------------|-----------------------------------------|
| `name`      | `str`                         | Unique task identifier                  |
| `expected`  | `Any`                         | The correct output                      |
| `evaluator` | `Callable` or `None`          | Custom `(actual, expected) -> bool`     |
| `metadata`  | `dict`                        | Arbitrary key-value pairs               |

### EvalResult

A Pydantic model capturing the outcome of running an agent on a task.

| Field              | Type          | Description                        |
|--------------------|---------------|------------------------------------|
| `task_name`        | `str`         | Which task was evaluated           |
| `expected`         | `Any`         | Expected answer                    |
| `actual`           | `Any`         | Agent's answer                     |
| `correct`          | `bool`        | Whether it passed                  |
| `steps`            | `int`         | Steps the agent took               |
| `duration_seconds` | `float`       | Wall-clock time                    |
| `error`            | `str or None` | Exception message, if any          |
| `tool_calls`       | `list[str]`   | Tool names invoked during the run  |

### AgentBench (orchestrator)

The main class ties everything together:

1. **register_task** — adds a `BenchmarkTask` to the suite.
2. **run_evaluation** — executes an agent function against tasks.
3. **score_accuracy** / **score_efficiency** — numeric scoring.
4. **compare_agents** — side-by-side evaluation of multiple agents.
5. **generate_report** — produces a Markdown report.
6. **export_results** — serialises results to JSON, CSV, or Markdown.

### BenchConfig

Environment-aware configuration via Pydantic with sensible defaults. Reads from environment variables prefixed with `AGENTBENCH_`.

## Design Decisions

- **Pydantic v2** for data validation and serialisation.
- **Callable agents** — any function `(BenchmarkTask) -> Any` qualifies as an agent, keeping the interface minimal.
- **Pluggable evaluators** — tasks can carry custom evaluator functions; the default is case-insensitive exact match for strings.
- **No external dependencies** beyond Pydantic — the framework stays lightweight and easy to embed.
