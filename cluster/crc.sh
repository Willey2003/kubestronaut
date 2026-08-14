#!/usr/bin/env bash
# Golden Astronaut 2026 - provision Red Hat OpenShift Local (formerly CRC).
# The easiest way to get a real, single-node OpenShift cluster for practice.
#
# Usage:  ./cluster/crc.sh [setup|start|login|status]
#   setup - install crc + pull the bundle (interactive, needs a pull secret)
#   start - start the cluster
#   login - print the oc login command + kubeadmin password
#   status- cluster health summary
set -euo pipefail

CRC_BIN="$(command -v crc || true)"
[ -n "$CRC_BIN" ] || { echo "crc not found. Install it, then run '$0 setup'."; exit 1; }

case "${1:-status}" in
  setup)
    crc setup
    echo "Enter your Red Hat pull secret (paste and press Enter):"
    read -r SECRET
    printf '%s' "$SECRET" | crc start -p /dev/stdin
    ;;
  start)
    crc start
    ;;
  login)
    CONSOLE_URL=$(crc console-url)
    PASS=$(crc console --credentials | awk '/kubeadmin/{print $NF}')
    echo "Console: $CONSOLE_URL"
    echo "login  : oc login -u kubeadmin -p $PASS https://api.crc.testing:6443"
    echo "kubeconfig: $HOME/.crc/machines/crc/kubeconfig"
    ;;
  status)
    crc status
    echo "---"
    oc cluster-info 2>&1 || echo "not logged in - run '$0 login' first"
    ;;
  *) echo "usage: $0 [setup|start|login|status]"; exit 2 ;;
esac
