"""Golden Astronaut 2026 - facilitator: HTTP server (UI + JSON API).

Pure stdlib. Config via environment:
  GA_BANKS    path to banks root          (default ./banks)
  GA_STATE    path to attempts state dir  (default ./state)
  GA_CONDUCTOR  conductor base URL        (default http://127.0.0.1:9001)
  GA_ADDR     bind address                (default 127.0.0.1)
  GA_PORT     port                        (default 8900)
"""

from __future__ import annotations

import argparse
import json
import os
import random
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import state
from .bank import Bank, BankError, discover

BASE = Path(__file__).resolve().parent
UI_DIR = BASE / "ui"


class Fac:
    def __init__(self, banks_root: Path, state_root: Path, conductor_url: str):
        self.banks_root = banks_root
        self.state_root = state_root
        self.conductor_url = conductor_url
        self.lock = threading.Lock()

    # ---- helpers ---------------------------------------------------------
    def _banks(self) -> list[dict]:
        return [{
            "id": b.id,
            "title": b.title,
            "engine": b.exam.get("engine", "mixed"),
            "draw_size": b.draw_size,
            "duration_minutes": b.duration_minutes,
            "pass_threshold": b.pass_threshold,
            "n_questions": len(b.questions),
            "domains": b.domains,
        } for b in discover(self.banks_root)]

    def _public_question(self, q, reveal: bool) -> dict:
        d = {
            "qid": q.qid,
            "kind": q.kind,
            "domain": q.domain,
            "title": q.title,
            "prompt": q.prompt,
            "level": q.level,
        }
        if q.kind == "knowledge":
            d["options"] = q.options
        if reveal:
            if q.kind == "knowledge":
                d["answer"] = q.answer
                d["explanation"] = q.explanation
            else:
                d["solution"] = q.solution
        return d

    def _create_attempt(self, bank_id: str, mode: str, focus_domain: str | None) -> dict:
        bank = Bank(self.banks_root / bank_id)
        rng = random.Random()
        if mode == "training":
            drawn = bank.questions[:]  # train on everything
        elif focus_domain:
            drawn = bank.draw(rng, bank.draw_size, focus_domain=focus_domain)
        else:
            drawn = bank.draw(rng, bank.draw_size)

        attempt = {
            "id": state.new_attempt_id(),
            "bank": bank_id,
            "mode": mode,
            "focus_domain": focus_domain,
            "drawn": [q.qid for q in drawn],
            "answers": {},
            "status": "active",
            "started_at": time.time(),
            "duration_seconds": bank.duration_minutes * 60 if mode != "training" else 0,
            "questions": [self._public_question(q, reveal=(mode == "training")) for q in drawn],
            "result": None,
        }
        state.save(self.state_root, attempt)
        return attempt

    def _submit(self, attempt_id: str) -> dict:
        attempt = state.load(self.state_root, attempt_id)
        if attempt is None:
            raise KeyError(attempt_id)
        if attempt["result"] is not None:
            return attempt
        if state.seconds_remaining(attempt) == 0 and attempt["mode"] != "training":
            attempt["status"] = "expired"
        payload = json.dumps({"attempt_id": attempt_id}).encode()
        req = urllib.request.Request(self.conductor_url + "/grade",
                                     data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=180) as resp:
            result = json.loads(resp.read())
        attempt["status"] = "graded"
        attempt["result"] = result
        attempt["ended_at"] = time.time()
        state.save(self.state_root, attempt)
        return attempt


