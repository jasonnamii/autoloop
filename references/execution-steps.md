# execution-steps — autoloop 실행 단계 상세

허브(SKILL.md)의 step 0~7 상세 프로토콜. 허브는 분기·규칙·포인터만 유지하고 본 문서가 각 단계의 실행 세부를 담는다.

---

## step 0: 맥락 수집

**멈춰라. 아래 항목이 모두 확인되기 전까지 실험을 시작하지 마라.**

1. **대상 스킬** — 볼트 원본 SKILL.md 정확한 경로
2. **테스트 입력** — 3개의 서로 다른 프롬프트/시나리오 (기본값. 사용자 지정 시 변경)
3. **Eval 기준** — 3-6개 binary yes/no 체크. 각 eval에 `auto_scorable` 여부 표시. → [eval-guide.md](eval-guide.md) 참조 (이 시점에 로드)
4. **실험당 실행 횟수** — 기본값: 3
5. **α 판정** — auto_scorable eval 수 / 전체 eval 수 → 모드 자동 결정
6. **예산 상한** — 선택. 최대 실험 사이클 수
7. **실행 환경 확인** — 코워크 세션 내에서만 실행. `AUTOLOOP_LAB = /sessions/{session-id}/autoloop-lab/` (세션 로컬)

**왜 코워크 세션인가:**
- 스킬은 코워크 세션에서 사용된다. 실험도 같은 환경(MCP·UP·마운트)에서 돌아야 eval 결과가 실사용과 일치한다.
- 세션은 샌드박스이므로 `git reset --hard`가 볼트 원본을 오염시킬 수 없다.
- 실험 잔해(중간 변이, discard된 커밋)가 볼트에 쌓이지 않는다.

---

## step 1: 스킬 읽기 + reference 캐싱

SKILL.md + references/ 읽기 → 핵심 작업·프로세스·출력 형식 파악 → 안티패턴 메모.

**reference 1회 캐싱:** step 1에서 이 스킬의 references/ 4파일(eval-guide.md, loop-mechanics.md, trigger-principles.md, schemas.md)을 **전부 읽어 컨텍스트에 적재**한다. 이후 step 2~6에서 "→ references/ 참조"로 표기된 지점에서 **재로딩하지 않는다**. 이유: 루프 5회 × 4파일 = 최대 20회 재로딩 → 캐싱으로 4회로 고정. 토큰 절감 ~30%.

---

## step 2: eval 스위트 구성

→ [eval-guide.md](eval-guide.md) 참조 (step 0에서 미로드 시 이 시점에 로드)

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
3. **단계별 프로파일 기록** — 각 실행에서 step_profile 캡처 → timing.json에 저장. → [schemas.md](schemas.md) §step_profile 참조 (이 시점에 로드)
4. 90%+면 사용자에게 계속할지 확인.

---

## step 3-bis: 라이브 대시보드 생성 (v6.4 — 절대 규칙 #7)

baseline 점수가 results.tsv에 기록된 직후, 4 진입 전에 **반드시** 대시보드를 띄운다.

```bash
LAB=/sessions/{session-id}/autoloop-lab/{skill-name}
python /sessions/{session-id}/mnt/.claude/skills/autoloop/scripts/gen_dashboard.py \
  init "$LAB" --skill "{skill-name}" --baseline {baseline_pct}
# 산출: $LAB/dashboard.html, $LAB/results.json
# 가능 시 자동 오픈:
open "$LAB/dashboard.html" 2>/dev/null || \
  echo "대시보드 경로: $LAB/dashboard.html — 브라우저에서 직접 여세요"
```

**왜 step 3-bis인가:** 형이 자리를 비워도 진행을 시각으로 추적할 수 있게. results.tsv는 텍스트라 안 봄. autoresearch에서 흡수한 가장 큰 가치.

**대시보드 동작:**
- 10초마다 results.json fetch → 점수 progression 라인차트 갱신
- experiment별 색상바 (green=keep, red=discard, blue=baseline)
- per-eval breakdown (어느 eval이 자주 통과/실패하는지)
- 상태 pill (running·complete·idle)

대시보드 미동작 환경(Linux headless·서버 등)이면 `dashboard.html` 경로만 안내해도 OK. 파일 자체 생성은 필수.

---

## step 4: 실험 루프

autoloop의 핵심. 시작하면 멈출 때까지 자율 실행한다.

### 루프 구조

```
4a. 실패 분해 (+ 이전 판정 이유 흡수 + 프로파일 병목 확인)
4b. 변이 생성 — 1후보 집중형 (대안키워드 저축)
4c. 실행+채점 — 병렬 가능 시 병렬, 불가 시 순차
4d. keep/discard + git commit/reset + 프로파일 기록 + changelog 백업
4e. 정체 시 RAR + 귀인 검증
```

각 메커니즘 상세: → [loop-mechanics.md](loop-mechanics.md) 참조 (step 4 진입 시 로드)

### 4a: 실패 분해

