#!/usr/bin/env python3
"""self_check.py — autoloop 자체 점검 스크립트.

스킬이 기본 invariant를 유지하는지 확인한다. skill-doctor의 외부 진단과 별개로
스킬 내부에서 실행 가능한 경량 점검이다.

검사 항목:
  1. SKILL.md 존재 + 크기 <= 10KB 권장 (5KB 목표)
  2. references/ 4개 핵심 스포크 존재
  3. evals/cases.json 로드 가능 + case id 중복 없음
  4. P1 키워드 5개 이상
  5. NOT 섹션 존재
  6. Gotchas 섹션 존재
  7. "절대 금지" 또는 "절대 규칙" 최소 1건

exit 0 = PASS, exit 1 = FAIL.
usage:
    python scripts/self_check.py [path_to_autoloop_dir]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


REQUIRED_REFERENCES = [
    "eval-guide.md",
    "loop-mechanics.md",
    "trigger-principles.md",
    "schemas.md",
    "execution-steps.md",
]


def check(path: Path) -> tuple[bool, list[str]]:
    failures: list[str] = []
    warnings: list[str] = []

    skill_md = path / "SKILL.md"
    if not skill_md.exists():
        failures.append(f"SKILL.md missing at {skill_md}")
        return False, failures

    body = skill_md.read_text(encoding="utf-8")
    size = len(body.encode("utf-8"))
    if size > 10 * 1024:
        failures.append(f"SKILL.md too large: {size}B (>10KB hub limit)")
    elif size > 5 * 1024:
        warnings.append(f"SKILL.md above target: {size}B (>5KB target)")

    refs = path / "references"
    for ref in REQUIRED_REFERENCES:
        if not (refs / ref).exists():
            failures.append(f"missing reference: references/{ref}")

    cases = path / "scripts" / "self_check_cases.json"
    if not cases.exists():
        failures.append("scripts/self_check_cases.json missing")
    else:
        try:
            data = json.loads(cases.read_text(encoding="utf-8"))
            ids = [c.get("id") for c in data.get("cases", [])]
            if len(ids) != len(set(ids)):
                failures.append(f"duplicate case id in scripts/self_check_cases.json: {ids}")
            if len(ids) < 3:
                warnings.append(f"self_check_cases.json has {len(ids)} case(s); recommend >=3")
        except json.JSONDecodeError as exc:
            failures.append(f"self_check_cases.json invalid JSON: {exc}")

    # P1 keyword count
    import re
    p1_match = re.search(r"P1:\s*([^\n]+)", body)
    if not p1_match:
        failures.append("description P1 line missing")
    else:
        p1_items = [x.strip() for x in p1_match.group(1).split(",") if x.strip()]
        if len(p1_items) < 5:
            failures.append(f"P1 keywords={len(p1_items)} (min 5)")

    if "NOT:" not in body:
        failures.append("description NOT line missing")
    if "Gotchas" not in body:
        failures.append("Gotchas section missing")
    if ("절대 금지" not in body) and ("절대 규칙" not in body):
        failures.append("invariant block missing (need '절대 금지' or '절대 규칙')")

    report = {
        "target": str(path),
        "size_bytes": size,
        "failures": failures,
        "warnings": warnings,
        "status": "PASS" if not failures else "FAIL",
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return not failures, failures


def main() -> int:
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent
    ok, _ = check(target)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
