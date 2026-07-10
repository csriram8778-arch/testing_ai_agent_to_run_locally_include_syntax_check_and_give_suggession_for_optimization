from __future__ import annotations

import pytest

from harness_mcp.settings import get_settings

_REQUIRED_ENV = {
    "HARNESS_ACCOUNT_ID": "test-account",
    "SECRETS_BACKEND": "vault",
    "VAULT_ADDR": "https://vault.example.internal:8200",
    "HARNESS_BASE_URL": "https://app.harness.io/",
    "HARNESS_AUTO_APPROVE_RISK": "none",
    "CONFIRMATION_STORE_BACKEND": "memory",
    "AUDIT_FAIL_CLOSED": "true",
    "AUDIT_LOCAL_FILE_PATH": "/tmp/harness-mcp-test-audit.jsonl",
}


@pytest.fixture(autouse=True)
def _base_settings_env(monkeypatch, tmp_path):
    for key, value in _REQUIRED_ENV.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setenv("AUDIT_LOCAL_FILE_PATH", str(tmp_path / "audit.jsonl"))
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
