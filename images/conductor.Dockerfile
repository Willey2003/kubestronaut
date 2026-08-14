FROM python:3.12-slim
LABEL org.opencontainers.image.title="Golden Astronaut 2026 - conductor"
LABEL org.opencontainers.image.source="https://github.com/<owner>/kubestronaut"

ARG KUBECTL_VERSION=v1.31.0
ARG OC_VERSION=stable-4.17

RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates openssh-client && \
    curl -fsSLO "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/amd64/kubectl" && \
    install -m 0755 kubectl /usr/local/bin/kubectl && rm -f kubectl && \
    curl -fsSLO "https://mirror.openshift.com/pub/openshift-v4/clients/ocp/${OC_VERSION}/openshift-client-linux.tar.gz" && \
    tar -xzf openshift-client-linux.tar.gz oc && \
    install -m 0755 oc /usr/local/bin/oc && rm -f openshift-client-linux.tar.gz oc && \
    pip install --no-cache-dir pyyaml && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY engine/ /app/engine/
COPY banks/ /app/banks/

ENV GA_BANKS=/app/banks \
    GA_STATE=/app/state \
    GA_CLUSTER=local \
    GA_CONDUCTOR_PORT=9001

VOLUME ["/app/state"]
# Mount the host kubeconfig here to reach the OpenShift cluster, e.g.
#   -v ${HOME}/.kube:/root/.kube:ro
EXPOSE 9001

HEALTHCHECK --interval=15s --timeout=5s --retries=10 \
  CMD python3 -c "import urllib.request,sys; urllib.request.urlopen('http://127.0.0.1:9001/healthz'); sys.exit(0)" || exit 1

ENTRYPOINT ["python3", "-m", "engine.conductor", "--serve"]
