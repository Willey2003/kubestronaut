"""Golden Astronaut 2026 - conductor: grades attempts.

Knowledge questions: exact answer match.
Hands-on questions: run the task's checks against a cluster backend and
compare expectations. Points split evenly across checks.

Usage:
    python3 -m engine.conductor <attempt.json> --cluster local
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .bank import Bank
from .cluster_backend import Backend, make_backend


class Conductor:
    def __init__(self, bank_root: Path, cluster_spec: str = "none"):
        self.bank_root = Path(bank_root)
        self.cluster: Backend = make_backend(cluster_spec)

    def _bank(self, bank_id: str) -> Bank:
        return Bank(self.bank_root / bank_id)

    def grade_attempt(self, attempt: dict, live: bool = True) -> dict:
        bank = self._bank(attempt["bank"])
        answers = attempt.get("answers") or {}

        questions = {q.qid: q for q in bank.questions}
        drawn = attempt.get("drawn", [])
        results = []
        total_earned = 0.0
        total_possible = 0.0
        for qid in drawn:
            q = questions.get(qid)
            if q is None:
                continue
            given = answers.get(qid)
            max_pts = q.max_points()
            total_possible += max_pts
            verdict, earned, detail = self._grade_question(bank, q, given, live)
            results.append({
                "qid": qid,
                "domain": q.domain,
                "title": q.title,
                "earned": round(earned, 3),
                "max": max_pts,
                "verdict": verdict,
                "detail": detail,
            })
            total_earned += earned

        pct = (total_earned / total_possible) if total_possible else 0.0
        return {
            "id": attempt["id"],
            "bank": bank.id,
            "mode": attempt.get("mode"),
            "pct": round(pct, 4),
            "passed": pct >= bank.pass_threshold,
            "threshold": bank.pass_threshold,
            "earned": round(total_earned, 3),
            "possible": round(total_possible, 3),
            "results": results,
            "domains": self._domain_breakdown(results),
        }

    def _grade_question(self, bank: Bank, q, given, live: bool) -> tuple[str, float, list]:
        if q.kind == "knowledge":
            if given is None:
                return "unanswered", 0.0, []
            ok = str(given).strip().upper() == str(q.answer).strip().upper()
            return ("pass" if ok else "fail", 1.0 if ok else 0.0,
                    [{"desc": "Correct answer selected", "pass": ok}])

        # hands-on
        if not live or self.cluster.name == "none":
            return "not-graded", 0.0, [{"desc": "No cluster backend (Training / no cluster)", "pass": None}]

        detail = []
        passed = 0
        for c in q.checks:
            code, out = self.cluster.run(c["run"])
            ok = self._expectation(c, code, out)
            passed += 1 if ok else 0
            detail.append({"desc": c.get("desc", c["run"]), "run": c["run"], "pass": ok, "output": out[:400]})
        total = len(q.checks)
        return ("pass" if passed == total else "fail", passed / total, detail)

    @staticmethod
    def _expectation(check: dict, code: int, out: str) -> bool:
        if "exit-success" in check:
            return code == 0
        if "non-empty" in check:
            return bool(out.strip())
        if "equals" in check:
            return out.strip() == str(check["equals"]).strip()
        if "not-equals" in check:
            return out.strip() != str(check["not-equals"]).strip()
        if "contains" in check:
            return str(check["contains"]) in out
        if "matches" in check:
            return re.search(check["matches"], out, re.DOTALL) is not None
        return False

    @staticmethod
    def _domain_breakdown(results: list[dict]) -> list[dict]:
        agg = {}
        for r in results:
            agg.setdefault(r["domain"], {"earned": 0.0, "possible": 0.0})
            agg[r["domain"]]["earned"] += r["earned"]
            agg[r["domain"]]["possible"] += r["max"]
        out = []
        for d, v in agg.items():
            out.append({"domain": d, "pct": (v["earned"] / v["possible"]) if v["possible"] else 0.0})
        out.sort(key=lambda x: x["pct"])
        return out


def main(argv=None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    if argv and argv[0] == "--serve":
        return _serve(argv[1:])
    ap = argparse.ArgumentParser(description="Grade an attempt JSON")
    ap.add_argument("attempt", type=Path)
    ap.add_argument("--banks", type=Path, default=Path("banks"))
    ap.add_argument("--cluster", default="local")
    args = ap.parse_args(argv)

    attempt = json.loads(args.attempt.read_text())
    c = Conductor(args.banks, args.cluster)
    result = c.grade_attempt(attempt)
    print(json.dumps(result, indent=2))
    return 0 if result["passed"] else 1


class _ConductorHandler(BaseHTTPRequestHandler):
    conductor: "Conductor" = None

    def log_message(self, fmt, *args):
        print("[conductor] " + (fmt % args))

    def _json(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if self.path != "/grade":
            self._json({"error": "not found"}, 404)
            return
        try:
            n = int(self.headers.get("Content-Length", 0) or 0)
            payload = json.loads(self.rfile.read(n)) if n else {}
            aid = payload.get("attempt_id")
            state_root = Path(os.environ.get("GA_STATE", "state"))
            banks_root = Path(os.environ.get("GA_BANKS", "banks"))
            from . import state as state_mod

            attempt = state_mod.load(state_root, aid)
            if not attempt:
                self._json({"error": "attempt not found"}, 404)
                return
            result = self.conductor.grade_attempt(attempt)
            self._json(result)
        except Exception as e:  # noqa: BLE001
            self._json({"error": str(e)}, 500)

    def do_GET(self):
        if self.path in ("/healthz", "/"):
            self._json({"ok": True})
        else:
            self._json({"error": "not found"}, 404)


def _serve(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Run the conductor as an HTTP service")
    ap.add_argument("--addr", default=os.environ.get("GA_ADDR", "0.0.0.0"))
    ap.add_argument("--port", type=int, default=int(os.environ.get("GA_CONDUCTOR_PORT", "9001")))
    ap.add_argument("--cluster", default=os.environ.get("GA_CLUSTER", "local"))
    ap.add_argument("--banks", default=os.environ.get("GA_BANKS", "banks"))
    args = ap.parse_args(argv)
    _ConductorHandler.conductor = Conductor(Path(args.banks), args.cluster)
    httpd = ThreadingHTTPServer((args.addr, args.port), _ConductorHandler)
    print(f"[conductor] listening on {args.addr}:{args.port}  cluster={args.cluster}")
    httpd.serve_forever()
    return 0


if __name__ == "__main__":
    sys.exit(main())
