"""Configuration for AgentBench."""

from __future__ import annotations

import os
from pydantic import BaseModel, Field


class BenchConfig(BaseModel):
    """Global configuration for an AgentBench session."""

    name: str = Field(default="agentbench", description="Name of the benchmark suite")
    log_level: str = Field(
        default_factory=lambda: os.getenv("AGENTBENCH_LOG_LEVEL", "INFO"),
        description="Logging level",
    )
    output_dir: str = Field(
        default_factory=lambda: os.getenv("AGENTBENCH_OUTPUT_DIR", "./results"),
        description="Directory for output files",
    )
    max_steps: int = Field(
        default_factory=lambda: int(os.getenv("AGENTBENCH_MAX_STEPS", "50")),
        description="Maximum steps allowed per task",
    )
    export_format: str = Field(
        default_factory=lambda: os.getenv("AGENTBENCH_EXPORT_FORMAT", "json"),
        description="Default export format (json, csv, markdown)",
    )
    task_timeout: int = Field(
        default_factory=lambda: int(os.getenv("AGENTBENCH_TASK_TIMEOUT", "300")),
        description="Timeout per task in seconds",
    )

    model_config = {"validate_assignment": True}
