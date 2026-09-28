# syntax=docker/dockerfile:1.7
# Build context: repository root. Scanners are pinned with checksums (docs/scanner-tools.md).

FROM python:3.12-slim-trixie AS build
COPY --from=ghcr.io/astral-sh/uv:0.12 /uv /bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY packages packages
COPY apps/api apps/api
COPY apps/worker apps/worker
RUN uv sync --frozen --no-dev --no-editable --package luibui-worker

FROM python:3.12-slim-trixie AS scanners
ADD --checksum=sha256:551f6fc83ea457d62a0d98237cbad105af8d557003051f41f3e7ca7b3f2470eb \
    https://github.com/gitleaks/gitleaks/releases/download/v8.30.1/gitleaks_8.30.1_linux_x64.tar.gz \
    /tmp/gitleaks.tgz
RUN tar -xzf /tmp/gitleaks.tgz -C /usr/local/bin gitleaks
ADD --checksum=sha256:ca69b3d3cd08f889a49dc0a383122f71cc528b83803671df5fd874d97485b108 --chmod=755 \
    https://github.com/google/osv-scanner/releases/download/v2.6.0/osv-scanner_linux_amd64 \
    /usr/local/bin/osv-scanner
# Opengrep (LGPL-2.1, own rules only). The binary unpacks itself on first start; do that once
# here into a read-only cache instead of 240 MB per job.
ADD --checksum=sha256:35779bdd72e92129c8df2a77f0c55e8c08356801ea92591ef32108d6b28d564c --chmod=755 \
    https://github.com/opengrep/opengrep/releases/download/v1.30.0/opengrep_manylinux_x86 \
    /usr/local/bin/opengrep
RUN HOME=/tmp XDG_CACHE_HOME=/opt/opengrep-cache /usr/local/bin/opengrep --version \
 && chmod -R a+rX,a-w /opt/opengrep-cache

FROM python:3.12-slim-trixie
COPY --from=scanners /usr/local/bin/gitleaks /usr/local/bin/osv-scanner /usr/local/bin/opengrep /usr/local/bin/
COPY --from=scanners /opt/opengrep-cache /opt/opengrep-cache
RUN useradd --system --uid 10001 --no-create-home --home-dir /nonexistent luibui \
 && mkdir -p /scratch /rules/osv && chown 10001:10001 /scratch /rules /rules/osv \
 && chmod 700 /scratch
COPY --from=build /app/.venv /app/.venv
COPY rules /app/rules
ENV PATH=/app/.venv/bin:$PATH PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    SCRATCH_ROOT=/scratch LITELLM_LOCAL_MODEL_COST_MAP=True \
    LUIBUI_RULES_DIR=/app/rules LUIBUI_GITLEAKS=/usr/local/bin/gitleaks \
    LUIBUI_OSV_SCANNER=/usr/local/bin/osv-scanner LUIBUI_OSV_DB=/rules/osv \
    LUIBUI_MALWARE_DB=/rules/malware/sha256.bin \
    LUIBUI_OPENGREP=/usr/local/bin/opengrep LUIBUI_OPENGREP_CACHE=/opt/opengrep-cache \
    LUIBUI_NETZ_ISOLIEREN=1
USER 10001
WORKDIR /scratch
ENTRYPOINT ["luibui-worker"]
