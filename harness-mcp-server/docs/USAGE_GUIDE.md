# Harness MCP Server — Step-by-Step Usage Guide

This is the "how do I actually use this" companion to [`README.md`](../README.md), which covers architecture and
the security model. This guide is split into three parts:

- **Part A — Platform Admin Setup** (one-time, done by whoever runs the team's infrastructure)
- **Part B — Team Member Onboarding** (done once per person who wants to use Claude with Harness)
- **Part C — Day-to-Day Usage** (what it actually looks like to use this from Claude)
- **Part D — Troubleshooting**

---

## Part A — Platform Admin Setup (one-time)

### A1. Prerequisites checklist

- [ ] A Kubernetes cluster inside your private VPC (or Docker host, for a smaller/dev setup)
- [ ] A container registry the cluster can pull from
- [ ] A Harness account, with permission to create Service Account Tokens (SATs)
- [ ] One of: a reachable HashiCorp Vault instance, **or** an AWS account for Secrets Manager
- [ ] (Recommended) An S3 bucket you can enable Object Lock on, for the immutable audit trail
- [ ] (If deploying multiple replicas) A reachable Redis instance
- [ ] (Optional) A SIEM/webhook endpoint that accepts signed JSON POSTs

### A2. Get the code building

```bash
cd harness-mcp-server
docker build -t <your-registry>/harness-mcp-server:0.1.0 .
docker push <your-registry>/harness-mcp-server:0.1.0
```

### A3. Configure the secrets backend

Pick one (see `.env.example` and `secrets/vault_provider.py` / `secrets/aws_provider.py`):

**Vault:**
1. Enable a KV v2 mount (default expected path prefix: `secret/harness-mcp-server`).
2. Enable Kubernetes auth (`vault auth enable kubernetes`) and create a role bound to the
   `harness-mcp-server` ServiceAccount/namespace (matches `deploy/k8s/serviceaccount.yaml`).
3. Store the server's own operational secrets under that KV path — e.g.
   `secret/harness-mcp-server/audit-webhook-signing-secret` with a `value` field, if you're using the webhook sink.
4. Set `SECRETS_BACKEND=vault`, `VAULT_ADDR`, `VAULT_AUTH_METHOD=kubernetes`, `VAULT_ROLE` (see
   `deploy/k8s/configmap.yaml` / `secret.example.yaml`).

**AWS Secrets Manager:**
1. Create secrets under a common prefix, e.g. `harness-mcp-server/audit-webhook-signing-secret`.
2. Attach an IAM role (via IRSA) to the `harness-mcp-server` ServiceAccount with `secretsmanager:GetSecretValue`
   scoped to that prefix only.
3. Set `SECRETS_BACKEND=aws-secrets-manager`, `AWS_SECRETS_MANAGER_REGION`, `AWS_SECRETS_MANAGER_PREFIX`.

### A4. Create one scoped Harness Service Account Token per team member

Do **not** create one shared token. For each person:

1. In Harness: **Account Settings → Access Control → Service Accounts** (or have each person use their own
   personal access token if your org prefers that over SATs — either way, it must be scoped to one person).
2. Grant the **minimum** roles needed for the toolsets your team actually uses — e.g. Pipeline Executor + Viewer,
   Environment Viewer, STO Viewer/Triage, Feature Flag Viewer/Editor, CCM Viewer, Chaos Viewer/Executor, Audit
   Viewer. Do **not** grant Account Admin, secret-read, or RBAC-management permissions — the server structurally
   blocks those calls anyway (see README §5), so granting them just widens blast radius if the token leaks.
3. Hand the token to that person directly (e.g. via your org's secrets-sharing tool) — never post it in Slack/email
   in plaintext, and never put it in a shared config file.

### A5. Configure audit destinations

1. **S3 Object Lock bucket** (recommended, for the immutable record):
   ```bash
   aws s3api create-bucket --bucket <org>-harness-mcp-audit-log --region us-east-1 \
     --object-lock-enabled-for-bucket
   aws s3api put-object-lock-configuration --bucket <org>-harness-mcp-audit-log \
     --object-lock-configuration '{"ObjectLockEnabled":"Enabled","Rule":{"DefaultRetention":{"Mode":"COMPLIANCE","Years":1}}}'
   ```
   Set `AUDIT_S3_BUCKET`, `AUDIT_S3_REGION` accordingly.
2. **SIEM/webhook** (optional, in addition to S3): set `AUDIT_WEBHOOK_URL` and store the HMAC signing secret in
   your secrets backend, referenced via `AUDIT_WEBHOOK_SIGNING_SECRET_REF` (a *key name*, not the secret itself).
3. Leave `AUDIT_FAIL_CLOSED=true` unless you have a specific reason not to (see README §4).

### A6. Deploy to Kubernetes

Apply in this order (dependencies matter — namespace/SA/config before the deployment that references them):

```bash
kubectl apply -f deploy/k8s/namespace.yaml
kubectl apply -f deploy/k8s/serviceaccount.yaml      # edit the IRSA role-arn annotation first
kubectl apply -f deploy/k8s/configmap.yaml
```

Now create the real Secret — **do not** hand-apply `secret.example.yaml`'s placeholder values. Use your secrets
operator (e.g. External Secrets Operator) to sync real values from Vault/AWS into a Secret named
`harness-mcp-server-secrets` in the `harness-mcp` namespace, matching the keys documented in
`deploy/k8s/secret.example.yaml`.

```bash
kubectl apply -f deploy/k8s/deployment.yaml          # edit the image reference first
kubectl apply -f deploy/k8s/service.yaml
kubectl apply -f deploy/k8s/networkpolicy.yaml       # edit the egress CIDRs/FQDNs first — see inline comments
kubectl apply -f deploy/k8s/poddisruptionbudget.yaml
kubectl apply -f deploy/k8s/hpa.yaml
```

### A7. Verify the deployment

```bash
kubectl -n harness-mcp get pods
kubectl -n harness-mcp logs deploy/harness-mcp-server --tail=50
kubectl -n harness-mcp port-forward svc/harness-mcp-server 8443:443
curl -k https://localhost:8443/healthz     # expect {"status": "alive"}
curl -k https://localhost:8443/readyz      # expect {"status": "ready", "checks": {...}}
```

Then confirm auth actually rejects unauthenticated calls:

```bash
curl -k -i https://localhost:8443/          # expect 401
curl -k -i https://localhost:8443/ -H "x-harness-api-key: <a-real-scoped-token>"   # expect a normal MCP response
```

### A8. Give each team member their onboarding info

Share with each person: the server's internal HTTPS URL, and point them at Part B below plus their own token from
A4. Never send the URL and a token together in the same shared/persistent message if you can avoid it.

---

## Part B — Team Member Onboarding

### B1. Get your own scoped Harness token

Ask your platform admin for your own Service Account Token (see A4). This is **yours** — do not share it with
teammates, and do not commit it anywhere.

### B2a. Configure Claude Code

Open (or create) `~/.claude.json` (or a project-level `.mcp.json`), and merge in the `harness` entry from
[`config/claude_code_mcp_config.example.json`](../config/claude_code_mcp_config.example.json):

```json
{
  "mcpServers": {
    "harness": {
      "type": "http",
      "url": "https://<your-team's-internal-url>/",
      "headers": {
        "x-harness-api-key": "<your-own-scoped-harness-token>"
      }
    }
  }
}
```

Restart Claude Code (or run `/mcp` to reconnect) and check that `harness` shows up as connected — in Claude Code,
run `/mcp` to see connected servers and their tool counts.

### B2b. Configure Claude Desktop

Open Claude Desktop → Settings → Developer → Edit Config, and merge the same `harness` entry from
[`config/claude_desktop_config.example.json`](../config/claude_desktop_config.example.json) into
`claude_desktop_config.json`. Restart Claude Desktop.

> If your installed Claude Desktop version doesn't yet support the `url` + `headers` remote-server form, use the
> local stdio example instead (single-user only, see the `harness-local-stdio` entry in the Claude Code config
> example) until you upgrade — that mode is fine for a solo developer trying things out, but is **not** how the
> team should connect (it uses one developer's token, not per-person identity).

### B3. Verify connectivity with a read-only ask

In a new conversation, ask Claude something like:

> "Using the harness tools, list the CI/CD pipelines in our project."

Claude should call `list_pipelines` and show you results. If instead you get an authentication error, see
Part D.

### B4. See the confirmation flow once, deliberately

Ask Claude to do something low-stakes but real, e.g. trigger a pipeline you're comfortable re-running:

> "Trigger pipeline `my-test-pipeline`."

Claude will call `trigger_pipeline`, get back `status: pending_confirmation`, and should explicitly ask you to
confirm before calling it again with the confirmation token. This is expected — it happens for **every**
WRITE-tier action, every time, regardless of what you asked for or how you phrased it.

---

## Part C — Day-to-Day Usage

Once connected, you can either just talk to Claude naturally (it will pick the right tools) or use the seven named
prompts as a shortcut for the team's standard workflows. Typing `/` in Claude Code or Desktop should surface them
once the server is connected.

### `/deploy` — promote an artifact

```
/deploy pipeline_id=deploy-web environment_id=staging service_id=web artifact_version=1.4.2
```
Claude checks current environment state and any blocking security findings, summarizes what will happen, asks you
to confirm, then calls `promote_artifact`.

### `/rollback` — roll a service back

```
/rollback environment_id=production service_id=web
```
Claude shows the current deployed version and recent history, confirms with you, then calls `initiate_rollback`.

### `/triage` — work through security findings

```
/triage pipeline_execution_id=abc123
```
Claude lists findings by severity, pulls detail on the ones you care about, proposes a triage status/comment, and
only calls `triage_vulnerability` after you agree to the specific status/comment.

### `/review-pr` — read-only code review

```
/review-pr connector_id=github-org repo_name=my-service pipeline_id=ci-my-service
```
Grounded in real repo/pipeline state; Claude does the actual review itself. No confirmation step — nothing here
can write.

### `/document` — generate pipeline documentation

```
/document pipeline_id=deploy-web
```
Read-only, grounded in the pipeline's real YAML.

### `/cost-check` — cloud cost and anomalies

```
/cost-check perspective_id=eng-prod start_time=2026-06-01 end_time=2026-07-01
```
Read-only — there are no write tools in the cost module at all.

### `/chaos-run` — run a chaos experiment

```
/chaos-run experiment_id=pod-kill-web
```
Claude explains blast radius and fault type *before* proposing to run it, gets your explicit go-ahead, then calls
`run_chaos_experiment` — this one has an explicit approval gate per the team's policy, on top of the standard
WRITE-tier confirmation.

### What a denied action looks like

If you (or Claude) attempt something structurally excluded — reading a secret value, deleting a pipeline,
modifying RBAC — the tool either doesn't exist (Claude will say so) or the call comes back `status: denied` with a
plain-language reason. This is not a bug to work around; it's the point.

---

## Part D — Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Every call returns 401 / "invalid or expired Harness token" | Token missing, wrong, expired, or revoked | Re-check the `x-harness-api-key` value in your config; ask your admin if the SAT is still valid |
| `status: pending_confirmation` then confirming fails | You waited past `CONFIRMATION_TTL_SECONDS` (default 300s), changed a parameter between calls, or reused an already-consumed token | Start the request over from scratch with identical parameters |
| Tool call fails with an audit-related error even though the Harness action seems to have happened | `AUDIT_FAIL_CLOSED=true` and every audit sink was unreachable | This is intentional (README §4) — the action may have gone through on the Harness side; check Harness directly, then get the audit sink issue fixed before retrying more writes |
| Confirmation from one call never works even seconds later, in a team HTTP deployment | Multiple replicas + `CONFIRMATION_STORE_BACKEND=memory` | Admin must set `CONFIRMATION_STORE_BACKEND=redis` with a real `REDIS_URL` for multi-replica deployments |
| `/readyz` reports `harness_reachable: false` | NetworkPolicy egress too narrow, or Harness base URL misconfigured | Check `HARNESS_BASE_URL` and the NetworkPolicy egress rules (README's NetworkPolicy/FQDN limitation note) |
| A tool response looks suspiciously empty/missing fields you expected | The redaction allowlist for that tool doesn't yet include a field your account's Harness response actually returns | Expected fail-safe behavior (README §9) — extend `redaction/allowlists.py` for that tool once you've confirmed the field is safe to expose |
| Claude Desktop doesn't show a `harness` entry as connected | Config not merged correctly, or Desktop version doesn't support remote MCP servers with headers yet | Re-check JSON syntax; fall back to the stdio example for solo local testing while you sort out Desktop version support |
