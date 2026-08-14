from async_repository_worker.config import Settings


def test_default_settings():
    settings = Settings()

    assert settings.worker_count == 4
    assert settings.rate_limit == 5.0
    assert settings.rate_capacity == 5
    assert settings.retry_attempts == 3


def test_environment_settings(monkeypatch):
    monkeypatch.setenv("WORKER_COUNT", "8")
    monkeypatch.setenv("RATE_LIMIT", "10")
    monkeypatch.setenv("RETRY_ATTEMPTS", "5")

    settings = Settings.from_env()

    assert settings.worker_count == 8
    assert settings.rate_limit == 10
    assert settings.retry_attempts == 5
