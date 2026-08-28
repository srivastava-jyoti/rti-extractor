import pytest

from rti_extractor.config import Settings


def test_settings_load(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test")
    monkeypatch.setenv("GEMINI_MODEL", "test-model")
    monkeypatch.setenv("DATABASE_URL", "postgresql://x/y")
    monkeypatch.setenv("STRAPI_BASE_URL", "http://x")
    s = Settings(_env_file=None)
    assert s.dry_run is True
