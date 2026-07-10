# Harness MCP Server

A self-hosted [MCP](https://modelcontextprotocol.io) server that lets Claude (Claude Code, Claude Desktop, and the
Claude API) operate a team's day-to-day Harness workflow — CI/CD pipelines, deployments, security scans, feature
flags, cloud cost, chaos engineering, and audit logs — entirely inside the team's private network, under strict
human-approval and audit guardrails.

This is a new, standalone service. It does not share code or configuration with anything else in this repository.

> **Looking for step-by-step setup and usage instructions?** See [`docs/USAGE_GUIDE.md`](docs/USAGE_GUIDE.md) —
> admin deployment steps, team member onboarding, and day-to-day examples for every prompt. This README covers
> architecture and the security model.

---

## 1. Architecture

```
Claude (Code/Desktop/API)
        │  HTTPS + x-harness-api-key: <your own scoped Harness token>
        ▼
┌───────────────────────────────────────────────────────────────────────────┐
│  harness-mcp-server  (Docker/Kubernetes, private VPC, non-root, read-only) │
│                                                                             │
│  auth.middleware  ──▶  tools.registry (the ONLY way a tool gets called)   │
│                          │                                                 │
│                          ├─▶ guardrails.approval_hook  (risk tier +       │
│                          │      HARNESS_AUTO_APPROVE_RISK=none +          │
│                          │      confirm/elicitation state machine)        │
│                          ├─▶ harness_client.*  (per-call caller token,    │
│                          │      deny_list second check, TLS-only)         │
│                          ├─▶ redaction.sanitizer  (allowlist + regex)     │
│                          └─▶ audit_logging  (structured JSON, fan-out to  │
│                                 local file + S3 Object Lock + webhook)    │
└───────────────────────────────────────────────────────────────────────────┘
        │  HTTPS + x-api-key: <caller's own token>
        ▼
                              Harness platform
```

Every property below is **structural** — enforced by code that runs on every call — not a convention a tool author
has to remember.

- **`tools/registry.py`** is the single choke point. A tool is only callable if it went through
  `register_tool(...)`, which composes, in fixed order: resolve identity → risk classification → approval →
  Harness call → redaction → audit (in a `finally`, so denials and exceptions are audited too).
- **Prompts never call Harness directly.** The seven named prompts (`prompts/*.py`) only describe which
  registry-wrapped tools to call — a prompt's text (or a hostile instruction embedded in tool output) cannot bypass
  approval or audit, because the enforcement lives one layer below, in code the prompt has no way to reach around.
- **`HARNESS_AUTO_APPROVE_RISK=none`** is validated at process startup (`settings.py`) — any other value fails to
  boot. `guardrails/approval_hook.py` takes no override parameter of any kind.

## 2. Multi-user HTTP mode & per-user identity

Team use is **HTTP mode** (`MCP_MODE=http`): the server holds **zero Harness credentials**. Every request carries
its own scoped token via the `x-harness-api-key` header. `auth/middleware.py` is Starlette middleware wrapped
around FastMCP's Streamable HTTP app — it runs before any MCP method (including `initialize`), validates the token
against Harness's own identity endpoint, and sets a `contextvars.ContextVar` (`session_context.py`) that every tool
handler reads via `get_current_session()`. A request with a missing or invalid/expired token gets `401` before
anything else runs — there is no unauthenticated fallback path in this codebase.

This also means: **each team member authenticates with their own Harness identity**, never a shared credential.
Point Claude at the server with *your own* scoped Harness Service Account Token (or personal token), per the config
snippets in `config/`.

`MCP_MODE=stdio` exists for local single-developer use only (one token, read from the configured secrets backend
or an env var) — never use it for shared/team access.

## 3. Approval model — no unattended writes

Every tool is classified `READ_ONLY`, `WRITE`, or `DESTRUCTIVE_EXCLUDED` in `guardrails/risk.py`. Classification is
enforced at import/startup time: an unclassified tool cannot be registered, and `DESTRUCTIVE_EXCLUDED` tools are
never implemented at all (see §5).

`WRITE`-tier tools require explicit human confirmation via a two-step **propose → confirm** pattern, which is the
portable default because MCP client support for the newer `elicitation/create` capability varies:

1. First call: the tool runs `approval_hook.evaluate(...)`, which returns `{"status": "pending_confirmation",
   "confirmation_token": "..."}` **without touching Harness**. Claude must show the user exactly what will happen
   and get explicit agreement in that conversation turn.
