from __future__ import annotations

from harness_mcp.redaction.patterns import scrub_string
from harness_mcp.redaction.sanitizer import apply_redaction


def test_scrub_string_redacts_ip_and_email():
    cleaned, hits = scrub_string("connect to 10.0.0.5 or mail admin@example.com")
    assert "10.0.0.5" not in cleaned
    assert "admin@example.com" not in cleaned
    assert "IPV4_ADDRESS" in hits
    assert "EMAIL_ADDRESS" in hits


def test_scrub_string_leaves_clean_text_untouched():
    cleaned, hits = scrub_string("pipeline succeeded")
    assert cleaned == "pipeline succeeded"
    assert hits == []


def test_allowlist_drops_unlisted_fields():
    payload = {
        "identifier": "pipe-1",
        "name": "My Pipeline",
        "internalDebugField": "should-not-survive",
        "secretHint": "should-also-not-survive",
    }
    sanitized, _ = apply_redaction("get_pipeline", payload)
    assert sanitized["identifier"] == "pipe-1"
    assert sanitized["name"] == "My Pipeline"
    assert "internalDebugField" not in sanitized
    assert "secretHint" not in sanitized


def test_allowlist_projects_list_items():
    payload = {
        "content": [
            {"identifier": "p1", "name": "One", "secretStuff": "x"},
            {"identifier": "p2", "name": "Two", "secretStuff": "y"},
        ],
        "totalElements": 2,
    }
    sanitized, _ = apply_redaction("list_pipelines", payload)
    assert sanitized["totalElements"] == 2
    assert len(sanitized["content"]) == 2
    for item in sanitized["content"]:
        assert set(item.keys()) <= {
            "identifier", "name", "description", "tags", "status", "createdAt",
            "lastModifiedAt", "createdBy", "accountId", "orgIdentifier", "projectIdentifier",
        }
        assert "secretStuff" not in item


def test_envelope_unwrap_preserves_status_and_projects_data():
    payload = {
        "status": "SUCCESS",
        "correlationId": "abc-123",
        "metaData": None,
        "data": {"identifier": "pipe-1", "name": "My Pipeline", "internalOnly": "drop-me"},
    }
    sanitized, _ = apply_redaction("get_pipeline", payload)
    assert sanitized["status"] == "SUCCESS"
    assert sanitized["correlationId"] == "abc-123"
    assert sanitized["data"]["identifier"] == "pipe-1"
    assert "internalOnly" not in sanitized["data"]


def test_regex_scrub_applies_even_to_allowlisted_field():
    payload = {"identifier": "pipe-1", "name": "contact admin@example.com for access"}
    sanitized, hits = apply_redaction("get_pipeline", payload)
    assert "admin@example.com" not in sanitized["name"]
    assert "EMAIL_ADDRESS" in hits


def test_unknown_tool_falls_back_to_common_allowlist():
    payload = {"identifier": "x", "name": "y", "somethingElse": "z"}
    sanitized, _ = apply_redaction("some_future_tool_not_yet_in_allowlist", payload)
    assert sanitized["identifier"] == "x"
    assert "somethingElse" not in sanitized
