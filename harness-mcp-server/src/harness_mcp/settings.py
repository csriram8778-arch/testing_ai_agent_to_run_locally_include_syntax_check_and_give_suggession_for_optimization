"""Single source of truth for server configuration.

Every value is read from the environment exactly once at process start into a
frozen ``Settings`` singleton. Nothing downstream (a tool, a prompt, a request
parameter) can mutate these values at runtime -- that is what makes
``HARNESS_AUTO_APPROVE_RISK=none`` and the TLS-only / no-plaintext-secrets
requirements structural rather than conventional.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import AnyHttpUrl, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

McpMode = Literal["stdio", "http"]
SecretsBackend = Literal["vault", "aws-secrets-manager"]
HarnessEdition = Literal["saas", "self_managed_ee"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        frozen=True,
    )

    # -- Server / transport -------------------------------------------------
    mcp_mode: McpMode = Field(default="stdio", alias="MCP_MODE")
    http_host: str = Field(default="0.0.0.0", alias="HTTP_HOST")
    http_port: int = Field(default=8443, alias="HTTP_PORT")
    # In HTTP mode the server MUST terminate or sit behind TLS. This flag only
    # controls whether uvicorn itself terminates TLS (set False when a
    # sidecar/ingress does it) -- it never permits a plaintext *external*
    # listener in the reference Kubernetes deployment.
    tls_terminated_upstream: bool = Field(default=True, alias="TLS_TERMINATED_UPSTREAM")
    tls_cert_path: str | None = Field(default=None, alias="TLS_CERT_PATH")
    tls_key_path: str | None = Field(default=None, alias="TLS_KEY_PATH")

    # -- Hard safety constraint ----------------------------------------------
    # This is intentionally the ONLY legal value. Any other value fails
    # startup validation below. There is no code path that reads this field
    # more than once, and no tool/prompt parameter can override it.
    harness_auto_approve_risk: Literal["none"] = Field(
        default="none", alias="HARNESS_AUTO_APPROVE_RISK"
    )

    # -- Harness -------------------------------------------------------------
    harness_edition: HarnessEdition = Field(default="saas", alias="HARNESS_EDITION")
    harness_account_id: str = Field(alias="HARNESS_ACCOUNT_ID")
    harness_org_id: str | None = Field(default=None, alias="HARNESS_ORG_ID")
    harness_project_id: str | None = Field(default=None, alias="HARNESS_PROJECT_ID")
    harness_base_url: AnyHttpUrl = Field(
        default="https://app.harness.io", alias="HARNESS_BASE_URL"
    )
    # Used only in stdio (single-user, local dev) mode. In HTTP mode the
    # server holds zero Harness credentials -- every caller supplies their
    # own token via the x-harness-api-key header.
    harness_stdio_service_account_token_env: str = Field(
        default="HARNESS_SAT_TOKEN", alias="HARNESS_STDIO_TOKEN_ENV_VAR"
    )

    # -- Secrets backend -------------------------------------------------
    secrets_backend: SecretsBackend = Field(alias="SECRETS_BACKEND")

    vault_addr: AnyHttpUrl | None = Field(default=None, alias="VAULT_ADDR")
    vault_auth_method: Literal["kubernetes", "approle", "token"] = Field(
        default="kubernetes", alias="VAULT_AUTH_METHOD"
    )
    vault_role: str | None = Field(default=None, alias="VAULT_ROLE")
    vault_kv_mount: str = Field(default="secret", alias="VAULT_KV_MOUNT")
    vault_kv_path_prefix: str = Field(
        default="harness-mcp-server", alias="VAULT_KV_PATH_PREFIX"
    )

    aws_secrets_manager_region: str | None = Field(
        default=None, alias="AWS_SECRETS_MANAGER_REGION"
    )
    aws_secrets_manager_prefix: str = Field(
        default="harness-mcp-server/", alias="AWS_SECRETS_MANAGER_PREFIX"
    )

    # -- Approval / confirmation ----------------------------------------
    confirmation_ttl_seconds: int = Field(default=300, alias="CONFIRMATION_TTL_SECONDS")
    confirmation_store_backend: Literal["memory", "redis"] = Field(
        default="memory", alias="CONFIRMATION_STORE_BACKEND"
    )
    redis_url: str | None = Field(default=None, alias="REDIS_URL")

    # -- Audit -----------------------------------------------------------
    audit_fail_closed: bool = Field(default=True, alias="AUDIT_FAIL_CLOSED")
    audit_local_file_path: str = Field(
        default="/var/log/harness-mcp/audit.jsonl", alias="AUDIT_LOCAL_FILE_PATH"
    )
    audit_s3_bucket: str | None = Field(default=None, alias="AUDIT_S3_BUCKET")
    audit_s3_region: str | None = Field(default=None, alias="AUDIT_S3_REGION")
    audit_s3_prefix: str = Field(default="harness-mcp-audit/", alias="AUDIT_S3_PREFIX")
    audit_webhook_url: AnyHttpUrl | None = Field(default=None, alias="AUDIT_WEBHOOK_URL")
    audit_webhook_signing_secret_ref: str | None = Field(
        default=None, alias="AUDIT_WEBHOOK_SIGNING_SECRET_REF"
    )

    # -- Observability -----------------------------------------------------
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    metrics_port: int = Field(default=9090, alias="METRICS_PORT")

    @field_validator("harness_auto_approve_risk")
    @classmethod
    def _lock_auto_approve(cls, v: str) -> str:
        if v != "none":
            raise ValueError(
                "HARNESS_AUTO_APPROVE_RISK must be 'none'. Auto-approval of "
                "write/deploy/destructive actions is a hard constraint of this "
                "server and cannot be relaxed via configuration."
            )
        return v

    @model_validator(mode="after")
    def _validate_backend_config(self) -> "Settings":
        if self.secrets_backend == "vault" and not self.vault_addr:
            raise ValueError("VAULT_ADDR is required when SECRETS_BACKEND=vault")
        if self.secrets_backend == "aws-secrets-manager" and not self.aws_secrets_manager_region:
            raise ValueError(
                "AWS_SECRETS_MANAGER_REGION is required when "
                "SECRETS_BACKEND=aws-secrets-manager"
            )
        if self.confirmation_store_backend == "redis" and not self.redis_url:
            raise ValueError("REDIS_URL is required when CONFIRMATION_STORE_BACKEND=redis")
        if str(self.harness_base_url).startswith("http://"):
            raise ValueError("HARNESS_BASE_URL must be HTTPS -- plaintext HTTP is not permitted")
        if self.mcp_mode == "http" and not self.tls_terminated_upstream:
            if not (self.tls_cert_path and self.tls_key_path):
                raise ValueError(
                    "In HTTP mode, either TLS must be terminated upstream "
                    "(TLS_TERMINATED_UPSTREAM=true, e.g. by an ingress/sidecar) "
                    "or TLS_CERT_PATH/TLS_KEY_PATH must be set so this process "
                    "terminates TLS itself. Plaintext HTTP is never permitted."
                )
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide immutable Settings singleton."""
    return Settings()  # type: ignore[call-arg]
