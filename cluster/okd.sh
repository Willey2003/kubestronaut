#!/usr/bin/env bash
# Golden Astronaut 2026 - provision an OKD (community OpenShift) cluster.
# OKD is the upstream community distribution of OpenShift. This script
# provides the two supported lightweight routes:
#
#   A) colocated single-node (a helper node running the cluster with
#      openshift-install single-node ignition), or
#   B) assisted-installer style install on a VM you control.
#
# This script is a guarded checklist + helpers, NOT a full installer: a real
# OKD install needs networking/DNS decisions that differ per lab. Read
# docs/cluster-setup.md before running.
set -euo pipefail

OCP_VER="4.17"
MIRROR="https://mirror.openshift.com/pub/openshift-v4/clients/ocp"

fetch() { # fetch <file>
  local f="$1"
  [ -f "cluster/.cache/$f" ] || { mkdir -p cluster/.cache; curl -fsSLO "$MIRROR/$OCP_VER/$f" -o "cluster/.cache/$f"; }
  echo "cluster/.cache/$f"
}

case "${1:-}" in
  fetch-tools)
    echo "Fetching openshift-install + oc for OKD $OCP_VER ..."
    INSTALL_TGZ="openshift-install-linux.tar.gz"
    curl -fsSL "$MIRROR/stable-4.17/$INSTALL_TGZ" -o /tmp/openshift-install.tgz && tar -xzf /tmp/openshift-install.tgz -C /usr/local/bin openshift-install
    curl -fsSL "$MIRROR/stable-4.17/openshift-client-linux.tar.gz" -o /tmp/oc.tgz && tar -xzf /tmp/oc.tgz -C /usr/local/bin oc kubectl
    openshift-install version
    oc version --client
    ;;
  install-config)
    echo "Generating an install-config.yaml template. EDIT it (pullSecret, sshKey, node details) first."
    mkdir -p cluster/okd-install
    cat > cluster/okd-install/install-config.yaml <<'EOF'
apiVersion: v1
baseDomain: example.com          # <-- CHANGE
metadata:
  name: lab
compute:
- architecture: amd64
  hyperthreading: Enabled
  name: worker
  replicas: 0
controlPlane:
  architecture: amd64
  hyperthreading: Enabled
  name: master
  replicas: 1
networking:
  networkType: OVNKubernetes
  clusterNetwork:
  - cidr: 10.128.0.0/14
    hostPrefix: 23
  serviceNetwork:
  - 172.30.0.0/16
platform:
  none: {}
pullSecret: '{"auths":{"fake":{}}}'   # <-- CHANGE
sshKey: 'ssh-rsa AAAA...'             # <-- CHANGE
EOF
    echo "Wrote cluster/okd-install/install-config.yaml"
    echo "Next: edit it, then: openshift-install create cluster --dir cluster/okd-install"
    ;;
  *)
    cat <<'EOF'
OKD provisioning helpers:

  ./cluster/okd.sh fetch-tools      # download openshift-install + oc (root install)
  ./cluster/okd.sh install-config   # write an install-config.yaml template to edit

A full single-node OKD install is a multi-step, network-sensitive process.
Read docs/cluster-setup.md for the recommended order, and run it on a host
whose network you can shape (DNS for api.lab.example.com, apps.lab.example.com).
EOF
    exit 0
    ;;
esac
