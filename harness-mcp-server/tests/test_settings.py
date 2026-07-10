from __future__ import annotations

import pytest
from pydantic import ValidationError

from harness_mcp.settings import Settings, get_settings


def test_default_settings_load(monkeypatch):
    get_settings.cache_clear()
    settings = get_settings()
    assert settings.harness_auto_approve_risk == "none"
    assert str(settings.harness_base_url).startswith("https://")


def test_auto_approve_risk_locked_to_none(monkeypatch):
    monkeypatch.setenv("HARNESS_AUTO_APPROVE_RISK", "low")
    with pytest.raises(ValidationError):
        Settings()


def test_plaintext_harness_url_rejected(monkeypatch):
    monkeypatch.setenv("HARNESS_BASE_URL", "http://app.harness.io/")
    with pytest.raises(ValidationError):
        Settings()


def test_vault_backend_requires_vault_addr(monkeypatch):
    monkeypatch.delenv("VAULT_ADDR", raising=False)
    with pytest.raises(ValidationError):
        Settings()


def test_redis_confirmation_backend_requires_redis_url(monkeypatch):
    monkeypatch.setenv("CONFIRMATION_STORE_BACKEND", "redis")
    monkeypatch.delenv("REDIS_URL", raising=False)
    with pytest.raises(ValidationError):
        Settings()
