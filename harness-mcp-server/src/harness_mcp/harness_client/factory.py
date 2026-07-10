"""Process-wide singletons for the shared HTTP client and per-module clients.
Tool modules import from here rather than constructing clients themselves."""

from __future__ import annotations

from functools import lru_cache

from harness_mcp.harness_client.audit import HarnessAuditClient
from harness_mcp.harness_client.base import HarnessHTTPClient
from harness_mcp.harness_client.ccm import CcmClient
from harness_mcp.harness_client.chaos import ChaosClient
from harness_mcp.harness_client.context import ContextClient
from harness_mcp.harness_client.deployments import DeploymentClient
from harness_mcp.harness_client.feature_flags import FeatureFlagClient
from harness_mcp.harness_client.pipeline import PipelineClient
from harness_mcp.harness_client.sto import StoClient
from harness_mcp.settings import get_settings


@lru_cache(maxsize=1)
def get_http_client() -> HarnessHTTPClient:
    return HarnessHTTPClient(get_settings())


@lru_cache(maxsize=1)
def get_pipeline_client() -> PipelineClient:
    return PipelineClient(get_http_client())


@lru_cache(maxsize=1)
def get_deployment_client() -> DeploymentClient:
    return DeploymentClient(get_http_client())


@lru_cache(maxsize=1)
def get_feature_flag_client() -> FeatureFlagClient:
    return FeatureFlagClient(get_http_client())


@lru_cache(maxsize=1)
def get_sto_client() -> StoClient:
    return StoClient(get_http_client())


@lru_cache(maxsize=1)
def get_ccm_client() -> CcmClient:
    return CcmClient(get_http_client())


@lru_cache(maxsize=1)
def get_chaos_client() -> ChaosClient:
    return ChaosClient(get_http_client())


@lru_cache(maxsize=1)
def get_audit_client() -> HarnessAuditClient:
    return HarnessAuditClient(get_http_client())


@lru_cache(maxsize=1)
def get_context_client() -> ContextClient:
    return ContextClient(get_http_client())
