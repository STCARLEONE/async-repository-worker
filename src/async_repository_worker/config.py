from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Settings:
    # Worker Pool
    worker_count: int = 4
    job_timeout: float = 30.0
    shutdown_timeout: float = 10.0

    # Queue
    queue_max_size: int = 1000

    # Rate Limiter (Global)
    rate_limit: float = 5.0  # requests per second
    rate_capacity: int = 5  # burst capacity

    # Retry Policy
    retry_attempts: int = 3
    retry_base_delay: float = 0.5  # seconds
    retry_max_delay: float = 30.0  # seconds
    retry_jitter: bool = True  # add jitter to prevent thundering herd

    # GitHub API
    github_base_url: str = "https://api.github.com"
    github_api_timeout: float = 30.0
    github_max_retries: int = 3

    # Database / Cache
    data_dir: Path = field(default_factory=lambda: Path("./data"))
    database_path: Path | None = None

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"  # "json" or "text"

    # Observability
    enable_metrics: bool = True

    @classmethod
    def from_env(cls) -> Settings:
        """Create settings from environment variables."""
        data_dir = Path(os.getenv("DATA_DIR", "./data"))
        database_path_str = os.getenv("DATABASE_PATH")
        database_path = (
            Path(database_path_str)
            if database_path_str
            else data_dir / "repositories.db"
        )

        return cls(
            # Worker Pool
            worker_count=int(os.getenv("WORKER_COUNT", "4")),
            job_timeout=float(os.getenv("JOB_TIMEOUT", "30.0")),
            shutdown_timeout=float(os.getenv("SHUTDOWN_TIMEOUT", "10.0")),
            # Queue
            queue_max_size=int(os.getenv("QUEUE_MAX_SIZE", "1000")),
            # Rate Limiter
            rate_limit=float(os.getenv("RATE_LIMIT", "5.0")),
            rate_capacity=int(os.getenv("RATE_CAPACITY", "5")),
            # Retry
            retry_attempts=int(os.getenv("RETRY_ATTEMPTS", "3")),
            retry_base_delay=float(os.getenv("RETRY_BASE_DELAY", "0.5")),
            retry_max_delay=float(os.getenv("RETRY_MAX_DELAY", "30.0")),
            retry_jitter=os.getenv("RETRY_JITTER", "true").lower() == "true",
            # GitHub API
            github_base_url=os.getenv("GITHUB_BASE_URL", "https://api.github.com"),
            github_api_timeout=float(os.getenv("GITHUB_API_TIMEOUT", "30.0")),
            github_max_retries=int(os.getenv("GITHUB_MAX_RETRIES", "3")),
            # Database
            data_dir=data_dir,
            database_path=database_path,
            # Logging
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
            log_format=os.getenv("LOG_FORMAT", "json"),
            # Observability
            enable_metrics=os.getenv("ENABLE_METRICS", "true").lower() == "true",
        )

    def validate(self) -> None:
        """Validate settings values."""
        if self.worker_count < 1:
            raise ValueError("worker_count must be >= 1")
        if self.rate_limit <= 0:
            raise ValueError("rate_limit must be > 0")
        if self.rate_capacity < 1:
            raise ValueError("rate_capacity must be >= 1")
        if self.retry_attempts < 0:
            raise ValueError("retry_attempts must be >= 0")
        if self.retry_base_delay < 0:
            raise ValueError("retry_base_delay must be >= 0")
        if self.retry_max_delay < self.retry_base_delay:
            raise ValueError("retry_max_delay must be >= retry_base_delay")
        if self.job_timeout <= 0:
            raise ValueError("job_timeout must be > 0")
        if self.github_api_timeout <= 0:
            raise ValueError("github_api_timeout must be > 0")

    def ensure_directories(self) -> None:
        """Create necessary directories."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        if self.database_path and self.database_path.parent:
            self.database_path.parent.mkdir(parents=True, exist_ok=True)
