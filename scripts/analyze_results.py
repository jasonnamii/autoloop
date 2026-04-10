#!/usr/bin/env python3
"""
autoloop 실험 결과 분석기.

results.tsv를 읽어 통계 요약 + 시각화 PNG를 생성한다.
dashboard.html의 브라우저 기반 차트를 보완하는 오프라인 분석 도구.

산출물:
  - summary_stats.json    — 핵심 통계 (baseline, best, improvement, keep_rate 등)
  - score_trend.png       — 실험별 점수 추이 라인 차트
  - eval_heatmap.png      — eval별 pass/fail 히트맵 (results.json 필요)
  - branch_summary.png    — 분기 탐색 요약 (full 모드, results.json 필요)
  - experiment_report.md  — 마크다운 요약 리포트

사용법:
  python scripts/analyze_results.py <autoloop-dir>

예시:
  python scripts/analyze_results.py autoloop-diagram-generator/
"""

import sys
import json
import pathlib
from typing import Any

# ---------------------------------------------------------------------------
# Lazy imports — pip install pandas matplotlib 필요
# ---------------------------------------------------------------------------

def _import_pandas():
    try:
        import pandas as pd
        return pd
    except ImportError:
        print("ERROR: pandas 필요. `pip install pandas` 실행 후 재시도.", file=sys.stderr)
        sys.exit(1)

def _import_matplotlib():
    try:
        import matplotlib
        matplotlib.use("Agg")  # headless
        import matplotlib.pyplot as plt
        import matplotlib.ticker as ticker
        # CJK(한글) 폰트 fallback
        import matplotlib.font_manager as fm
        cjk_candidates = [
            "AppleGothic", "Apple SD Gothic Neo",           # macOS
            "NanumGothic", "Malgun Gothic",                 # Korean
            "Noto Sans CJK KR", "Noto Sans KR",            # Noto
            "WenQuanYi Micro Hei", "Droid Sans Fallback",  # Linux fallback
        ]
        available = {f.name for f in fm.fontManager.ttflist}
        for font_name in cjk_candidates:
            if font_name in available:
                matplotlib.rcParams["font.family"] = font_name
                matplotlib.rcParams["axes.unicode_minus"] = False
                break
        return plt, ticker
    except ImportError:
        print("ERROR: matplotlib 필요. `pip install matplotlib` 실행 후 재시도.", file=sys.stderr)
        sys.exit(1)


# ---------------------------------------------------------------------------
# 1. 데이터 로드
# ---------------------------------------------------------------------------

def load_results_tsv(dirpath: pathlib.Path):
    """results.tsv → pandas DataFrame. 컬럼: experiment, score, max_score, pass_rate, status, description"""
    pd = _import_pandas()
    tsv = dirpath / "results.tsv"
    if not tsv.exists():
        print(f"ERROR: {tsv} 없음.", file=sys.stderr)
        sys.exit(1)
    df = pd.read_csv(tsv, sep="\t")
    # pass_rate가 문자열 "70.0%" 형태일 수 있음 → float 변환
    if df["pass_rate"].dtype == object:
        df["pass_rate"] = df["pass_rate"].str.rstrip("%").astype(float)
    return df