class Handler(BaseHTTPRequestHandler):
    fac: Fac = None  # set in main()

    # -- plumbing ----------------------------------------------------------
    def log_message(self, fmt, *args):
        print("[facilitator] " + (fmt % args))

    def _json(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _text(self, text, code=200, ctype="text/plain"):
        body = text.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self) -> dict:
        n = int(self.headers.get("Content-Length", 0) or 0)
        if not n:
            return {}
        return json.loads(self.rfile.read(n)) if n else {}

    # -- routing -----------------------------------------------------------
    def do_GET(self):
        path = self.path.split("?")[0]
        try:
            if path in ("/", "/index.html"):
                self._serve_static("index.html", "text/html")
            elif path == "/exam.html":
                self._serve_static("exam.html", "text/html")
            elif path.startswith("/static/"):
                name = path[len("/static/"):]
                self._serve_static("static/" + name, _ctype(name))
            elif path == "/api/banks":
                self._json(self.fac._banks())
            elif path == "/api/attempts":
                self._json([self._public_attempt(a) for a in state.list_attempts(self.fac.state_root)])
            elif path.startswith("/api/attempts/") and path.endswith("/result"):
                aid = path.split("/")[3]
                a = state.load(self.fac.state_root, aid)
                if not a:
                    self._json({"error": "not found"}, 404)
                else:
                    self._json(a["result"] if a["result"] else {"status": "not-graded"})
            elif path.startswith("/api/attempts/"):
                aid = path.split("/")[3]
                a = state.load(self.fac.state_root, aid)
                if not a:
                    self._json({"error": "not found"}, 404)
                else:
                    self._json(self._public_attempt(a))
            elif path == "/api/healthz":
                self._json({"ok": True})
            else:
                self._json({"error": "not found"}, 404)
        except Exception as e:  # noqa: BLE001
            self._json({"error": str(e)}, 500)

    def do_POST(self):
        path = self.path.split("?")[0]
        try:
            if path == "/api/attempts":
                body = self._read_body()
                bank_id = body.get("bank")
                mode = body.get("mode", "mastery")
                focus = body.get("focus_domain")
                if mode not in ("training", "mastery", "exam"):
                    self._json({"error": "bad mode"}, 400)
                    return
                try:
                    a = self.fac._create_attempt(bank_id, mode, focus)
                except BankError as e:
                    self._json({"error": str(e)}, 400)
                    return
                self._json(self._public_attempt(a), 201)
            elif path.startswith("/api/attempts/") and path.endswith("/answers"):
                aid = path.split("/")[3]
                a = state.load(self.fac.state_root, aid)
                if not a:
                    self._json({"error": "not found"}, 404)
                    return
                a["answers"].update(self._read_body().get("answers") or {})
                state.save(self.fac.state_root, a)
                self._json({"ok": True})
            elif path.startswith("/api/attempts/") and path.endswith("/submit"):
                aid = path.split("/")[3]
                try:
                    a = self.fac._submit(aid)
                except KeyError:
                    self._json({"error": "not found"}, 404)
                    return
                self._json(self._public_attempt(a))
            elif path == "/api/healthz":
                self._json({"ok": True})
            else:
                self._json({"error": "not found"}, 404)
        except Exception as e:  # noqa: BLE001
            self._json({"error": str(e)}, 500)

    # -- rendering helpers -------------------------------------------------
    def _public_attempt(self, a: dict) -> dict:
        reveal = a["mode"] == "training" and a["status"] in ("active", "graded")
        out = dict(a)
        out["questions"] = a.get("questions")
        if a["result"]:
            out["result"] = a["result"]
        out["seconds_remaining"] = state.seconds_remaining(a)
        out.pop("answers", None)
        return out

    def _serve_static(self, rel: str, ctype: str):
        p = UI_DIR / rel
        if not p.is_file():
            self._json({"error": "not found"}, 404)
            return
        self._text(p.read_text(), ctype=ctype)


def _ctype(name: str) -> str:
    return {
        ".html": "text/html",
        ".css": "text/css",
        ".js": "text/javascript",
        ".svg": "image/svg+xml",
        ".png": "image/png",
    }.get(Path(name).suffix, "text/plain")


def serve(banks_root: Path, state_root: Path, addr: str, port: int, conductor_url: str):
    f = Fac(banks_root, state_root, conductor_url)
    Handler.fac = f
    httpd = ThreadingHTTPServer((addr, port), Handler)
    print(f"[facilitator] listening on http://{addr}:{port}")
    print(f"[facilitator] banks: {banks_root}  state: {state_root}  conductor: {conductor_url}")
    httpd.serve_forever()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Golden Astronaut facilitator")
    ap.add_argument("--banks", default=os.getenv("GA_BANKS", "banks"))
    ap.add_argument("--state", default=os.getenv("GA_STATE", "state"))
    ap.add_argument("--conductor", default=os.getenv("GA_CONDUCTOR", "http://127.0.0.1:9001"))
    ap.add_argument("--addr", default=os.getenv("GA_ADDR", "127.0.0.1"))
    ap.add_argument("--port", type=int, default=int(os.getenv("GA_PORT", "8900")))
    args = ap.parse_args(argv)
    serve(Path(args.banks), Path(args.state), args.addr, args.port, args.conductor)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
