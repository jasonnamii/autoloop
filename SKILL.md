---
name: autoloop
description: |
  스킬 자동최적화 루프. 실행→채점→변이 반복. α 연속체 모드. v6.4: 라이브 HTML 대시보드 + 변이 가드 4종 + RAR 탈출구 4갈래.
    P1: optimize, improve, autoloop, benchmark, eval, deep optimize, 스킬 최적화, dashboard, 대시보드, 오토루프, 자동최적화, 스킬개선, 스킬벤치마크, 스킬평가, 반복최적화, 루프최적화, 뮤테이션, 변이최적화, 스킬루프, 최적화루프, autoloop 돌려, 스킬 돌려.
    P2: 돌려줘, 개선해줘, optimize this, run autoloop on, make better, 최적화해줘, 스킬 개선해줘, 벤치마크해줘, eval 돌려줘.
    P3: skill optimization, eval benchmark, mutation loop, live dashboard, automated skill improvement, iterative optimization.
    P4: 스킬 성능 개선이 필요할 때, 반복 최적화가 필요할 때, 스킬 벤치마킹할 때.
    P5: improved SKILL.md, results log, changelog, dashboard.html.
    NOT: 프롬프트엔지니어링(→직접수행), 플러그인(→cowork-plugin-management:create-cowork-plugin), 스킬생성(→skill-builder), 패키징(→skill-builder).
vault_dependency: HARD
---

# autoloop — 스킬 자동최적화 루프

에이전트가 반복 실행→채점→변이하며 실패를 조여간다. **benchmark → optimize → improve** 1턴 루프로 스킬을 성장시킨다.

