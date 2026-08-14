from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Settings:
    worker_count: int = 4
    rate_limit: float = 5.0
    rate_capacity: int = 5
    retry_attempts: int = 3
    retry_base_delay: float = 0.5
    retry_max_delay: float = 30.0
    job_timeout: float = 30.0

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            worker_count=int(os.getenv("WORKER_COUNT", "4")),
            rate_limit=float(os.getenv("RATE_LIMIT", "5")),
            rate_capacity=int(os.getenv("RATE_CAPACITY", "5")),
            retry_attempts=int(os.getenv("RETRY_ATTEMPTS", "3")),
            retry_base_delay=float(
                os.getenv("RETRY_BASE_DELAY", "0.5")
            ),
            retry_max_delay=float(
                os.getenv("RETRY_MAX_DELAY", "30")
            ),
            job_timeout=float(
                os.getenv("JOB_TIMEOUT", "30")
            ),
        )