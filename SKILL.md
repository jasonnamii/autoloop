---
name: autoloop
description: |
  스킬 자동최적화 루프. 실행→채점→변이 반복. full/light/turbo 3모드. v4.0: 속도2배(실행+채점합침, 코드자동채점, 단일프롬프트변이, git).
  P1: optimize, improve, autoloop, benchmark, eval, deep optimize, 스킬 최적화.
  P2: 돌려줘, 개선해줘, optimize this, run autoloop on, make better.
  P3: skill optimization, eval benchmark, mutation loop.
  P5: improved SKILL.md, results log, changelog.
  NOT: 프롬프트엔지니어링(→직접수행), 플러그인(→create-cowork-plugin), 스킬생성(→skill-builder).
"@uses":
  - references/loop-mechanics.md
  - references/trigger-principles.md
  - references/eval-guide.md
  - references/schemas.md
---

# autoloop — 스킬 자동최적화 4축 루프

에이전트가 반복 실행→채점→변이하며 30% 실패를 0%로 조여간다.

**v4.0: Speed × 2.** 실행+채점 합침, 코드 자동채점, 단일 프롬프트 변이, git 버전관리.

| 모드 | 대상 | LLM/실험 |
|------|------|---------|
| **full** | 내용적 스킬 (분석, 기획) | ~8회 |
| **light** (기본) | 형식적 스킬 (코드, 포맷) | ~4회 |
| **turbo** | auto_scorable 100% | ~2회 |

내용적 eval ≥50% → full 자동전환. auto_scorable 100% → turbo 권고.

---

## 핵심 작업

1. 테스트 입력으로 스킬 출력 생성
2. 모든 출력을 eval 기준으로 채점
3. 실패를 분석하고 스킬 프롬프트를 변이
4. 점수가 오른 변이만 유지, 나머지 폐기
5. 한계에 도달하거나 사용자가 멈출 때까지 반복

**산출물:** 개선된 SKILL.md + `results.tsv` + `changelog.md`.

---

## step 0: 맥락 수집

**멈춰라. 아래 항목이 모두 확인되기 전까지 실험을 시작하지 마라.**

1. **대상 스킬** — SKILL.md 정확한 경로
2. **테스트 입력** — 3개의 서로 다른 프롬프트/시나리오 (기본값. 사용자 지정 시 변경)
3. **Eval 기준** — 3-6개 binary yes/no 체크. 각 eval에 `auto_scorable` 여부 표시. 작성법은 [eval-guide.md](references/eval-guide.md) 참조
4. **실험당 실행 횟수** — 기본값: 3 (v3.1의 5에서 축소. 이유: 실행+채점 합침으로 신호 품질 유지하면서 호출 수 절감)
5. **모드** — `full`, `light`, 또는 `turbo`. 기본값: light
6. **예산 상한** — 선택. 최대 실험 사이클 수
7. **git repo** — autoloop-lab 경로 확인 (없으면 생략, 파일 기반 폴백)

---

## step 1: 스킬 읽기

1. SKILL.md 전체 읽기
2. `references/`에 연결된 파일 읽기
3. 핵심 작업, 프로세스 단계, 출력 형식 파악
4. 기존 품질 체크나 안티패턴 메모

---

## step 2: eval 스위트 구성

모든 체크는 binary — pass 또는 fail. 척도는 변동성을 증폭시키고 신뢰할 수 없는 결과를 낸다.

```
EVAL [번호]: [짧은 이름]
질문: [출력에 대한 yes/no 질문]
Pass 조건: ["yes"가 어떤 모습인지]
Fail 조건: ["no"를 유발하는 것]
유형: [형식적/내용적]
auto_scorable: [yes/no] — grep/regex/wc 등 코드로 판정 가능 여부
auto_script: [판정 코드 1줄] — auto_scorable=yes일 때만. 예: `wc -w < output.txt | awk '{print ($1 >= 150 && $1 <= 400)}'`
```

`auto_scorable=yes`: grep/wc/regex로 판정 가능 (단어수, 문자열 포함, 섹션 존재). `no`: LLM 판단 필요 (분석 깊이, 논리, 다관점). 상세는 [eval-guide.md](references/eval-guide.md) 참조.

