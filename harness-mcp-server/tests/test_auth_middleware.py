from __future__ import annotations

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from harness_mcp.auth.middleware import HarnessSessionAuthMiddleware
from harness_mcp.auth.token_validator import Identity, TokenValidationError
from harness_mcp.server.session_context import get_current_session


class _FakeValidator:
    def __init__(self, *, should_succeed: bool) -> None:
        self._should_succeed = should_succeed

    async def validate(self, token: str) -> Identity:
        if not self._should_succeed:
            raise TokenValidationError("rejected by fake validator")
        return Identity(user_id="user-1", harness_account_id="acct-1", expires_at=None)


async def _whoami(request: Request) -> JSONResponse:
    principal = get_current_session()
    return JSONResponse({"user_id": principal.user_id})


def _build_app(validator) -> Starlette:
    app = Starlette(routes=[Route("/whoami", _whoami), Route("/healthz", lambda r: JSONResponse({"ok": True}))])
    app.add_middleware(HarnessSessionAuthMiddleware, token_validator=validator)
    return app


def test_missing_header_rejected():
    client = TestClient(_build_app(_FakeValidator(should_succeed=True)))
    resp = client.get("/whoami")
    assert resp.status_code == 401


def test_invalid_token_rejected():
    client = TestClient(_build_app(_FakeValidator(should_succeed=False)))
    resp = client.get("/whoami", headers={"x-harness-api-key": "bad-token"})
    assert resp.status_code == 401


def test_valid_token_sets_session_context():
    client = TestClient(_build_app(_FakeValidator(should_succeed=True)))
    resp = client.get("/whoami", headers={"x-harness-api-key": "good-token"})
    assert resp.status_code == 200
    assert resp.json()["user_id"] == "user-1"


def test_health_endpoint_does_not_require_auth():
    client = TestClient(_build_app(_FakeValidator(should_succeed=False)))
    resp = client.get("/healthz")
    assert resp.status_code == 200
