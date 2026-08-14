#!/usr/bin/env bash
# Golden Astronaut 2026 - cluster preflight.
# Checks whether this host can run an OpenShift cluster (CRC/OpenShift Local or OKD).
set -euo pipefail

pass=0; fail=0
check() { if eval "$2"; then echo "  [ok] $1"; pass=$((pass+1)); else echo "  [!!] $1  ($3)"; fail=$((fail+1)); fi; }

echo "Golden Astronaut 2026 - cluster preflight"

check "CPU count >= 4"          '[ "$(nproc)" -ge 4 ]' "have $(nproc)"
check "RAM >= 8 GB"             '[ "$(awk '/MemTotal/{print int($2/1024/1024)}' /proc/meminfo)" -ge 8 ]' \
                                "have $(awk '/MemTotal/{print int($2/1024/1024)}' /proc/meminfo) GB"
check "Disk free >= 30 GB"      '[ "$(df -BG --output=avail / 2>/dev/null | tail -1 | tr -dc 0-9)" -ge 30 ]' "low disk"
check "oc client installed"     'command -v oc' "install oc (mirror.openshift.com/pub/openshift-v4/clients/ocp/stable/)"
check "crc installed (CRC path)" 'command -v crc' "optional: https://developers.redhat.com/products/openshift-local"

if command -v systemd-detect-virt >/dev/null 2>&1; then
  check "nested virtualization available" \
    '[ "$(systemd-detect-virt -v 2>/dev/null | tr A-Z a-z)" != "none" ] || grep -qE "vmx|svm" /proc/cpuinfo' \
    "CRC needs KVM; OKD may work under other hypervisors"
else
  check "vmx/svm flag in cpuinfo" 'grep -qE "vmx|svm" /proc/cpuinfo' "no hardware virt flags"
fi

check "docker available (optional, platform)" 'command -v docker' "only needed to run the simulator UI"

echo
echo "pass=$pass fail=$fail"
if [ "$fail" -gt 0 ]; then
  echo "Review the failed items. CRC/OpenShift Local is the easiest route; see docs/cluster-setup.md"
  exit 1
fi
echo "Host looks ready for an OpenShift cluster."
