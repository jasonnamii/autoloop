---
name: autoloop
description: |
  스킬 자동최적화 루프. 실행→채점→변이 반복. α 연속체 모드. v6.1: 스킬빌더 핸드오프(handoff.json) 내장 — 완료 후 패키징 직행. 코워크 세션 네이티브, 세션 유실 백업, 볼트 오염 제거.
  P1: optimize, improve, autoloop, benchmark, eval, deep optimize, 스킬 최적화.
  P2: 돌려줘, 개선해줘, optimize this, run autoloop on, make better.
  P3: skill optimization, eval benchmark, mutation loop.
  P5: improved SKILL.md, results log, changelog.
  NOT: 프롬프트엔지니어링(→직접수행), 플러그인(→create-cowork-plugin), 스킬생성(→skill-builder), 패키징(→skill-builder).
---

# autoloop — 스킬 자동최적화 루프

에이전트가 반복 실행→채점→변이하며 30% 실패를 0%로 조여간다.

**v6.1: 스킬빌더 핸드오프.** step 7 추가 — 최적화 완료 후 handoff.json 생성 → 스킬빌더 패키징으로 자연 연결. v6.0 기반(코워크 세션 네이티브, 볼트 Read(in)+Write(out) 2회, changelog 백업). v5.0 기반(1후보+대안키워드, α 연속체 모드, 병렬 실행, 귀인 검증, 단계별 프로파일).

---

## 실행 환경 원칙

| 항목 | 위치 | 이유 |
|------|------|------|
| **실험장** | `/sessions/{session-id}/autoloop-lab/{skill-name}/` | 세션 = 샌드박스. git reset이 원본에 영향 없음 |
| **볼트 원본** | `mnt/.claude/skills/{skill-name}/` 또는 볼트 경로 | Read only. 실험 시작 시 1회 복사 |
| **최종 반영** | 볼트 원본 경로에 Write | 루프 종료 후 1회만 |
| **changelog 백업** | 볼트 `Agent-Ops/_autoloop-lab/{skill-name}/changelog.md` | 세션 유실 대비. 매 keep마다 백업 |

**절대 금지:** 볼트 안에서 git init/commit/reset 실행. 볼트는 지식 저장소지 실험실이 아니다.

---

## α 연속체 모드

모드는 **α(auto_scorable eval 수 / 전체 eval 수)**가 결정한다. 이산 모드명은 호환용 별칭.

| α 범위 | 호환명 | 실험 횟수 |
|--------|--------|----------|
| α = 1.0 | turbo | ~2회 |
| 0.5 ≤ α < 1.0 | light (기본) | ~3회 |
| α < 0.5 | full | ~5회 |

내용적 eval ≥50% → α < 0.5 → full 자동전환. auto_scorable 100% → α = 1.0 → turbo 권고.

α가 결정하는 분기: → [loop-mechanics.md](references/loop-mechanics.md) §α 분기표 참조

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

1. **대상 스킬** — 볼트 원본 SKILL.md 정확한 경로
2. **테스트 입력** — 3개의 서로 다른 프롬프트/시나리오 (기본값. 사용자 지정 시 변경)
3. **Eval 기준** — 3-6개 binary yes/no 체크. 각 eval에 `auto_scorable` 여부 표시. → [eval-guide.md](references/eval-guide.md) 참조 (이 시점에 로드)
4. **실험당 실행 횟수** — 기본값: 3
5. **α 판정** — auto_scorable eval 수 / 전체 eval 수 → 모드 자동 결정
6. **예산 상한** — 선택. 최대 실험 사이클 수
7. **실행 환경 확인** — 코워크 세션 내에서만 실행. `AUTOLOOP_LAB = /sessions/{session-id}/autoloop-lab/` (세션 로컬)

**왜 코워크 세션인가:**
- 스킬은 코워크 세션에서 사용된다. 실험도 같은 환경(MCP·UP·마운트)에서 돌아야 eval 결과가 실사용과 일치한다.
- 세션은 샌드박스이므로 `git reset --hard`가 볼트 원본을 오염시킬 수 없다.
- 실험 잔해(중간 변이, discard된 커밋)가 볼트에 쌓이지 않는다.

---

## step 1: 스킬 읽기

SKILL.md + references/ 읽기 → 핵심 작업·프로세스·출력 형식 파악 → 안티패턴 메모.

---

## step 2: eval 스위트 구성

