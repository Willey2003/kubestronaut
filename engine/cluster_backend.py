"""Cluster backends for hands-on grading.

`local`  - run `oc`/`kubectl` on this host (same machine as the cluster).
`remote` - run commands over SSH to a cluster host (oc lives there).
`none`   - no cluster: hands-on questions are ungraded (Training mode).

Plug in more backends (e.g. the OpenShift REST API) by subclassing Backend.
"""

from __future__ import annotations

import os
import shutil
import subprocess

TIMEOUT = float(os.getenv("GA_CMD_TIMEOUT", "30"))


class Backend:
    name = "none"

    def run(self, command: str) -> tuple[int, str]:
        raise NotImplementedError


class LocalBackend(Backend):
    name = "local"

    def run(self, command: str) -> tuple[int, str]:
        proc = subprocess.run(command, shell=True, capture_output=True,
                              text=True, timeout=TIMEOUT)
        return proc.returncode, (proc.stdout + proc.stderr).strip()


class RemoteBackend(Backend):
    name = "remote"

    def __init__(self, host: str, user: str = "root", key: str | None = None):
        self.host = host
        self.user = user
        self.key = key

    def run(self, command: str) -> tuple[int, str]:
        ssh = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10"]
        if self.key:
            ssh += ["-i", self.key]
        ssh += [f"{self.user}@{self.host}", command]
        proc = subprocess.run(ssh, capture_output=True, text=True, timeout=TIMEOUT + 10)
        return proc.returncode, (proc.stdout + proc.stderr).strip()


def make_backend(spec: str | None) -> Backend:
    """spec: "none" | "local" | "remote://user@host" | "remote://user@host:port"."""
    if not spec or spec == "none":
        return Backend()
    if spec == "local":
        return LocalBackend()
    if spec.startswith("remote://"):
        rest = spec[len("remote://"):]
        user_host, _, key = rest.partition("?key=")
        user, _, host = user_host.partition("@")
        host, _, port = host.partition(":")
        if port:
            key = None  # port not wired yet; documented limitation
        return RemoteBackend(host, user or "root", key)
    raise ValueError(f"unknown backend spec: {spec}")


def have_oc() -> bool:
    return shutil.which("oc") is not None


def have_kubectl() -> bool:
    return shutil.which("kubectl") is not None


if __name__ == "__main__":
    spec = os.getenv("GA_CLUSTER", "local")
    b = make_backend(spec)
    code, out = b.run("oc version --client 2>&1 || true")
    print(f"backend={b.name} exit={code}")
    print(out)