**모드 자동 판정:** 내용적 ≥50% → full. 형식적 100% + auto_scorable 100% → turbo.

---

## step 3: baseline

### git (autoloop-lab 존재 시)

`cp -r {skill-path}/ autoloop-lab/{skill-name}/` → `git checkout -b autoloop/{skill-name}` → `git commit -m "baseline"`. 없으면 파일 폴백 (`autoloop-[skill-name]/` + `SKILL.md.baseline`).

### baseline 스킵 (v4.0)

이전 results.tsv가 존재 + SKILL.md 미변경 + eval/입력 미변경 → 마지막 점수를 baseline으로 재사용. N회 실행 절약.

### baseline 실행

1. **실행 모드 판정:** 독립 실행 가능 → **실행** (Agent로 로드+실행). 외부 의존성 → **시뮬레이션** (지시문 강제력 판정). 실행 가능하면 실행 필수.
2. 스킬 [N]번 실행+채점 합침 → baseline 점수 기록 → results.tsv
3. 90%+면 사용자에게 계속할지 확인.

---

## step 4: 실험 루프

autoloop의 핵심. 시작하면 멈출 때까지 자율 실행한다.

### 루프 구조 (v4.0)

```
4a. 실패 분해 (+ 이전 실험 점수 원인 흡수)
4b. 변이 생성+선택 — 단일 프롬프트 (full: 후보+약점+반론+선택 / light: 1개+약점)
4c. 실행+채점 — 합침 (auto_scorable은 코드, 내용적만 LLM)
4d. keep/discard + git commit/reset
4e. 정체 시 RAR
```

각 메커니즘의 상세 원리는 [loop-mechanics.md](references/loop-mechanics.md) 참조.

### 실행+채점 합침 (v4.0)

v3.1: 실행 N회 + 채점 1회 = N+1. **v4.0: 실행+채점을 1회 호출로 합침 = N.**

- **auto_scorable eval:** 출력 파일 → bash/python 즉시 채점. LLM 0.
- **내용적 eval:** 실행 Agent 프롬프트에 eval 기준 포함. 실행+채점 1호출.
- **full 내용적:** 실행 Agent 1회 + 별도 Agent 2회 (다수결) = 3회.
- **turbo:** 전부 코드 채점. 실행 N회 + 채점 코드 = LLM N호출.

상세는 [loop-mechanics.md](references/loop-mechanics.md) §3 참조.

### 4a~4e 요약

| 단계 | 행동 | turbo | light | full |
|------|------|-------|-------|------|
| **4a. 실패 분해** | eval×input 매트릭스 + 이전 실험 점수 원인 흡수 | 매트릭스 자동 | 매트릭스 + 수동 분석 | + grep 수치화 |
| **4b. 변이 생성+선택** | **단일 프롬프트**로 합침 (v4.0) | 1개, 약점 생략 | 1개 + 약점 1문장 | "후보 3개 + 각 약점 + 반론 + 최유력 선택" = 1호출 |
| **4c. 실행+채점** | **합침** (v4.0) | N회 실행 + 코드 채점 | N회 (실행+채점 합침) | N회 합침 + 내용적 eval 추가 2회 Agent |
| **4d. keep/discard** | 점수↑=keep, 동일/↓=discard + git commit/reset | 판정만 | 판정만 | 판정만 (post-reflection → 다음 4a에 흡수) |
| **4e. RAR** | 3회 연속 discard 시 changelog 재분석 | 요약 1회 | 요약 1회 | 매트릭스+패턴 추출 |

### 4b 상세: 단일 프롬프트 변이 (v4.0)

v3.1 full: 후보(1) + pre-reflection(1) + debate(1) = 3호출. **v4.0 full: 1호출.**

단일 프롬프트에 "후보 3개 + 각 약점 + 각 반론 + 최유력 선택"을 포함. light: 후보 1개 + 약점 1문장. turbo: 후보 1개만. 상세는 [loop-mechanics.md](references/loop-mechanics.md) §1, §4 참조.

### 4d: keep/discard + git