→ [eval-guide.md](references/eval-guide.md) 참조 (step 0에서 미로드 시 이 시점에 로드)

모든 체크는 binary — pass 또는 fail. eval당 `auto_scorable` 표시 필수.

**α 산출:** auto_scorable=yes 수 / 전체 eval 수 → 모드 확정.

---

## step 3: baseline

### 세션 로컬 셋업

```
# 1. 볼트 원본을 세션 실험장으로 복사 (Read in — 1회)
AUTOLOOP_LAB=/sessions/{session-id}/autoloop-lab
mkdir -p $AUTOLOOP_LAB/{skill-name}
cp -r {볼트-skill-path}/ $AUTOLOOP_LAB/{skill-name}/

# 2. 세션 실험장에서 git 초기화
cd $AUTOLOOP_LAB/{skill-name}
git init && git add -A && git commit -m "baseline"
```

**볼트에는 git을 만들지 않는다.** 세션 로컬에서만 git을 사용한다.

### baseline 스킵 — 부분 재사용

| 조건 | 행동 |
|------|------|
| 이전 results.tsv 존재 + SKILL.md·eval·입력 **전부** 미변경 | 마지막 점수를 baseline으로 재사용. N회 실행 절약 |
| eval 또는 입력 **일부만** 변경 | 변경되지 않은 eval×입력 조합은 이전 점수 재사용, 변경된 조합만 재실행 |
| SKILL.md 변경 | 전체 재실행 (기준 자체가 달라짐) |

**세션 간 재사용:** 이전 세션의 changelog 백업이 볼트에 있으면(`Agent-Ops/_autoloop-lab/{skill-name}/changelog.md`), 어디까지 진행했는지 확인하고 이어서 진행 가능. 단, SKILL.md가 변경됐으면 전체 재실행.

### baseline 실행

1. **실행 모드 판정:** 독립 실행 가능 → **실행** (Agent로 로드+실행). 외부 의존성 → **시뮬레이션**.
2. 스킬 [N]번 실행+채점 → baseline 점수 기록 → results.tsv
3. **단계별 프로파일 기록** — 각 실행에서 step_profile 캡처 → timing.json에 저장. → [schemas.md](references/schemas.md) §step_profile 참조 (이 시점에 로드)
4. 90%+면 사용자에게 계속할지 확인.

---

## step 4: 실험 루프

autoloop의 핵심. 시작하면 멈출 때까지 자율 실행한다.

### 루프 구조 (v5.0)

```
4a. 실패 분해 (+ 이전 판정 이유 흡수 + 프로파일 병목 확인)
4b. 변이 생성 — 1후보 집중형 (대안키워드 저축)
4c. 실행+채점 — 병렬 가능 시 병렬, 불가 시 순차
4d. keep/discard + git commit/reset + 프로파일 기록 + changelog 백업
4e. 정체 시 RAR + 귀인 검증
```

각 메커니즘 상세: → [loop-mechanics.md](references/loop-mechanics.md) 참조 (step 4 진입 시 로드)

### 4a: 실패 분해

eval×input 매트릭스 + 이전 판정 이유 흡수. **v5.0 추가:** step_profile에서 토큰·시간 병목 확인 → 다음 변이 우선순위에 반영.

| α | 분석 깊이 |
|---|----------|
| = 1.0 | 매트릭스 자동 (코드) |
| ≥ 0.5 | 매트릭스 + 수동 분석 |
| < 0.5 | + grep 수치화 |

### 4b: 변이 생성 — 1후보 집중형 (v5.0)

**모든 α에서 후보 1개.** 탐색 폭은 대안키워드가 changelog→RAR 경로로 보존.

```
실패: [E{N}] {eval 이름} — {실패 증상 1문장}
이전: {판정 이유 1문장}

이 실패를 해결하는 변이 1개를 제안하라.
- 변경: [어디를 어떻게]
- 약점: [이 변이가 실패할 수 있는 이유 1개]  ← α=1.0이면 생략
- 대안 키워드 2개 (미실행 후보 복원용)       ← changelog에 저장
```

변이 내용 채우기: → [trigger-principles.md](references/trigger-principles.md) 참조 (4b 최초 진입 시 로드)

한 번에 한 가지(1 eval 타겟, 1 가설). 형식 실패→형식 먼저. 2회 discard→내용으로 전환. changelog에 "타겟: E[N], 가설: [1문장], 대안: [키워드1, 키워드2]" 기록.

### 4c: 실행+채점 — 병렬 옵션 (v5.0)

