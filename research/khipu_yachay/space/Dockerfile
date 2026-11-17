FROM python:3.12.16-slim@sha256:5e2bdb1b0d542d5039cffb8181c65930093949194a65c365dfb1b0fe13a4fa5b
# Multi-arch index digest for docker.io/library/python:3.12.16-slim, read from
# registry-1.docker.io on 2026-11-17. A digest pin is necessary for release
# admission, not sufficient: the Space still needs owner approval and readback.
# app.py defaults HOST to loopback for local runs; the Space router needs the
# container interface, so the image binds 0.0.0.0.
ENV HOST=0.0.0.0 PORT=7860 PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY . /app
RUN useradd -m -u 1000 user && chown -R user:user /app
USER user
EXPOSE 7860
CMD ["python", "space/app.py"]
