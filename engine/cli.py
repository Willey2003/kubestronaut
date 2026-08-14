"""Golden Astronaut 2026 - platform CLI (`ga`).

Commands:
  ga doctor            preflight checks
  ga validate          validate all banks
  ga build             build platform images
  ga up                start the platform (docker compose)
  ga down              stop the platform (state preserved)
  ga logs [svc]        follow logs
  ga expose            bind facilitator + desktop to 0.0.0.0 for LAN use
  ga status            list banks and attempts
  ga exam <bank>       headless: create a mastery attempt and print it

Run `python3 -m engine.cli <cmd>` or the ./ga wrapper.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATE_DIR = ROOT / "state"


def _sh(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)


def _have(cmd: str) -> bool:
    return shutil.which(cmd) is not None


def doctor() -> int:
    print("Golden Astronaut 2026 - preflight")
    checks = [
        ("python3", _have("python3")),
        ("docker", _have("docker")),
        ("docker compose", _have("docker") and subprocess.run(
            ["docker", "compose", "version"], capture_output=True).returncode == 0),
        ("oc  (cluster client)", _have("oc")),
        ("kubectl", _have("kubectl")),
    ]
    ok = True
    for name, good in checks:
        print(f"  [{'ok' if good else '!!'}] {name}")
        ok &= good
    # RAM
    try:
        with open("/proc/meminfo") as fh:
            kb = int([l for l in fh if l.startswith("MemTotal")][0].split()[1])
        ram_gb = kb / 1024 / 1024
        print(f"  [{'ok' if ram_gb >= 8 else '!!'}] RAM {ram_gb:.1f} GB (>= 8 GB for CRC)")
        ok &= ram_gb >= 8
    except FileNotFoundError:
        print("  [..] RAM: /proc/meminfo not readable")
    return 0 if ok else 1


def validate() -> int:
    from .validator import validate_root
    return validate_root(ROOT / "banks")


def _compose(*args: str) -> int:
    proc = _sh(["docker", "compose", *args])
    print(proc.stdout, end="")
    if proc.stderr:
        print(proc.stderr, end="", file=sys.stderr)
    return proc.returncode


def build() -> int:
    return _compose("build")


def up() -> int:
    return _compose("up", "-d", "--build")


def down() -> int:
    return _compose("down")


def logs(service: str | None) -> int:
    return _compose("logs", "-f", service) if service else _compose("logs", "-f")


def expose() -> int:
    print("Rebinding facilitator (8900) and desktop (6080-6081) to 0.0.0.0 ...")
    print("NOTE: platform has no authentication - private LAN only. See docs/security.md")
    return _compose("up", "-d")


def status() -> int:
    from .bank import discover
    print("Banks:")
    for b in discover(ROOT / "banks"):
        print(f"  {b.id:<16} {b.title}  ({len(b.questions)}q, draw {b.draw_size}, "
              f"pass {b.pass_threshold:.0%})")
    from . import state as st
    attempts = st.list_attempts(STATE_DIR)
    print(f"\nAttempts ({len(attempts)}):")
    for a in attempts[:10]:
        pct = a["result"]["pct"] if a.get("result") else "-"
        print(f"  {a['id']}  {a['bank']:<14} {a['mode']:<8} status={a['status']} pct={pct}")
    return 0


def exam(bank_id: str, mode: str = "mastery", addr: str = "http://127.0.0.1:8900") -> int:
    body = json.dumps({"bank": bank_id, "mode": mode}).encode()
    req = urllib.request.Request(addr + "/api/attempts", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as resp:
        attempt = json.loads(resp.read())
    print(json.dumps({k: v for k, v in attempt.items() if k != "questions"}, indent=2))
    print(f"\n{len(attempt.get('questions', []))} questions drawn.")
    print(f"Open the UI at {addr}/exam.html?attempt={attempt['id']} to sit it.")
    return 0


COMMANDS = {
    "doctor": doctor,
    "validate": validate,
    "build": build,
    "up": up,
    "down": down,
    "logs": logs,
    "expose": expose,
    "status": status,
    "exam": exam,
}


def main(argv=None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    if not argv or argv[0] in ("-h", "--help", "help"):
        print(__doc__)
        return 0
    cmd, rest = argv[0], argv[1:]
    if cmd not in COMMANDS:
        print(f"unknown command: {cmd}\n{__doc__}")
        return 2
    if cmd == "logs":
        return logs(rest[0] if rest else None)
    if cmd == "exam":
        if not rest:
            print("usage: ga exam <bank-id> [--mode training|mastery|exam]")
            return 2
        mode = "mastery"
        if "--mode" in rest:
            i = rest.index("--mode")
            mode = rest[i + 1]
            rest = rest[:i]
        return exam(rest[0], mode)
    return COMMANDS[cmd]()


if __name__ == "__main__":
    sys.exit(main())
