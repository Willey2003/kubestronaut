FROM python:3.12-slim
LABEL org.opencontainers.image.title="Kubestronaut 2026 - facilitator"
LABEL org.opencontainers.image.source="https://github.com/<owner>/kubestronaut"

RUN pip install --no-cache-dir pyyaml && \
    apt-get update && apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY engine/ /app/engine/
COPY banks/ /app/banks/
COPY curriculum/ /app/curriculum/
COPY ga /app/ga

ENV GA_BANKS=/app/banks \
    GA_STATE=/app/state \
    GA_CONDUCTOR=http://conductor:9001 \
    GA_ADDR=0.0.0.0 \
    GA_PORT=8900

VOLUME ["/app/state"]
EXPOSE 8900

HEALTHCHECK --interval=15s --timeout=5s --retries=10 \
  CMD curl -fsS http://127.0.0.1:8900/api/healthz || exit 1

ENTRYPOINT ["python3", "-m", "engine.facilitator"]
