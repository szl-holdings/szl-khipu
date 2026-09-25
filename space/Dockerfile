# syntax=docker/dockerfile:1
# SZL KHIPU hologram — stdlib HTTP, numpy kernels, no Gradio. No npm ci.
# GCR pin — ECR Public and Docker Hub python: are factory exit 128.
# Flatten payload at Hub root: Dockerfile + server.py + index.html + README + szl_khipu/.
# Doctrine v11: exact revision, not a floating tag. python:3.12-slim manifest
# list digest observed on Docker Hub 2026-09-25 (image last pushed 2026-09-19);
# mirror.gcr.io serves the same content-addressed manifest.
FROM mirror.gcr.io/library/python:3.12-slim@sha256:2f17fc044b579bab302c2e8054d3a686e2cb9a83de48e70534b94cd8ebbe06a9
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=7860
# numpy pinned to the same release the a11oy runtime image installs (estate parity).
RUN pip install --no-cache-dir "numpy==2.5.2"
# Non-root runtime user (uid 1000, the Hugging Face Spaces convention). The
# server binds an unprivileged port and performs no disk writes.
RUN useradd --create-home --uid 1000 --shell /usr/sbin/nologin appuser
COPY --chown=appuser:appuser server.py ./server.py
COPY --chown=appuser:appuser index.html ./index.html
COPY --chown=appuser:appuser energy.py ./energy.py
COPY --chown=appuser:appuser szl-holo-v2.css ./szl-holo-v2.css
COPY --chown=appuser:appuser szl-holo-v2.js ./szl-holo-v2.js
COPY --chown=appuser:appuser szl_khipu ./szl_khipu
COPY --chown=appuser:appuser artifacts ./artifacts
USER appuser
EXPOSE 7860
# Liveness against the existing /healthz route; kernel/energy truth stays on
# its own honest routes (LIVE / UNAVAILABLE), never inferred from liveness.
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD ["python", "-c", "import sys, urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:7860/healthz', timeout=4).status == 200 else 1)"]
CMD ["python", "-u", "server.py"]