eval×input 매트릭스 + 이전 판정 이유 흡수. step_profile에서 토큰·시간 병목 확인 → 다음 변이 우선순위에 반영.

| α | 분석 깊이 |
|---|----------|
| = 1.0 | 매트릭스 자동 (코드) |
| ≥ 0.5 | 매트릭스 + 수동 분석 |
| < 0.5 | + grep 수치화 |

### 4b: 변이 생성 — 1후보 집중형

**모든 α에서 후보 1개.** 탐색 폭은 대안키워드가 changelog→RAR 경로로 보존.

```
실패: [E{N}] {eval 이름} — {실패 증상 1문장}
이전: {판정 이유 1문장}

이 실패를 해결하는 변이 1개를 제안하라.
- 변경: [어디를 어떻게]
- 약점: [이 변이가 실패할 수 있는 이유 1개]  ← α=1.0이면 생략
- 대안 키워드 2개 (미실행 후보 복원용)       ← changelog에 저장
```

변이 내용 채우기: → [trigger-principles.md](trigger-principles.md) 참조 (4b 최초 진입 시 로드)

한 번에 한 가지(1 eval 타겟, 1 가설). 형식 실패→형식 먼저. 2회 discard→내용으로 전환. changelog에 "타겟: E[N], 가설: [1문장], 대안: [키워드1, 키워드2]" 기록.

### 4c: 실행+채점 — 병렬 필수

| 조건 | 실행 방식 |
|------|----------|
| **기본 (MUST)** | N회 실행을 **동시 Agent spawn**. auto_scorable은 즉시 코드 채점, 내용적만 LLM. **병렬이 가능한 환경에서 순차 실행 = FAIL** |
| 순차 폴백 (제한적) | Agent tool이 병렬 spawn을 지원하지 않는 환경에서만 허용. 폴백 사유를 changelog에 명시 |

| eval 유형 | 채점 방식 |
|-----------|----------|
| auto_scorable=yes | 코드 자동 채점. LLM 0 |
| 형식적 + auto_scorable=no | 실행+채점 합침 1회 |
| 내용적 (α < 0.5만) | 실행 Agent 1회 + 별도 Agent 2회 (다수결) |

**Scorer 앵커링:** eval 프리앰블 복사 / Agent 격리 / drift 감지(3실험 연속 2:1→재작성) / auto_scorable→코드 필수.

### 4d: keep/discard + 프로파일 + 백업 + JSON 갱신

- **keep:** `git commit -m "exp-{N}: keep — E{target} — {가설}"` + step_profile 기록 + **changelog 백업** (→ step 5 참조)
- **discard:** `git reset --hard HEAD~1` + step_profile 기록
- **판정 이유:** changelog에 1문장 + 대안키워드 → 다음 4a 입력
- **대시보드 갱신 (v6.4 필수):**
  ```bash
  python /sessions/{session-id}/mnt/.claude/skills/autoloop/scripts/gen_dashboard.py update "$LAB"
  ```
  results.tsv에 행 append 직후 호출. 미호출 = 대시보드 멈춰있는 것처럼 보임.

### 4e: RAR + 귀인 검증

3회 연속 discard 시 **2단계 진단**. → [loop-mechanics.md](loop-mechanics.md) §8 상세 참조

```
① 귀인 검증: 지목 구간→원본 복원+재실행. 점수 무변화→귀인 틀림→매트릭스 재분석
② RAR: changelog→시도/미시도 매트릭스. 대안키워드 미시도 우선. keep 패턴 추출
```

**Scorer 노이즈:** α < 1.0일 때만 추적. 3실험 연속 일치도 < 80% → 정지 + eval 재설계.

### 자동 종료 조건

- 사용자가 수동 중지
- 예산 상한 도달
- 3회 연속 95%+ pass rate
- **iteration 하드캡:** 예산 미지정 시 기본 상한 = α별 권장 실험수 × 3 (turbo: 6회, light: 9회, full: 15회). 상한 도달 시 자동 종료 + 결과 보고. 형이 명시적으로 연장 지시한 경우만 추가 실행

**절대 멈추지 마라.** 루프가 시작되면 사용자에게 계속할지 물으며 일시정지하지 않는다. **단, 하드캡 도달 시 종료는 멈춤이 아니라 완료다.**

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

→ [schemas.md](schemas.md) 참조 (이 시점에 로드)

### 결과 보고

루프 종료 시:
1. 대시보드 finish: `python scripts/gen_dashboard.py finish "$LAB"` → status=complete
2. ①점수 요약(Baseline→최종) ②실험 횟수+Keep율 ③효과적 변경 Top 3 ④남은 실패 ⑤git log ⑥프로파일 요약(병목 단계+총 토큰)
3. dashboard.html 경로 다시 안내 (형이 닫았을 수 있음)

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

세션 실험장 루트에 `handoff.json` 생성. → [schemas.md](schemas.md) §handoff.json 참조

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
  "top_changes": [...],
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
