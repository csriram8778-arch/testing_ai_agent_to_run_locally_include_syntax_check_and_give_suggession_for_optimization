"""HashiCorp Vault secrets adapter (KV v2), Kubernetes/AppRole/token auth."""

from __future__ import annotations

import json
import threading
from typing import Any

import hvac

from harness_mcp.settings import Settings


class VaultSecretsProvider:
    def __init__(self, settings: Settings) -> None:
        if not settings.vault_addr:
            raise ValueError("VAULT_ADDR is required for the Vault secrets backend")
        self._settings = settings
        self._client = hvac.Client(url=str(settings.vault_addr))
        self._lock = threading.Lock()
        self._authenticate()

    def _authenticate(self) -> None:
        method = self._settings.vault_auth_method
        if method == "kubernetes":
            with open("/var/run/secrets/kubernetes.io/serviceaccount/token", "r") as fh:
                jwt = fh.read()
            if not self._settings.vault_role:
                raise ValueError("VAULT_ROLE is required for VAULT_AUTH_METHOD=kubernetes")
            self._client.auth.kubernetes.login(role=self._settings.vault_role, jwt=jwt)
        elif method == "approle":
            import os

            role_id = os.environ.get("VAULT_ROLE_ID")
            secret_id = os.environ.get("VAULT_SECRET_ID")
            if not role_id or not secret_id:
                raise ValueError(
                    "VAULT_ROLE_ID and VAULT_SECRET_ID env vars are required for "
                    "VAULT_AUTH_METHOD=approle"
                )
            self._client.auth.approle.login(role_id=role_id, secret_id=secret_id)
        elif method == "token":
            import os

            token = os.environ.get("VAULT_TOKEN")
            if not token:
                raise ValueError("VAULT_TOKEN env var is required for VAULT_AUTH_METHOD=token")
            self._client.token = token
        else:  # pragma: no cover - guarded by Settings Literal
            raise ValueError(f"Unsupported VAULT_AUTH_METHOD: {method}")

    def _read(self, key: str) -> dict[str, Any]:
        path = f"{self._settings.vault_kv_path_prefix}/{key}"
        with self._lock:
            if not self._client.is_authenticated():
                self._authenticate()
            resp = self._client.secrets.kv.v2.read_secret_version(
                mount_point=self._settings.vault_kv_mount, path=path
            )
        return resp["data"]["data"]

    def get_secret(self, key: str) -> str:
        data = self._read(key)
        if "value" in data:
            return str(data["value"])
        raise KeyError(f"Vault secret at '{key}' has no 'value' field")

    def get_secret_json(self, key: str) -> dict:
        data = self._read(key)
        if "json" in data:
            return json.loads(data["json"]) if isinstance(data["json"], str) else data["json"]
        return data
