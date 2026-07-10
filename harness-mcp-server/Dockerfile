# syntax=docker/dockerfile:1

# ---- builder ---------------------------------------------------------------
FROM python:3.12-slim AS builder

WORKDIR /build
RUN pip install --no-cache-dir --upgrade pip hatchling

COPY pyproject.toml README.md ./
COPY src ./src

RUN pip install --no-cache-dir --prefix=/install .

# ---- runtime ----------------------------------------------------------------
FROM python:3.12-slim AS runtime

# Dedicated non-root UID/GID -- never runs as root, never uses an existing
# broadly-shared UID.
RUN groupadd --gid 10001 harness-mcp \
    && useradd --uid 10001 --gid harness-mcp --no-create-home --shell /usr/sbin/nologin harness-mcp

COPY --from=builder /install /usr/local

# Writable paths the app needs even under a read-only root filesystem: the
# local append-only audit log directory. Everything else is read-only.
RUN mkdir -p /var/log/harness-mcp && chown -R harness-mcp:harness-mcp /var/log/harness-mcp

USER harness-mcp:harness-mcp
WORKDIR /home/harness-mcp

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    MCP_MODE=http \
    HTTP_HOST=0.0.0.0 \
    HTTP_PORT=8443

EXPOSE 8443

# Liveness is process-only (see observability/healthcheck.py) so this probe
# never fails due to a transient Harness/Vault outage.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8443/healthz', timeout=3).status==200 else 1)"

ENTRYPOINT ["python", "-m", "harness_mcp"]