2. Second call: the same tool, same parameters, plus `confirmation_token=<token>`. The token is single-use,
   short-lived (`CONFIRMATION_TTL_SECONDS`, default 300s), and bound to the exact user + tool + parameters — a
   changed parameter, a different user, an expired or reused token, all fail closed.

If the connected MCP client supports elicitation, `guardrails/elicitation.py` opportunistically uses it for a nicer
UX on top of the same state machine — but the two-step pattern above is what every client can rely on.

`CONFIRMATION_STORE_BACKEND=memory` (default) is correct for stdio mode or a single HTTP replica. **A multi-replica
HTTP deployment must set `CONFIRMATION_STORE_BACKEND=redis`**, or a confirmation proposed on one pod can't be
consumed on another.

## 4. Audit logging

Every tool call — allowed, denied, pending, or errored — produces a structured JSON `AuditEvent`
(`audit_logging/event.py`) with timestamp, resolved user identity, tool name, (redacted) input parameters, outcome,
a request id, and best-effort `reasoning_context` if the calling client sent one (this is **not** a standardized
MCP field yet — treat it as best-effort, not a guarantee that Claude's reasoning is always captured).

Events fan out concurrently to every configured sink (`audit_logging/sinks/`):

- **Local append-only JSONL** — always active, a crash-safety net.
- **S3 with Object Lock** (`AUDIT_S3_BUCKET`/`AUDIT_S3_REGION`) — the durable, immutable record. The bucket must be
  created with Object Lock enabled and a default retention policy; this server never shortens or removes it.
- **Generic SIEM/webhook** (`AUDIT_WEBHOOK_URL` + HMAC-signed via a secret pulled from the secrets backend).

`AUDIT_FAIL_CLOSED=true` (default): if every sink fails to write, the tool call fails rather than returning success
silently unaudited. **Known limitation:** because the Harness call happens before the completion audit event is
written, fail-closed can only fail the *response back to the caller* for a `WRITE`-tier tool whose Harness call
already succeeded — it cannot undo that action. `tools/registry.py` also emits a best-effort **pre-flight** audit
event before contacting Harness for `WRITE`-tier tools, so a trail showing intent survives even if the final write
fails.

No prompt text, tool parameter, or client instruction can suppress an event: the emit call lives in
`tools/registry.py`'s `finally` block, which every registered tool passes through unconditionally.

## 5. What Claude can and cannot do

**Never, structurally — not a policy, a code fact:**

- Read a secret value or environment-variable value stored in Harness.
- Delete a pipeline, service, environment, or project.
- Modify RBAC roles, user-group membership, or create/revoke API tokens.
- See a raw, unredacted Harness API response — every response goes through `redaction/sanitizer.py`
  (allowlist projection + regex scrubbing of IPs, hostnames, ARNs, emails, and token-shaped strings) before
  it can reach the client.
- Perform a write/deploy/destructive action without a human explicitly confirming it in that conversation turn.
- Call any tool at all without a valid, non-expired session token.

These are enforced independently in two places: the tool simply doesn't exist for excluded operations
(`guardrails/risk.py`'s `DESTRUCTIVE_EXCLUDED_INTENT` + nothing implementing it), **and** `harness_client/base.py`
checks every outbound HTTP call against `guardrails/deny_list.py` before sending it — defense in depth, not a
single point of failure.

**Always requires a human "yes" in-conversation, one WRITE tool at a time:**

`trigger_pipeline`, `abort_execution`, `promote_artifact`, `initiate_rollback`, `triage_vulnerability`,
`update_flag_state`, `run_chaos_experiment`.

**Always available, read-only, no confirmation:**

`list_pipelines`, `get_pipeline`, `get_pipeline_yaml`, `list_executions`, `get_execution`, `get_execution_logs`,
`get_environment_state`, `list_scan_results`, `get_vulnerability`, `check_critical_block`, `list_flags`,
`get_flag`, `evaluate_flag`, `get_cost_summary`, `list_cost_anomalies`, `get_cost_recommendations`,
`list_chaos_experiments`, `get_chaos_experiment`, `query_audit_trail`, `get_repo_info`.

Code generation, review, and documentation are performed by Claude itself, grounded in real pipeline/repo state
fetched via the read-only tools above (`get_pipeline_yaml`, `get_repo_info`, etc.) — this server does not call out
to a separate LLM.

## 6. Named prompts

`/deploy`, `/rollback`, `/triage`, `/review-pr`, `/document`, `/cost-check`, `/chaos-run` — each templates the
team's standard workflow and, for the four that touch state (`/deploy`, `/rollback`, `/triage`, `/chaos-run`),
explicitly instructs Claude to summarize impact and get explicit approval before the confirming tool call. This is
a UX aid; the actual enforcement is in §3, independent of what the prompt text says.

## 7. Onboarding

1. **Platform admin, once:** deploy the server (see §8) into the private VPC, wire the secrets backend (Vault or
   AWS Secrets Manager — see `.env.example`), create the S3 Object Lock bucket and/or SIEM webhook for audit, and
   issue each team member a scoped Harness Service Account Token (minimum required scopes — never a shared/personal
   admin token).
2. **Each team member:** merge the `harness` entry from `config/claude_code_mcp_config.example.json` (Claude Code)
   or `config/claude_desktop_config.example.json` (Claude Desktop) into your own config, pointing `url` at the
   team's internal HTTPS endpoint and `x-harness-api-key` at **your own** token.
3. Try a read-only tool first (e.g. ask Claude to list pipelines) to confirm connectivity, then try a `/deploy` or
   similar WRITE-tier workflow to see the confirmation step in action.

Local single-developer stdio mode (no team infra needed) is documented inline in the stdio example in
`config/claude_code_mcp_config.example.json` — set your own token in `HARNESS_SAT_TOKEN`, never commit it.

## 8. Running it

```bash
# Local dev, HTTP mode, against a dev Vault container:
cp .env.example .env   # then edit — never commit .env
docker compose -f docker-compose.dev.yml up --build

# Production: build and push the image, then apply the Kubernetes manifests
docker build -t <your-registry>/harness-mcp-server:<tag> .
kubectl apply -f deploy/k8s/namespace.yaml
kubectl apply -f deploy/k8s/serviceaccount.yaml
kubectl apply -f deploy/k8s/configmap.yaml
# Secrets: sync deploy/k8s/secret.example.yaml's keys from Vault/AWS Secrets
# Manager via your secrets operator -- do not hand-apply real values.
kubectl apply -f deploy/k8s/deployment.yaml
kubectl apply -f deploy/k8s/service.yaml
kubectl apply -f deploy/k8s/networkpolicy.yaml   # edit the egress CIDRs/FQDNs first, see inline comments
kubectl apply -f deploy/k8s/poddisruptionbudget.yaml
kubectl apply -f deploy/k8s/hpa.yaml
```

Tests:

```bash
pip install -e ".[dev,redis]"
pytest
```

## 9. Known limitations — read before production use

- **Harness NG API paths are best-effort.** `harness_client/*.py` is built from well-known, public Harness NextGen
  API conventions (module prefixes `pipeline`, `ng`, `cf`, `sto`, `ccm`, `chaos`, `audit`; the `{status, data,
  metaData, correlationId}` response envelope). Exact paths drift across releases and differ SaaS vs Self-Managed
  Enterprise Edition. Verify every endpoint in `harness_client/*.py` against your account's live OpenAPI docs
  before production use — `harness_client/endpoints.py` is the single seam to adjust them. STO's API version
  (v1 vs v2) and Chaos's REST-vs-GraphQL surface are the most likely to have shifted.
- **Redaction allowlists are a starting point.** `redaction/allowlists.py`'s per-tool field lists are conservative
  and built from common Harness NG field names, not a live schema fetch. An incomplete allowlist fails safe (too
  little data returned, never leaked data) — but you should still tune it against your account's real responses.
- **Elicitation support varies by MCP client.** The two-step propose/confirm pattern (§3) is the guaranteed path;
  treat elicitation as a UX bonus, not something to depend on.
- **`AUDIT_FAIL_CLOSED` cannot undo a completed Harness write** if every audit sink is down when the completion
  event is written — see §4's pre-flight-event mitigation and its limits.
- **Kubernetes `NetworkPolicy` cannot match FQDNs.** `deploy/k8s/networkpolicy.yaml`'s egress rule is a placeholder
  `0.0.0.0/0` on port 443 with an inline comment explaining why — you need either a CNI with FQDN-based policies
  (e.g. Cilium `toFQDNs`) or an egress proxy to actually scope egress to the Harness/Vault/S3/SIEM hosts by name.
- **Multi-replica HTTP mode needs Redis** for the confirmation store (§3) — the in-memory default only works
  single-replica or stdio.
- **This was designed and code-reviewed by an AI pairing session, not yet security-audited or run against a live
  Harness account.** Treat it as a strong starting point for your team's own review, threat-modeling, and staging
  rollout — not a drop-in production artifact.
