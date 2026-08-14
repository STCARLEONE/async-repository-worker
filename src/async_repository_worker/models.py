from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any


class JobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    RETRYING = "retrying"
    FAILED = "failed"


class JobPriority(StrEnum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass(slots=True)
class RepositoryJob:
    repository: str
    priority: JobPriority = JobPriority.NORMAL
    status: JobStatus = JobStatus.PENDING
    max_attempts: int = 3
    timeout: float = 30.0
    metadata: dict[str, Any] = field(default_factory=dict)

    attempt: int = 0
    error: str | None = None

    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    started_at: datetime | None = None
    completed_at: datetime | None = None

    @property
    def can_retry(self) -> bool:
        return self.attempt < self.max_attempts

    def mark_running(self) -> None:
        self.status = JobStatus.RUNNING
        self.started_at = datetime.now(timezone.utc)

    def mark_success(self) -> None:
        self.status = JobStatus.SUCCESS
        self.completed_at = datetime.now(timezone.utc)
        self.error = None

    def mark_failed(self, error: str) -> None:
        self.status = JobStatus.FAILED
        self.completed_at = datetime.now(timezone.utc)
        self.error = error

    def mark_retrying(self, error: str) -> None:
        self.status = JobStatus.RETRYING
        self.error = error
        self.attempt += 1