def load_results_json(dirpath: pathlib.Path) -> dict | None:
    """results.json → dict. 없으면 None."""
    jf = dirpath / "results.json"
    if not jf.exists():
        return None
    with open(jf, "r", encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# 2. 통계 계산
# ---------------------------------------------------------------------------

def compute_stats(df) -> dict[str, Any]:
    """핵심 통계 계산."""
    baseline = df[df["status"] == "baseline"]
    keeps = df[df["status"] == "keep"]
    discards = df[df["status"] == "discard"]
    total_experiments = len(df) - len(baseline)  # baseline 제외

    baseline_rate = float(baseline["pass_rate"].iloc[0]) if len(baseline) > 0 else 0.0
    best_row = df.loc[df["pass_rate"].idxmax()]
    worst_row = df.loc[df["pass_rate"].idxmin()]

    # 누적 최고 점수 추적 (keep만 반영)
    cumulative_best = baseline_rate
    keep_trajectory = [baseline_rate]
    for _, row in df.iterrows():
        if row["status"] == "keep":
            cumulative_best = max(cumulative_best, float(row["pass_rate"]))
        keep_trajectory.append(cumulative_best)

    stats = {
        "baseline_score": int(baseline["score"].iloc[0]) if len(baseline) > 0 else 0,
        "baseline_pass_rate": baseline_rate,
        "best_score": int(best_row["score"]),
        "best_pass_rate": float(best_row["pass_rate"]),
        "best_experiment": int(best_row["experiment"]),
        "worst_pass_rate": float(worst_row["pass_rate"]),
        "final_pass_rate": cumulative_best,
        "improvement_pp": round(cumulative_best - baseline_rate, 1),
        "total_experiments": total_experiments,
        "keeps": len(keeps),
        "discards": len(discards),
        "keep_rate": round(len(keeps) / total_experiments * 100, 1) if total_experiments > 0 else 0.0,
        "max_score": int(df["max_score"].iloc[0]),
        "mean_pass_rate": round(float(df["pass_rate"].mean()), 1),
        "std_pass_rate": round(float(df["pass_rate"].std()), 1),
    }
    return stats


# ---------------------------------------------------------------------------
# 3. 시각화
# ---------------------------------------------------------------------------

def plot_score_trend(df, stats: dict, outpath: pathlib.Path):
    """실험별 점수 추이 라인 차트 → PNG."""
    plt, ticker = _import_matplotlib()

    fig, ax = plt.subplots(figsize=(10, 5))

    experiments = df["experiment"].values
    pass_rates = df["pass_rate"].values
    statuses = df["status"].values

    # 색상 매핑
    colors = []
    for s in statuses:
        if s == "baseline":
            colors.append("#4A90D9")   # 파랑
        elif s == "keep":
            colors.append("#27AE60")   # 초록
        else:
            colors.append("#E74C3C")   # 빨강

    # 라인
    ax.plot(experiments, pass_rates, color="#555555", linewidth=1.5, zorder=1)
    # 점 (상태별 색상)
    ax.scatter(experiments, pass_rates, c=colors, s=80, zorder=2, edgecolors="white", linewidths=1.2)

    # baseline 수평선
    ax.axhline(y=stats["baseline_pass_rate"], color="#4A90D9", linestyle="--", alpha=0.5, label=f'Baseline {stats["baseline_pass_rate"]}%')
    # best 수평선
    ax.axhline(y=stats["best_pass_rate"], color="#27AE60", linestyle="--", alpha=0.5, label=f'Best {stats["best_pass_rate"]}%')

    ax.set_xlabel("Experiment #", fontsize=12)
    ax.set_ylabel("Pass Rate (%)", fontsize=12)
    ax.set_title("Autoresearch Score Trend", fontsize=14, fontweight="bold")
    ax.yaxis.set_major_formatter(ticker.FormatStrFormatter("%.0f%%"))
    ax.set_ylim(max(0, stats["worst_pass_rate"] - 10), 105)
    ax.legend(loc="lower right", fontsize=10)
    ax.grid(axis="y", alpha=0.3)

    # 범례 마커
    from matplotlib.lines import Line2D
    legend_elements = [
        Line2D([0], [0], marker='o', color='w', markerfacecolor='#4A90D9', markersize=10, label='Baseline'),
        Line2D([0], [0], marker='o', color='w', markerfacecolor='#27AE60', markersize=10, label='Keep'),
        Line2D([0], [0], marker='o', color='w', markerfacecolor='#E74C3C', markersize=10, label='Discard'),
    ]
    ax.legend(handles=legend_elements, loc="lower right", fontsize=10)

    fig.tight_layout()
    fig.savefig(outpath, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  -> {outpath}")


def plot_eval_heatmap(results_json: dict, outpath: pathlib.Path):
    """eval별 pass rate 바 차트 → PNG. results.json의 eval_breakdown 필요."""
    plt, ticker = _import_matplotlib()
    pd = _import_pandas()

    breakdown = results_json.get("eval_breakdown", [])
    if not breakdown:
        print("  -> eval_breakdown 데이터 없음, 히트맵 스킵.")
        return

    names = [e["name"] for e in breakdown]
    rates = [round(e["pass_count"] / e["total"] * 100, 1) if e["total"] > 0 else 0 for e in breakdown]

    fig, ax = plt.subplots(figsize=(8, max(3, len(names) * 0.8)))

    bar_colors = ["#27AE60" if r >= 80 else "#F39C12" if r >= 60 else "#E74C3C" for r in rates]
    bars = ax.barh(names, rates, color=bar_colors, edgecolor="white", height=0.6)

    for bar, rate in zip(bars, rates):
        ax.text(bar.get_width() + 1, bar.get_y() + bar.get_height() / 2,
                f"{rate}%", va="center", fontsize=10, fontweight="bold")

    ax.set_xlim(0, 110)
    ax.set_xlabel("Pass Rate (%)", fontsize=12)
    ax.set_title("Eval Breakdown", fontsize=14, fontweight="bold")
    ax.invert_yaxis()
    ax.grid(axis="x", alpha=0.3)

    fig.tight_layout()
    fig.savefig(outpath, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  -> {outpath}")


# ---------------------------------------------------------------------------
# 4. 분기 탐색 요약 (full 모드)
# ---------------------------------------------------------------------------

def plot_branch_summary(results_json: dict, outpath: pathlib.Path):
    """full 모드의 분기 탐색 통계 바 차트 → PNG. results.json에 branch_stats 필요."""
    plt, ticker = _import_matplotlib()

    experiments = results_json.get("experiments", [])
    # branch_stats: {"candidates_generated": N, "candidates_executed": 1, "candidates_discarded_pre": M}
    has_branch = any(e.get("branch_stats") for e in experiments if e.get("status") != "baseline")

    if not has_branch:
        print("  -> branch_stats 데이터 없음 (light 모드 또는 데이터 미포함), 분기 요약 스킵.")
        return

    exp_ids = []
    generated = []
    pre_discarded = []
    for e in experiments:
        if e.get("status") == "baseline":
            continue
        bs = e.get("branch_stats", {})
        if bs:
            exp_ids.append(f"#{e['id']}")
            generated.append(bs.get("candidates_generated", 1))
            pre_discarded.append(bs.get("candidates_discarded_pre", 0))

    if not exp_ids:
        return

    fig, ax = plt.subplots(figsize=(max(6, len(exp_ids) * 0.8), 4))

    x_pos = range(len(exp_ids))
    bar_width = 0.35

    ax.bar([p - bar_width/2 for p in x_pos], generated, bar_width,
           label="Generated", color="#4A90D9", alpha=0.8)
    ax.bar([p + bar_width/2 for p in x_pos], pre_discarded, bar_width,
           label="Pre-reflection discard", color="#E74C3C", alpha=0.8)

    ax.set_xlabel("Experiment", fontsize=11)
    ax.set_ylabel("Candidates", fontsize=11)
    ax.set_title("Branch Exploration Summary (full mode)", fontsize=13, fontweight="bold")
    ax.set_xticks(list(x_pos))
    ax.set_xticklabels(exp_ids)
    ax.legend(fontsize=10)
    ax.grid(axis="y", alpha=0.3)

    fig.tight_layout()
    fig.savefig(outpath, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  -> {outpath}")


# ---------------------------------------------------------------------------
# 5. 마크다운 리포트
# ---------------------------------------------------------------------------

def generate_report(df, stats: dict, results_json: dict | None, outpath: pathlib.Path):
    """experiment_report.md 생성."""
    lines = [
        f"# Autoloop 결과 리포트",
        "",
        "## 점수 요약",
        "",
        f"| 항목 | 값 |",
        f"|------|-----|",
        f"| Baseline | {stats['baseline_score']}/{stats['max_score']} ({stats['baseline_pass_rate']}%) |",
        f"| Best | {stats['best_score']}/{stats['max_score']} ({stats['best_pass_rate']}%) — 실험 #{stats['best_experiment']} |",
        f"| 개선폭 | +{stats['improvement_pp']}pp |",
        f"| 실험 횟수 | {stats['total_experiments']} |",
        f"| Keep / Discard | {stats['keeps']} / {stats['discards']} (keep rate {stats['keep_rate']}%) |",
        f"| 평균 pass rate | {stats['mean_pass_rate']}% (std {stats['std_pass_rate']}%) |",
        "",
        "## 실험 이력",
        "",
        "| # | Score | Pass Rate | Status | Description |",
        "|---|-------|-----------|--------|-------------|",
    ]

    for _, row in df.iterrows():
        status_icon = {"baseline": "🔵", "keep": "🟢", "discard": "🔴"}.get(row["status"], "⚪")
        lines.append(
            f"| {int(row['experiment'])} | {int(row['score'])}/{int(row['max_score'])} | {row['pass_rate']}% | {status_icon} {row['status']} | {row['description']} |"
        )

    lines.append("")

    # eval breakdown (있으면)
    if results_json and results_json.get("eval_breakdown"):
        lines.extend([
            "## Eval별 분석",
            "",
            "| Eval | Pass | Total | Rate |",
            "|------|------|-------|------|",
        ])
        for e in results_json["eval_breakdown"]:
            rate = round(e["pass_count"] / e["total"] * 100, 1) if e["total"] > 0 else 0
            lines.append(f"| {e['name']} | {e['pass_count']} | {e['total']} | {rate}% |")
        lines.append("")

    lines.extend([
        "## 산출물",
        "",
        "- `score_trend.png` — 점수 추이 차트",
        "- `eval_heatmap.png` — eval별 pass rate (results.json 필요)",
        "- `branch_summary.png` — 분기 탐색 요약 (full 모드, results.json 필요)",
        "- `summary_stats.json` — 머신 리더블 통계",
    ])

    outpath.write_text("\n".join(lines), encoding="utf-8")
    print(f"  -> {outpath}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) < 2:
        print("사용법: python scripts/analyze_results.py <autoloop-dir>")
        print("예시:   python scripts/analyze_results.py autoloop-diagram-generator/")
        sys.exit(1)

    dirpath = pathlib.Path(sys.argv[1])
    if not dirpath.is_dir():
        print(f"ERROR: {dirpath} 디렉토리 없음.", file=sys.stderr)
        sys.exit(1)

    print(f"[autoloop analyze] 분석 대상: {dirpath}")

    # 로드
    df = load_results_tsv(dirpath)
    results_json = load_results_json(dirpath)
    print(f"  실험 {len(df)}건 로드.")

    # 통계
    stats = compute_stats(df)
    stats_path = dirpath / "summary_stats.json"
    with open(stats_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    print(f"  -> {stats_path}")

    # 시각화
    plot_score_trend(df, stats, dirpath / "score_trend.png")
    if results_json:
        plot_eval_heatmap(results_json, dirpath / "eval_heatmap.png")
        plot_branch_summary(results_json, dirpath / "branch_summary.png")

    # 리포트
    generate_report(df, stats, results_json, dirpath / "experiment_report.md")

    # 최종 요약 출력
    print(f"\n[결과 요약]")
    print(f"  Baseline: {stats['baseline_pass_rate']}% → Best: {stats['best_pass_rate']}% (+{stats['improvement_pp']}pp)")
    print(f"  Keep: {stats['keeps']}, Discard: {stats['discards']} (keep rate {stats['keep_rate']}%)")
    print(f"  산출물: summary_stats.json, score_trend.png, eval_heatmap.png, branch_summary.png, experiment_report.md")


if __name__ == "__main__":
    main()