| 조건 | 실행 방식 |
|------|----------|
| 병렬 Agent 지원 | N회 실행을 동시 spawn → auto_scorable 즉시 코드 채점 → 내용적만 LLM |
| 순차 폴백 | 실행+채점 합침 (v4.0 방식 유지) |

| eval 유형 | 채점 방식 |
|-----------|----------|
| auto_scorable=yes | 코드 자동 채점. LLM 0 |
| 형식적 + auto_scorable=no | 실행+채점 합침 1회 |
| 내용적 (α < 0.5만) | 실행 Agent 1회 + 별도 Agent 2회 (다수결) |

**Scorer 앵커링:** eval 프리앰블 복사 / Agent 격리 / drift 감지(3실험 연속 2:1→재작성) / auto_scorable→코드 필수.

### 4d: keep/discard + 프로파일 + 백업

- **keep:** `git commit -m "exp-{N}: keep — E{target} — {가설}"` + step_profile 기록 + **changelog 백업** (→ step 5 참조)
- **discard:** `git reset --hard HEAD~1` + step_profile 기록
- **판정 이유:** changelog에 1문장 + 대안키워드 → 다음 4a 입력

### 4e: RAR + 귀인 검증 (v5.0)

3회 연속 discard 시 **2단계 진단**. → [loop-mechanics.md](references/loop-mechanics.md) §8 상세 참조

```
① 귀인 검증: 지목 구간→원본 복원+재실행. 점수 무변화→귀인 틀림→매트릭스 재분석
② RAR: changelog→시도/미시도 매트릭스. 대안키워드 미시도 우선. keep 패턴 추출
```

**Scorer 노이즈:** α < 1.0일 때만 추적. 3실험 연속 일치도 < 80% → 정지 + eval 재설계.

### 자동 종료 조건

- 사용자가 수동 중지
- 예산 상한 도달
- 3회 연속 95%+ pass rate

**절대 멈추지 마라.** 루프가 시작되면 사용자에게 계속할지 물으며 일시정지하지 않는다.

---

## step 5: changelog 작성 + 백업

매 실험 후 `changelog.md`에:

```
## Exp [N] — [keep/discard]
점수: [pass/total]
변경: [1문장]
판정 이유: [1문장]
대안 키워드: [kw1, kw2]
프로파일: 4b=[tokens]t, 4c=[tokens]t [duration]ms
```

**세션 유실 대비 백업 (매 keep마다):**

```bash
# 볼트 백업 경로 (DC 또는 Cowork Write)
BACKUP_PATH="Agent-Ops/_autoloop-lab/{skill-name}"
# changelog.md + results.tsv를 볼트에 백업
# → 다음 세션에서 이어서 진행 가능
```

백업 대상: `changelog.md`, `results.tsv`. SKILL.md 중간 변이는 백업하지 않는다 (git이 관리). discard 시에는 백업하지 않는다 (낭비).

---

## step 6: 결과 전달 + 볼트 반영

→ [schemas.md](references/schemas.md) 참조 (이 시점에 로드)

### 결과 보고

루프 종료 시: ①점수 요약(Baseline→최종) ②실험 횟수+Keep율 ③효과적 변경 Top 3 ④남은 실패 ⑤git log ⑥프로파일 요약(병목 단계+총 토큰).

15회↑ → `python scripts/analyze_results.py autoloop-lab/{skill-name}/`.

### 볼트 반영 (Write out — 1회)

```
# 최종 개선된 SKILL.md + references/를 볼트 원본 경로에 Write
# Cowork Write 또는 DC Write 사용. MCP(obsidian) write 사용 금지 (UP §OBSIDIAN).
```

**반영 전 확인:** ①Before/After diff를 사용자에게 보여준다 ②사용자 승인 후 Write. 자동 반영하지 않는다.

---

## step 7: 패키징 대기 (handoff-ready)

볼트 반영 승인 완료 후, 스킬빌더로의 핸드오프를 준비한다. 세션 실험장을 삭제하지 않는다.

### 7a: handoff.json 생성

세션 실험장 루트에 `handoff.json` 생성. → [schemas.md](references/schemas.md) §handoff.json 참조

