"""Golden Astronaut 2026 - bank loading and stratified question draws.

Pure stdlib. A bank is a directory with exam.yaml plus one YAML per question.
"""

from __future__ import annotations

import os
import random
import re
from pathlib import Path

try:
    import yaml  # type: ignore
except ImportError:
    yaml = None  # validator and facilitator report this clearly


class BankError(Exception):
    pass


class Question:
    def __init__(self, bank_id: str, qid: str, data: dict):
        self.bank_id = bank_id
        self.qid = qid
        self.data = data

    @property
    def kind(self) -> str:
        return self.data.get("kind", "knowledge")

    @property
    def domain(self) -> str:
        return self.data.get("domain", "misc")

    @property
    def level(self) -> str:
        return self.data.get("level", "core")

    @property
    def title(self) -> str:
        return self.data.get("title", self.qid)

    @property
    def prompt(self) -> str:
        return self.data.get("prompt", "")

    @property
    def options(self) -> dict:
        return self.data.get("options") or {}

    @property
    def answer(self):
        return self.data.get("answer")

    @property
    def explanation(self) -> str:
        return self.data.get("explanation", "")

    @property
    def solution(self) -> str:
        return self.data.get("solution", "")

    @property
    def checks(self) -> list:
        return self.data.get("checks") or []

    @property
    def setup(self) -> list:
        return self.data.get("setup") or []

    def max_points(self) -> float:
        if self.kind == "knowledge":
            return 1.0
        return float(len(self.checks))


class Bank:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.id = self.path.name
        self.exam = {}
        self.questions: list[Question] = []
        self._load()

    def _load(self):
        exam_file = self.path / "exam.yaml"
        if not exam_file.is_file():
            raise BankError(f"bank {self.id}: missing exam.yaml")
        if yaml is None:
            raise BankError("PyYAML is required to read banks (pip install pyyaml)")
        with exam_file.open() as fh:
            self.exam = yaml.safe_load(fh) or {}
        if self.exam.get("id") != self.id:
            raise BankError(f"bank {self.id}: exam.yaml id '{self.exam.get('id')}' != dir name")

        for f in sorted(self.path.glob("q*.yaml")):
            qid = f.stem
            with f.open() as fh:
                data = yaml.safe_load(fh) or {}
            self.questions.append(Question(self.id, qid, data))

        if not self.questions:
            raise BankError(f"bank {self.id}: no q*.yaml files")

    # ---- metadata helpers -------------------------------------------------
    @property
    def title(self) -> str:
        return self.exam.get("title", self.id)

    @property
    def draw_size(self) -> int:
        return int(self.exam.get("draw_size", 10))

    @property
    def pass_threshold(self) -> float:
        return float(self.exam.get("pass_threshold", 0.7))

    @property
    def duration_minutes(self) -> int:
        return int(self.exam.get("duration_minutes", 120))

    @property
    def domains(self) -> dict:
        return {k: float(v) for k, v in (self.exam.get("domains") or {}).items()}

    @property
    def levels(self) -> dict:
        return {k: float(v) for k, v in (self.exam.get("levels") or {}).items()}

    def questions_for(self, domain: str = None, level: str = None) -> list:
        out = self.questions
        if domain:
            out = [q for q in out if q.domain == domain]
        if level:
            out = [q for q in out if q.level == level]
        return out

    # ---- draws -----------------------------------------------------------
    def draw(self, rng: random.Random, size: int = None, focus_domain: str = None) -> list:
        """Stratified draw: weight by domain (and level) from exam.yaml.

        Returns a list of Questions with no repeats. Falls back gracefully when
        a domain has fewer questions than its quota.
        """
        size = size or self.draw_size
        rng = rng or random.Random()
        domains = self.domains
        if focus_domain:
            quota = {focus_domain: size}
        else:
            quota = {}
            for d, w in domains.items():
                quota[d] = max(1, round(w * size))
            # top up if the quotas don't reach size
            total = sum(quota.values())
            if total < size:
                extra = list(domains) if domains else [q.domain for q in self.questions]
                rng.shuffle(extra)
                i = 0
                while total < size and extra:
                    d = extra[i % len(extra)]
                    quota[d] = quota.get(d, 0) + 1
                    total += 1
                    i += 1
            elif total > size:
                # trim from the smallest quota buckets first
                for d in sorted(quota, key=quota.get)[: total - size]:
                    quota[d] = max(1, quota[d] - 1)

        levels = self.levels or {}
        drawn = []
        seen = set()
        for d, qty in quota.items():
            pool = [q for q in self.questions if q.domain == d]
            if not pool:
                continue
            # apply level stratification within the domain when configured
            if levels:
                ordered = []
                for lvl, lw in sorted(levels.items(), key=lambda kv: -kv[1]):
                    lvl_pool = [q for q in pool if q.level == lvl and q.qid not in seen]
                    n = min(round(lw * qty), qty - len(ordered), len(lvl_pool))
                    if n > 0:
                        chosen = rng.sample(lvl_pool, n)
                        ordered.extend(chosen)
                        seen.update(q.qid for q in chosen)
                short = qty - len(ordered)
                if short > 0:
                    remainder = [q for q in pool if q.qid not in seen]
                    for q in rng.sample(remainder, min(short, len(remainder))):
                        ordered.append(q)
                        seen.add(q.qid)
                drawn.extend(ordered[:qty])
            else:
                pool = [q for q in pool if q.qid not in seen]
                chosen = rng.sample(pool, min(qty, len(pool)))
                seen.update(q.qid for q in chosen)
                drawn.extend(chosen)
        return drawn[:size]


def discover(banks_root: Path) -> list[Bank]:
    out = []
    if not banks_root.is_dir():
        return out
    for d in sorted(banks_root.iterdir()):
        if (d / "exam.yaml").is_file():
            try:
                out.append(Bank(d))
            except BankError:
                continue
    return out