- **keep:** `git commit -m "exp-{N}: keep — E{target} — {가설}"` (git 미사용: 파일 유지)
- **discard:** `git reset --hard HEAD~1` (git 미사용: baseline에서 복원)
- **판정 이유:** changelog에 1문장 기록 → 다음 4a에 입력 (v3.1의 post-reflection 흡수)

### Scorer 앵커링 (4c)

| 규칙 | 내용 |
|------|------|
| **eval 프리앰블** | 채점 프롬프트 첫 줄에 eval 정의 그대로 복사 |
| **Agent 격리** | full 내용적 eval 3회 채점은 별도 Agent. 동일 컨텍스트 반복 금지 |
| **drift 감지** | 같은 eval 3실험 연속 2:1 → 해당 eval 정지 + 재작성 |
| **auto_scorable 우선** | 코드 채점 가능한 eval은 코드 필수. LLM 금지 |

### 변이 규칙

한 번에 한 가지(1 eval 타겟, 1 가설). 형식 실패→형식 먼저. 2회 discard→내용으로 전환. 내용 변이는 [trigger-principles.md](references/trigger-principles.md)에서 원리 추출→1-2문장 주입. changelog에 "타겟: E[N], 가설: [1문장]" 기록. turbo 예외: 형식적 eval 2개까지 동시 허용 (코드 채점으로 효과 분리 가능).

### 자동 종료 조건

- 사용자가 수동 중지
- 예산 상한 도달
- 3회 연속 95%+ pass rate

**절대 멈추지 마라.** 루프가 시작되면 사용자에게 계속할지 물으며 일시정지하지 않는다.

---

## step 5: changelog 작성

매 실험 후 `changelog.md`에: `## Exp [N] — [keep/discard]` + 점수 + 변경 1문장 + 판정 이유 1문장 (→다음 4a 입력). full은 추가로: 근거, 선택/미실행 후보.

---

## step 6: 결과 전달

루프 종료 시: ①점수 요약(Baseline→최종) ②실험 횟수+Keep율 ③효과적 변경 Top 3 ④남은 실패 ⑤개선된 SKILL.md 위치 ⑥git log (사용 시).

15회↑ → `python scripts/analyze_results.py autoloop-[skill-name]/`.

---

## 출력 형식

git: `autoloop-lab/{skill-name}/` (SKILL.md + results.tsv + changelog.md)
폴백: `autoloop-[skill-name]/` (+ SKILL.md.baseline)

---

## 속도 (v3.1 → v4.0)

| 모드 | v3.1 | v4.0 | 개선 |
|------|------|------|------|
| light | 7~8회 | ~4회 | -50% |
| full | 14~17회 | ~8회 | -53% |
| turbo | — | ~2회 | 신규 |

---

## 완성도 체크

baseline / binary eval / auto_scorable 표시 / 한 변이씩 / keep·discard 기록 / 자율 실행 / eval×input 매트릭스 / git(사용 시). eval 통과 but 품질 안 올랐다면 → eval이 나쁨. step 2로.

---

## Gotchas

- **full 비용 폭발:** 내용적 eval 3개 이하, 후보 2개로 시작.
- **pre-reflection 과잉:** "치명적 약점"만 필터. 사소한 우려는 실행해봐야 안다.
- **RAR:** 3회 연속 discard가 적정. 2회에 발동하면 미시도 변이를 건너뜀.
- **내용적 eval 노이즈:** 매 실험 2:1 분할되는 eval → 모호하다. 재작성.
- **시뮬레이션 과신:** 실행 가능한 스킬은 실행 모드 필수.
- **동일 컨텍스트 채점:** full 3회 채점은 반드시 별도 Agent. 편향 복제 방지.
- **복합 변이:** 다른 eval 타겟하는 복수 변경 금지. turbo도 형식적 2개까지.
- **auto_scorable 오판:** grep/regex로 판정 불가능하면 무조건 no.
- **git reset 범위:** `HEAD~1`만. 2회 연속 discard는 각각 reset.
- **baseline 스킵:** eval/입력 변경 시 스킵 불가. 기준 자체가 달라짐.
