from __future__ import annotations

import pytest

from harness_mcp.guardrails.deny_list import DeniedByGuardrailError, check_allowed
from harness_mcp.guardrails.risk import RiskTier, TOOL_RISK, requires_confirmation


def test_every_write_tool_requires_confirmation():
    for name, tier in TOOL_RISK.items():
        if tier == RiskTier.WRITE:
            assert requires_confirmation(name) is True
        elif tier == RiskTier.READ_ONLY:
            assert requires_confirmation(name) is False


def test_unclassified_tool_raises():
    with pytest.raises(KeyError):
        requires_confirmation("some_tool_nobody_registered")


def test_deny_list_blocks_delete():
    with pytest.raises(DeniedByGuardrailError):
        check_allowed("DELETE", "ng/api/pipelines/my-pipeline")


def test_deny_list_blocks_secret_read():
    with pytest.raises(DeniedByGuardrailError):
        check_allowed("GET", "ng/api/secrets/my-secret")


def test_deny_list_blocks_rbac():
    with pytest.raises(DeniedByGuardrailError):
        check_allowed("POST", "ng/api/rbac/role-assignments")


def test_deny_list_blocks_token_management():
    with pytest.raises(DeniedByGuardrailError):
        check_allowed("POST", "ng/api/api-key/create")


def test_deny_list_allows_ordinary_read():
    check_allowed("GET", "pipeline/api/pipelines/my-pipeline")  # must not raise


def test_deny_list_allows_ordinary_write_tool_call():
    check_allowed("POST", "pipeline/api/pipeline/execute/my-pipeline")  # must not raise
