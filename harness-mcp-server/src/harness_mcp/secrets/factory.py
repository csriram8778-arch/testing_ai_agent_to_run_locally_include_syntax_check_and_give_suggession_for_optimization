"""Single seam that picks a SecretsProvider implementation via SECRETS_BACKEND."""

from __future__ import annotations

from functools import lru_cache

from harness_mcp.secrets.provider import SecretsProvider
from harness_mcp.settings import Settings, get_settings


@lru_cache(maxsize=1)
def get_secrets_provider() -> SecretsProvider:
    settings = get_settings()
    return build_secrets_provider(settings)


def build_secrets_provider(settings: Settings) -> SecretsProvider:
    if settings.secrets_backend == "vault":
        from harness_mcp.secrets.vault_provider import VaultSecretsProvider

        return VaultSecretsProvider(settings)
    if settings.secrets_backend == "aws-secrets-manager":
        from harness_mcp.secrets.aws_provider import AwsSecretsManagerProvider

        return AwsSecretsManagerProvider(settings)
    raise ValueError(f"Unsupported SECRETS_BACKEND: {settings.secrets_backend}")  # pragma: no cover