```bash
# 세션 실험장에 handoff.json 생성
cat > $AUTOLOOP_LAB/{skill-name}/handoff.json << 'EOF'
{
  "skill_name": "{skill-name}",
  "session_path": "$AUTOLOOP_LAB/{skill-name}/",
  "baseline_score": {baseline},
  "final_score": {final},
  "kept_mutations": {N},
  "total_experiments": {N},
  "top_changes": [...],  // changelog에서 keep 변이 Top 3
  "remaining_failures": [...],
  "ready_for": "skill-builder"
}
EOF
```

### 7b: 볼트 백업

```bash
# changelog, results.tsv와 함께 handoff.json도 볼트에 백업
BACKUP_PATH="Agent-Ops/_autoloop-lab/{skill-name}"
# handoff.json → 볼트 백업 (DC 또는 Cowork Write)
```

### 7c: 스킬빌더 제안

사용자에게 1줄 제안: **"스킬빌더로 패키징할까요?"**

- 형이 "응" → `Skill tool`로 skill-builder 발동. 스킬빌더가 handoff.json을 감지하여 세션 실험장에서 직접 ②-b → ③ 진행.
- 형이 "아니" → 종료. handoff.json은 볼트 백업에 남아 다음 세션에서 사용 가능.

**왜 step 7인가:** 오토루프는 최적화 전문, 패키징은 스킬빌더 전문. 오토루프가 패키징까지 하면 책임 경계가 모호해진다. handoff.json이 두 스킬의 계약(contract)이다.

---

## 속도 (v4.0 → v5.0)

| 모드 | v4.0 호출/실험 | v5.0 호출/실험 | 개선 |
|------|--------------|--------------|------|
| turbo (α=1.0) | ~2 | ~2 | — |
| light (α≥0.5) | ~4 | ~3 | -25% |
| full (α<0.5) | ~8 | ~5 | -37% |

추가: 초기 로드 -70%, 4b 토큰 -60%, baseline -80% (조건부).

---

## 완성도 체크

baseline / binary eval / auto_scorable 표시 / α 판정 / 한 변이씩 / keep·discard 기록 / 대안키워드 / 자율 실행 / eval×input 매트릭스 / 프로파일 기록 / git(세션 로컬) / changelog 백업(매 keep) / 볼트 반영(사용자 승인 후) / **handoff.json 생성 + 스킬빌더 제안**. eval 통과 but 품질 안 올랐다면 → eval이 나쁨. step 2로.

---

## Gotchas

- **볼트에서 git 금지:** 실험은 세션 로컬에서만. 볼트에 git init/commit/reset 절대 실행하지 않는다.
- **세션 유실:** 매 keep마다 changelog+results.tsv를 볼트에 백업. 다음 세션에서 이어서 가능. SKILL.md 중간 변이는 유실될 수 있으나, changelog에서 재현 가능.
- **뺑뺑이:** 3회 연속 discard 시 반드시 귀인 검증 먼저. RAR 직행 금지.
- **병목 무시:** 프로파일 없이 최적화 대상 선정하면 감에 의존. 4c가 80%인데 4b를 줄여도 효과 미미.
- **full 비용 폭발:** 내용적 eval 3개 이하로 시작.
- **RAR:** 3회 연속 discard가 적정. 2회에 발동하면 미시도 변이를 건너뜀.
- **내용적 eval 노이즈:** 매 실험 2:1 분할되는 eval → 모호하다. 재작성.
- **시뮬레이션 과신:** 실행 가능한 스킬은 실행 모드 필수.
- **동일 컨텍스트 채점:** α < 0.5에서 내용적 3회 채점은 반드시 별도 Agent.
- **복합 변이:** 다른 eval 타겟하는 복수 변경 금지.
- **auto_scorable 오판:** grep/regex로 판정 불가능하면 무조건 no.
- **git reset 범위:** `HEAD~1`만. 2회 연속 discard는 각각 reset.
- **baseline 부분 재사용:** SKILL.md 변경 시 스킵 불가. 기준 자체가 달라짐.
- **대안키워드 누적:** changelog에 대안키워드가 10개+ 미시도 시 RAR에서 우선 소화.
- **볼트 반영 자동화 금지:** step 6에서 반드시 사용자 승인 후 Write. 자동 반영 = 원본 오염 리스크.
- **handoff.json 누락:** step 7을 건너뛰면 스킬빌더가 skills-plugin에서 구버전을 복사한다. 오토루프 종료 시 반드시 handoff.json 생성.
- **세션 실험장 조기 삭제:** handoff.json이 있어도 실험장이 없으면 스킬빌더가 읽을 수 없다. step 7 이후 실험장 삭제 금지.