**v6.4:** 라이브 HTML 대시보드(autoresearch venom #1) + 변이 가드 4종(#2) + RAR 탈출구 4갈래(#3) + eval 모범 차분 머지(#4). 세션 자리 비워도 브라우저로 진행 추적. `references/dashboard-template.html`·`scripts/gen_dashboard.py` 신설. 기능 로직 무변경 — 가시성·가드만 강화.

**v6.3:** 허브 슬림화. step 0~7 상세는 `references/execution-steps.md`로 분리, 허브에는 절대 규칙·분기·포인터만 유지. `evals/cases.json`·`scripts/self_check.py`·`CHANGELOG.md` 신설.

---

## ⛔ 절대 규칙 (5개)

| # | 규칙 | 이유 |
|---|------|------|
| 1 | **볼트 안에서 git init/commit/reset 금지** — 실험장은 세션 로컬(`/sessions/{id}/autoloop-lab/`)에서만 | 볼트는 지식 저장소. git 아카이브가 원본 오염시킴 |
| 2 | **볼트 반영은 사용자 승인 후 1회만** — Before/After diff를 보여주고 Write. 자동 반영 = FAIL | 사용자가 검증 없이 실파일 덮어씌움 방지 |
| 3 | **한 변이 = 한 eval 타겟 = 한 가설** — 복합 변이는 귀인 불가 | keep/discard 판정이 귀인 가능해야 함 |
| 4 | **handoff.json 생성 + 세션 실험장 유지** (step 7) | 스킬빌더가 실험장에서 직접 패키징. 실험장 삭제 시 구버전 복사됨 |
| 5 | **auto_scorable=no인 내용적 eval은 별도 Agent로 다수결 채점** (α<0.5) | 동일 컨텍스트 채점은 scorer drift 발생 |
| 6 | **변이 가드 4종 — bad mutation 즉시 폐기** — ①전체 재작성 ②다중룰 동시추가(2개+) ③길이 팽창만(가설 없는 추가) ④모호 지시("더 잘", "be creative") | 귀인 불가 + eval 게이밍 위험. → [loop-mechanics.md §변이 가드](references/loop-mechanics.md) |
| 7 | **라이브 대시보드 step 3-bis 강제** — baseline 생성 직후 `dashboard.html`·`results.json` 생성 + 가능 시 `open dashboard.html`. 미생성 = FAIL | 자리 비워도 진행 시각 추적. results.tsv만으론 형이 못 봄 |

---

## 실행 환경 원칙

| 항목 | 위치 | 이유 |
|------|------|------|
| 실험장 | `/sessions/{session-id}/autoloop-lab/{skill-name}/` | 세션 = 샌드박스. git reset이 원본 무영향 |
| 볼트 원본 | `mnt/.claude/skills/{skill-name}/` 또는 볼트 경로 | Read only. 실험 시작 시 1회 복사 |
| 최종 반영 | 볼트 원본 경로에 Write | 루프 종료 후 1회만 |
| changelog 백업 | 볼트 `Agent-Ops/_autoloop-lab/{skill-name}/changelog.md` | 세션 유실 대비. 매 keep마다 백업 |

---

## α 연속체 모드

모드는 **α(auto_scorable eval 수 / 전체 eval 수)**가 결정한다. 이산 모드명은 호환용 별칭.

| α 범위 | 호환명 | 실험 횟수 | 하드캡(예산 미지정) |
|--------|--------|----------|---------------------|
| α = 1.0 | turbo | ~2회 | 6회 |
| 0.5 ≤ α < 1.0 | light (기본) | ~3회 | 9회 |
| α < 0.5 | full | ~5회 | 15회 |

내용적 eval ≥50% → α < 0.5 → full 자동전환. auto_scorable 100% → α = 1.0 → turbo 권고.

α가 결정하는 분기표: → [loop-mechanics.md](references/loop-mechanics.md) §α 분기표

---

## 핵심 작업

1. 테스트 입력으로 스킬 출력 생성 (benchmark)
2. 모든 출력을 eval 기준으로 채점
3. 실패 분석 + 스킬 프롬프트 변이 (improve)
4. 점수 오른 변이만 유지, 나머지 폐기 (optimize)
5. 한계 도달 또는 사용자 중지까지 반복
6. 스킬빌더 패키징으로 핸드오프

**산출물:** 개선된 SKILL.md + `results.tsv` + `changelog.md` + `handoff.json`.

---

## 실행 단계 개요

상세 프로토콜: → [execution-steps.md](references/execution-steps.md)

| step | 이름 | 핵심 |
|------|------|------|
| 0 | 맥락 수집 | 대상·입력·eval·예산·α 판정 확인 전까지 STOP |
| 1 | 스킬 읽기 + reference 1회 캐싱 | 루프 중 재로딩 금지 (토큰 ~30% 절감) |
| 2 | eval 스위트 구성 | binary yes/no + `auto_scorable` 표시 → α 산출 |
| 3 | baseline | 세션 로컬 git init + N회 실행 + 프로파일 |
| **3-bis** | **라이브 대시보드 생성** | `python scripts/gen_dashboard.py` → `dashboard.html`·`results.json` → 가능 시 `open` |
| 4 | 실험 루프 | 4a 실패분해 → 4b 변이(가드 4종) → 4c 실행채점(병렬) → 4d keep/discard + JSON 갱신 → 4e RAR+귀인 |
| 5 | changelog 작성 + 백업 | 매 keep마다 볼트 백업 |
| 6 | 결과 전달 + 볼트 반영 | Before/After diff → 사용자 승인 → Write |
| 7 | 패키징 대기 (handoff-ready) | handoff.json 생성 → "스킬빌더로 패키징할까요?" |

**자동 종료:** 사용자 중지 / 예산 상한 / 3회 연속 95%+ pass rate / iteration 하드캡 도달.

**절대 멈추지 마라.** 루프 시작 후 사용자에게 계속할지 물으며 일시정지하지 않는다. 단, 하드캡 도달은 멈춤이 아니라 완료다.

---

## 속도 기준

| 모드 | 호출/실험 |
|------|----------|
| turbo (α=1.0) | ~2 |
| light (α≥0.5) | ~3 |
| full (α<0.5) | ~5 |

---

## 완성도 체크

baseline / binary eval / auto_scorable 표시 / α 판정 / 한 변이씩 / keep·discard 기록 / 대안키워드 / 자율 실행 / eval×input 매트릭스 / 프로파일 기록 / git(세션 로컬) / changelog 백업(매 keep) / 볼트 반영(사용자 승인 후) / **handoff.json 생성 + 스킬빌더 제안**.

eval 통과 but 품질 안 올랐다면 → eval이 나쁨. step 2로 회귀.

---

## 자체 점검 (self-check)

스킬 자체의 invariant 점검:

```bash
python scripts/self_check.py /sessions/{session-id}/mnt/.claude/skills/autoloop/
# exit 0 = PASS · exit 1 = FAIL + JSON 리포트
```

점검 항목: ①SKILL.md ≤10KB(5KB 목표) ②핵심 스포크 5개 존재 ③`evals/cases.json` 유효·case id 중복 없음 ④P1 키워드 ≥5 ⑤NOT·Gotchas·절대 규칙 섹션 존재. 수정 후 필수 실행.

---

## Gotchas

- **뺑뺑이:** 3회 연속 discard 시 반드시 귀인 검증 먼저. RAR 직행 금지.
- **아이디어 고갈 → 4갈래 탈출구** (RAR 후에도 막히면): ①실패 출력 재읽기(원본 텍스트 복귀) ②near-miss 두 변이 결합 ③제거 방향 변이(추가 대신 삭제) ④단순화도 keep — 점수 유지하면서 줄였다면 win. → [loop-mechanics.md §탈출구](references/loop-mechanics.md)
- **bad mutation 4종 즉시 폐기:** 전체 재작성·다중룰 동시추가·길이 팽창만·모호 지시 — 절대 규칙 #6에 의거 실험 전 자체 차단.
- **병목 무시:** 프로파일 없이 최적화 대상 선정하면 감에 의존. 4c가 80%인데 4b를 줄여도 효과 미미.
- **full 비용 폭발:** 내용적 eval 3개 이하로 시작.
- **RAR:** 3회 연속 discard가 적정. 2회에 발동하면 미시도 변이를 건너뜀.
- **내용적 eval 노이즈:** 매 실험 2:1 분할되는 eval → 모호하다. 재작성.
- **시뮬레이션 과신:** 실행 가능한 스킬은 실행 모드 필수.
- **동일 컨텍스트 채점:** α<0.5에서 내용적 3회 채점은 반드시 별도 Agent.
- **복합 변이:** 다른 eval 타겟하는 복수 변경 금지.
- **auto_scorable 오판:** grep/regex로 판정 불가능하면 무조건 no.
- **git reset 범위:** `HEAD~1`만. 2회 연속 discard는 각각 reset.
- **대안키워드 누적:** changelog에 대안키워드 10개+ 미시도 시 RAR에서 우선 소화.
- **handoff.json 누락:** step 7 건너뛰면 스킬빌더가 skills-plugin에서 구버전을 복사한다. 루프 종료 시 반드시 생성.
- **세션 실험장 조기 삭제:** handoff.json이 있어도 실험장이 없으면 스킬빌더가 읽을 수 없다. step 7 이후 삭제 금지.
- **대시보드 미생성:** step 3-bis 스킵 시 형이 진행 상황을 모른다. baseline 직후 무조건 생성. 코워크 환경에서 `open` 미동작 시 파일 경로만 안내해도 OK(파일 자체는 생성 필수).
- **results.json 미갱신:** 매 4d 직후 `gen_dashboard.py --update` 호출 누락하면 대시보드가 멈춰있는 것처럼 보임. keep/discard 기록과 동시에 JSON도 갱신.
