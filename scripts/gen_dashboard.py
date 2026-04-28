#!/usr/bin/env python3
"""
gen_dashboard.py — autoloop 라이브 대시보드 생성기 (v6.4 베놈 #1)

사용법:
  # baseline 직후: 대시보드 + 초기 results.json 생성
  python scripts/gen_dashboard.py init <lab_dir> --skill <name> --baseline <pct>

  # 매 4d 후: results.tsv 읽어 results.json 갱신
  python scripts/gen_dashboard.py update <lab_dir>

  # 종료 시: status를 complete로 변경
  python scripts/gen_dashboard.py finish <lab_dir>

lab_dir 안에 dashboard.html · results.tsv · results.json을 생성/갱신한다.
results.tsv는 autoloop step 4d가 append. 본 스크립트는 그것을 읽어 JSON으로 변환만 한다.

results.tsv 포맷 (탭 구분):
  experiment\tscore\tmax_score\tpass_rate\tstatus\ttarget\tdescription

빈 lines·헤더 행 자동 무시.
"""
import sys
import json
import os
import shutil
from pathlib import Path
from datetime import datetime

TEMPLATE_NAME = "dashboard-template.html"
RESULTS_TSV = "results.tsv"
RESULTS_JSON = "results.json"
DASHBOARD_HTML = "dashboard.html"


def find_template():
    """references/dashboard-template.html 자동 탐색."""
    here = Path(__file__).resolve().parent
    candidates = [
        here.parent / "references" / TEMPLATE_NAME,
        here.parent.parent / "references" / TEMPLATE_NAME,
        Path.cwd() / "references" / TEMPLATE_NAME,
    ]
    for c in candidates:
        if c.exists():
            return c
    raise FileNotFoundError(
        f"{TEMPLATE_NAME} 미발견. autoloop/references/ 안에 있어야 함. 검색 경로: {candidates}"
    )


def parse_tsv(tsv_path: Path):
    """results.tsv → list[dict]."""
    if not tsv_path.exists():
        return []
    rows = []
    with tsv_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line.strip():
                continue
            parts = line.split("\t")
            if parts[0].lower() == "experiment":  # header
                continue
            try:
                # baseline 행은 score/max_score가 "-"일 수 있음 (점수 미산출 케이스 대응)
                def _int_or_none(s):
                    s = s.strip()
                    if s in ("", "-"):
                        return None
                    return int(s)
                rows.append({
                    "id": int(parts[0]),
                    "score": _int_or_none(parts[1]),
                    "max_score": _int_or_none(parts[2]),
                    "pass_rate": float(parts[3].replace("%", "").strip()),
                    "status": parts[4] if len(parts) > 4 else "",
                    "target": parts[5] if len(parts) > 5 else "",
                    "description": parts[6] if len(parts) > 6 else "",
                })
            except (ValueError, IndexError) as e:
                print(f"warn: skip malformed line: {line!r} ({e})", file=sys.stderr)
    return rows


def build_json(skill_name: str, status: str, experiments: list, eval_breakdown=None):
    if not experiments:
        return {
            "skill_name": skill_name,
            "status": status,
            "baseline_score": None,
            "best_score": None,
            "experiments": [],
            "eval_breakdown": eval_breakdown or [],
        }
    baseline = next((e["pass_rate"] for e in experiments if e["status"] == "baseline"), experiments[0]["pass_rate"])
    best = max(e["pass_rate"] for e in experiments)
    return {
        "skill_name": skill_name,
        "status": status,
        "baseline_score": baseline,
        "best_score": best,
        "experiments": experiments,
        "eval_breakdown": eval_breakdown or [],
    }


def cmd_init(lab_dir: Path, skill: str, baseline_pct: float):
    lab_dir.mkdir(parents=True, exist_ok=True)
    template = find_template()
    shutil.copy2(template, lab_dir / DASHBOARD_HTML)

    # baseline 행이 results.tsv에 이미 있으면 그대로, 없으면 헤더만
    tsv = lab_dir / RESULTS_TSV
    if not tsv.exists():
        with tsv.open("w", encoding="utf-8") as f:
            f.write("experiment\tscore\tmax_score\tpass_rate\tstatus\ttarget\tdescription\n")
            if baseline_pct is not None:
                f.write(f"0\t-\t-\t{baseline_pct}\tbaseline\t-\toriginal skill — no changes\n")

    rows = parse_tsv(tsv)
    data = build_json(skill, "running", rows)
    (lab_dir / RESULTS_JSON).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[init] dashboard ready at {lab_dir / DASHBOARD_HTML}")
    print(f"[init] open it: open '{lab_dir / DASHBOARD_HTML}'")


def cmd_update(lab_dir: Path):
    tsv = lab_dir / RESULTS_TSV
    json_path = lab_dir / RESULTS_JSON
    if not tsv.exists():
        print(f"err: {tsv} 없음. init 먼저 호출하라.", file=sys.stderr)
        return 1

    # 기존 JSON에서 skill_name·eval_breakdown만 보존
    skill_name = "unknown"
    eval_breakdown = []
    if json_path.exists():
        try:
            prev = json.loads(json_path.read_text(encoding="utf-8"))
            skill_name = prev.get("skill_name", "unknown")
            eval_breakdown = prev.get("eval_breakdown", [])
        except Exception:
            pass

    rows = parse_tsv(tsv)
    data = build_json(skill_name, "running", rows, eval_breakdown)
    json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[update] {len(rows)} experiments → {json_path}")
    return 0


def cmd_finish(lab_dir: Path):
    json_path = lab_dir / RESULTS_JSON
    if not json_path.exists():
        print(f"err: {json_path} 없음.", file=sys.stderr)
        return 1
    data = json.loads(json_path.read_text(encoding="utf-8"))
    data["status"] = "complete"
    data["finished_at"] = datetime.now().isoformat(timespec="seconds")
    json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[finish] status=complete · {json_path}")
    return 0


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 1
    cmd = sys.argv[1]
    lab_dir = Path(sys.argv[2]).resolve()

    if cmd == "init":
        skill = "unknown"
        baseline = None
        for i, a in enumerate(sys.argv[3:], start=3):
            if a == "--skill" and i + 1 < len(sys.argv):
                skill = sys.argv[i + 1]
            if a == "--baseline" and i + 1 < len(sys.argv):
                try:
                    baseline = float(sys.argv[i + 1].replace("%", ""))
                except ValueError:
                    baseline = None
        cmd_init(lab_dir, skill, baseline)
        return 0
    elif cmd == "update":
        return cmd_update(lab_dir)
    elif cmd == "finish":
        return cmd_finish(lab_dir)
    else:
        print(f"unknown command: {cmd}", file=sys.stderr)
        print(__doc__)
        return 1


if __name__ == "__main__":
    sys.exit(main())
