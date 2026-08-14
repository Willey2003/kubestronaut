"""Golden Astronaut 2026 - bank validator.

Usage:
    python3 -m engine.validator [bank-dir ...]        # default: all banks under banks/
    ga validate
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from .bank import Bank, BankError

ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{2,63}$")
QID_RE = re.compile(r"^q[0-9]{3}$")
KINDS = ("knowledge", "hands-on")
LEVELS = ("quick", "core", "deep")


def _check_question(bank: Bank, q, errors: list[str], warnings: list[str]) -> None:
    if not QID_RE.match(q.qid):
        errors.append(f"{bank.id}/{q.qid}: id must match qNNN")
    if q.kind not in KINDS:
        errors.append(f"{bank.id}/{q.qid}: kind must be one of {KINDS}")
    if q.domain not in bank.domains and bank.domains:
        errors.append(f"{bank.id}/{q.qid}: domain '{q.domain}' not declared in exam.yaml")
    if q.level not in LEVELS:
        warnings.append(f"{bank.id}/{q.qid}: level '{q.level}' not in {LEVELS}")
    if not q.title:
        errors.append(f"{bank.id}/{q.qid}: missing title")
    if not q.prompt:
        errors.append(f"{bank.id}/{q.qid}: missing prompt")

    if q.kind == "knowledge":
        if not q.options or len(q.options) < 2:
            errors.append(f"{bank.id}/{q.qid}: knowledge question needs >= 2 options")
        if q.answer not in q.options:
            errors.append(f"{bank.id}/{q.qid}: answer '{q.answer}' not in options")
        if not q.explanation:
            warnings.append(f"{bank.id}/{q.qid}: knowledge question without explanation")
    else:  # hands-on
        if not q.checks:
            errors.append(f"{bank.id}/{q.qid}: hands-on question needs >= 1 check")
        for i, c in enumerate(q.checks):
            if not isinstance(c, dict) or not c.get("run"):
                errors.append(f"{bank.id}/{q.qid}: check {i} missing 'run'")
                continue
            expectations = [k for k in ("equals", "contains", "matches",
                                        "not-equals", "non-empty", "exit-success")
                            if k in c]
            if len(expectations) != 1:
                errors.append(f"{bank.id}/{q.qid}: check {i} needs exactly one expectation")
            if "matches" in c:
                try:
                    re.compile(c["matches"])
                except re.error as e:
                    errors.append(f"{bank.id}/{q.qid}: check {i} bad regex: {e}")
        if not q.solution:
            warnings.append(f"{bank.id}/{q.qid}: hands-on question without solution")


def validate_bank(path: Path, errors: list[str], warnings: list[str]) -> Bank | None:
    try:
        bank = Bank(path)
    except BankError as e:
        errors.append(str(e))
        return None

    exam = bank.exam
    if not ID_RE.match(str(exam.get("id", ""))):
        errors.append(f"{bank.id}: exam.yaml 'id' invalid")
    if not exam.get("title"):
        errors.append(f"{bank.id}: exam.yaml missing 'title'")
    if exam.get("engine") not in ("knowledge", "hands-on", "mixed"):
        errors.append(f"{bank.id}: exam.yaml 'engine' must be knowledge|hands-on|mixed")
    if not (0 < bank.pass_threshold <= 1):
        errors.append(f"{bank.id}: pass_threshold must be in (0,1]")
    if bank.draw_size < 1:
        errors.append(f"{bank.id}: draw_size must be >= 1")

    domains = bank.domains
    if not domains:
        errors.append(f"{bank.id}: exam.yaml needs 'domains'")
    else:
        total = sum(domains.values())
        if abs(total - 1.0) > 0.02:
            errors.append(f"{bank.id}: domain weights sum to {total:.2f}, want ~1.0")
    if bank.draw_size > len(bank.questions):
        errors.append(f"{bank.id}: draw_size {bank.draw_size} > {len(bank.questions)} questions")

    for q in bank.questions:
        _check_question(bank, q, errors, warnings)
    return bank


def validate_root(root: Path) -> int:
    errors, warnings = [], []
    if (root / "exam.yaml").is_file():
        banks = [root]
    else:
        banks = [d for d in sorted(root.iterdir()) if (d / "exam.yaml").is_file()]
    if not banks:
        print(f"[warn] no banks found under {root}")
        return 0
    for b in banks:
        bank = validate_bank(b, errors, warnings)
        if bank:
            print(f"OK   {bank.id}: {len(bank.questions)} questions, "
                  f"draw {bank.draw_size}, threshold {bank.pass_threshold:.0%}")
    for w in warnings:
        print(f"[warn] {w}")
    for e in errors:
        print(f"[error] {e}")
    if errors:
        print(f"\n{len(errors)} error(s), {len(warnings)} warning(s)")
        return 1
    print(f"\nAll banks valid ({len(banks)} bank(s), {len(warnings)} warning(s)).")
    return 0


def main(argv=None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    if argv:
        code = 0
        for arg in argv:
            code |= validate_root(Path(arg))
        return code
    root = Path(__file__).resolve().parent.parent / "banks"
    return validate_root(root)


if __name__ == "__main__":
    sys.exit(main())
