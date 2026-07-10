"""AWS Secrets Manager adapter. Relies on IRSA / instance role -- no static keys."""

from __future__ import annotations

import json

import boto3
from botocore.exceptions import ClientError

from harness_mcp.settings import Settings


class AwsSecretsManagerProvider:
    def __init__(self, settings: Settings) -> None:
        if not settings.aws_secrets_manager_region:
            raise ValueError(
                "AWS_SECRETS_MANAGER_REGION is required for the AWS Secrets Manager backend"
            )
        self._settings = settings
        self._client = boto3.client(
            "secretsmanager", region_name=settings.aws_secrets_manager_region
        )

    def _full_id(self, key: str) -> str:
        return f"{self._settings.aws_secrets_manager_prefix}{key}"

    def _read(self, key: str) -> str:
        try:
            resp = self._client.get_secret_value(SecretId=self._full_id(key))
        except ClientError as exc:  # pragma: no cover - network dependent
            raise KeyError(f"AWS Secrets Manager secret '{key}' not found: {exc}") from exc
        return resp.get("SecretString", "")

    def get_secret(self, key: str) -> str:
        raw = self._read(key)
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return raw
        if isinstance(parsed, dict) and "value" in parsed:
            return str(parsed["value"])
        return raw

    def get_secret_json(self, key: str) -> dict:
        return json.loads(self._read(key))
