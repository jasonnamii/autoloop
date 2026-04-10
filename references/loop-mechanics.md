# 루프 메커니즘 — 4축 레퍼런스

autoloop의 실험 루프를 구동하는 8개 메커니즘과 적용 지점.

trigger-principles.md가 "변이 **내용**을 무엇으로 채울지" 결정한다면, 이 문서는 "루프를 **어떻게** 돌릴지" 결정한다. 두 문서는 상호 보완이지 대체가 아니다.

**v4.0 변경:** 단일 프롬프트 합침(Tree of Thoughts + pre-reflection + Debate → 1호출), post-reflection 흡수, turbo 모드 추가, auto_scorable eval 코드 채점.

---

## 4축 구조

| 축 | 역할 | 포함 메커니즘 |
|----|------|-------------|
| **탐색** | 해 공간을 넓게 살핀다 | Tree of Thoughts, ReAct |
| **검증** | 결과를 다각도로 확인한다 | Self-Consistency, Debate |
| **구조화** | 문제를 정밀하게 분해한다 | Decomposition, Constraint Injection |
| **압축** | 불필요를 제거하고 개선한다 | Reflection Loop, RAR |

---

## 메커니즘별 적용 지점

### 1. Tree of Thoughts (분기 탐색)

**원리:** 한 경로가 아니라 여러 사고 가지를 생성 → 평가 → 가지치기. 로컬 최적 해를 탈출한다.

**autoloop 적용 — step 4b (v4.0: 단일 프롬프트로 합침):**

v3.1에서는 후보 생성, pre-reflection, debate가 각각 별도 호출이었다. v4.0에서는 단일 프롬프트 1회 호출로 합친다:

```
실패 패턴: [4a에서 도출]
이전 실험 판정 이유: [changelog에서 가져옴]

아래를 한 번에 수행하라:
1. 변이 후보 3개 (각 1문장 설명)
2. 각 후보 예상 약점 1문장
3. 각 후보 실패 반론 1문장
4. 약점+반론 최소인 후보 선택 + 근거
```

이 합침으로 full 모드 변이 탐색이 3호출 → 1호출.

**모드별 적용:**

| 모드 | 후보 수 | pre-reflection | debate | 호출 |
|------|---------|---------------|--------|------|
| turbo | 1개 | 없음 | 없음 | 1 |
| light | 1개 | 약점 1문장 | 없음 | 1 |
| full | 2-3개 | 각 약점 1문장 | 각 반론 1문장 | 1 (합침) |

나머지 후보는 changelog에 "미실행 후보"로 기록 — 후속 실험에서 재활용 가능.

**비용:** full 모드 기준 토큰은 v3.1과 유사(내용량 동일), 호출 수만 3→1.

---

### 2. ReAct (행동 루프)

**원리:** 생각 → 행동(도구 호출) → 결과 → 다시 생각. 정적 추론을 동적 문제 해결로 전환한다.

**autoloop 적용 — step 4a 강화:**
- 실패 분석에서 "출력을 읽고 판단"만 하지 않는다
- 실패한 출력을 grep/검색해서 패턴을 수치화한다
  - 예: "6개 출력 중 5개에서 '결론' 섹션 누락" → 구체적 타겟
  - 예: "평균 단어 수 850, 목표 500 이하" → 정량 근거
- 수치 근거가 있는 실패만 변이 대상으로 삼는다
- **v4.0 추가:** auto_scorable eval의 실패는 코드 출력에서 자동으로 수치화됨. LLM 분석 불필요.

**turbo/light:** auto_scorable 결과만 확인 (수동 분석 최소화).
**full:** + LLM grep 수치화 분석.

---

### 3. Self-Consistency (다수결 채점)

**원리:** 동일 문제를 여러 경로로 풀이 → 결과 다수결 선택. 단일 추론 오류를 제거한다.

**autoloop 적용 — step 4c:**

v4.0에서 채점 방식이 eval 유형에 따라 분기:

| eval 유형 | auto_scorable | 채점 방식 | 다수결 |
|-----------|--------------|----------|--------|
| 형식적 | yes | 코드 자동 채점 (grep/wc/regex) | 불필요 (결정적) |
| 형식적 | no | 실행+채점 합침 (1회) | 불필요 |
| 내용적 | no | 실행 Agent 1회(1차 채점) + 별도 Agent 2회(2·3차) | 2/3 합의 |

- 3회 채점 중 3:0 불일치(전원 의견 다름)면 해당 eval 자체를 재검토 대상으로 플래그.

**turbo:** auto_scorable only → 코드 채점. 다수결 불필요. LLM 채점 호출 0.
**light:** 모든 eval 1회 채점 (auto_scorable은 코드, 나머지는 실행+채점 합침).
**full:** 내용적 eval만 3회 다수결.

**비용:** v3.1 대비 auto_scorable eval 수만큼 LLM 채점 호출 감소.

---

### 4. Debate / Adversarial (내부 토론)

**원리:** 반대 입장 생성 → 논쟁 → 통합. 편향을 제거하고 논리를 강화한다.

**autoloop 적용 — step 4b (v4.0: Tree of Thoughts와 합침):**

v3.1에서는 별도 호출이었으나, v4.0에서는 단일 프롬프트 내의 "각 후보 실패 반론" 단계로 통합. 반론이 가장 약한(= 방어가 쉬운) 후보를 선택한다. changelog에 선택 근거와 탈락 후보의 반론을 기록한다.

**turbo/light:** 생략. pre-reflection이 간이 대체 (light) 또는 없음 (turbo).
**full:** 단일 프롬프트 내에서 실행.

---

### 5. Decomposition (문제 분해)

**원리:** 큰 문제 → 독립 서브문제로 분리 → 병렬 해결 → 통합. 복잡도를 감소시킨다.

**autoloop 적용 — step 4a:**
- 실패를 "eval × test-input" 매트릭스로 분해한다

  ```
            input-1  input-2  input-3
  eval-1      ✓        ✗        ✓
  eval-2      ✗        ✗        ✓
  eval-3      ✓        ✓        ✓
  ```

- 매트릭스에서 패턴을 읽는다:
  - 특정 eval이 전 입력에서 실패 → eval 자체의 문제 or 스킬의 근본 결함
  - 특정 입력에서만 실패 → 그 입력 유형에 대한 처리 부족
  - 특정 eval×입력 조합만 실패 → 정밀 타겟팅 가능

**v4.0 추가:** auto_scorable eval의 매트릭스는 코드 채점 결과에서 자동 생성. LLM 분석은 내용적 eval 패턴에만 집중.

**turbo:** 매트릭스 자동 생성 (코드). 분석도 자동.
**light:** 매트릭스 생성은 유지 (비용 거의 없음). 분석 깊이만 축소.
**full:** 매트릭스 + 패턴 분석 (LLM).

---

### 6. Constraint Injection (제약 주입)

**원리:** 의도적으로 규칙 삽입. 산출물의 구조적 완성도를 올린다.

**autoloop 적용 — 기존 trigger-principles.md 그대로 계승:**
- 실패 패턴 → 사고원리 매핑표에서 원리 추출 → 스킬에 1-2문장 주입
- 변경 없음. v2에서 구현됨.

**추가:** 주입 후 다음 실험에서 해당 eval이 개선됐는지 명시적으로 추적. 개선 없으면 주입 문장을 제거(= 제약이 효과 없었다).

---

### 7. Reflection Loop (자기 비평)

**원리:** 1차 결과 생성 → 스스로 오류/약점 지적 → 수정. 품질을 올린다.

**autoloop 적용 — v4.0 변경:**

**Pre-reflection (변이 전) — step 4b 내:**
- 변이 후보를 생성한 직후, 실행 전에 "이 변이의 예상 약점은?"을 자문한다
- 약점이 치명적이면 실행 없이 폐기 → 실험 낭비 방지
- v4.0에서는 Tree of Thoughts 단일 프롬프트에 통합되어 별도 호출 없음

**Post-reflection (채점 후) — v4.0에서 흡수:**
- v3.1에서는 step 5e에서 별도 LLM 호출로 "왜 이 점수인가?"를 분석했다
- v4.0에서는 이 분석을 **changelog의 "판정 이유" 1문장**으로 축소하고, 다음 실험의 **step 4a(실패 분해) 프롬프트에 "이전 실험 판정 이유"로 포함**한다
- 별도 호출 0 → 기존 호출(4a)에 흡수. 정보 손실 없이 호출 1회 절약
- 이유: post-reflection의 핵심 가치는 "다음 실험에 피드백 전달"이지 "별도 분석 문서 생성"이 아니다

**모드별:**
- turbo: pre-reflection 없음. 판정 이유만 changelog에 기록.
- light: pre-reflection 1문장 (4b 내). 판정 이유 1문장.
- full: pre-reflection 상세 (4b 단일 프롬프트 내). 판정 이유 1문장.

---

### 8. RAR (구조 기반 리트리벌)

**원리:** 기존 정보의 재배열/참조 구조화. 기억 오류를 줄이고 일관성을 높인다.

**autoloop 적용 — 정체 구간 돌파:**
- 3회 연속 discard 또는 점수 정체 시 자동 발동
- changelog를 재분석해서 아래 매트릭스를 생성한다:

  ```
  시도한 변이 유형     | 형식적  | 내용적
  ──────────────────────────────────
  추가 (지시 삽입)     | 3회    | 1회
  수정 (기존 재작성)   | 1회    | 0회
  제거 (불필요 삭제)   | 0회    | 0회
  예시 (in/out 추가)   | 1회    | 0회
  ```

- "0회" 셀이 다음 변이 후보의 우선 탐색 영역이 된다
- 과거 keep된 변이의 공통 패턴도 추출 ("구체적 수치 제시"가 3회 keep → 같은 패턴을 다른 eval에도 적용)

**Scorer 노이즈 매트릭스 (v3.1 유지):** RAR 발동 시 아래도 함께 생성:

  ```
  실험별 scorer 일치도
  exp1: 3/3 (100%)  ← 안정
  exp2: 2/3 (67%)   ← 노이즈 플래그
  exp3: 3/3 (100%)
  ```

- 3실험 연속 scorer 일치도 < 80% → 루프 정지 + eval 재설계 강제
- 특정 eval이 반복적으로 불일치 → 해당 eval을 정지하고 재작성
- 이유: scorer 노이즈가 변이 효과보다 점수 변동을 더 크게 만들면 루프가 무의미해진다
- **v4.0:** auto_scorable eval은 scorer 노이즈가 0이므로 매트릭스에서 제외. 내용적 eval만 추적.

**turbo:** auto_scorable only → scorer 노이즈 매트릭스 불필요. changelog 요약만.
**light:** 정체 시에만 changelog 요약 1회 생성. 매트릭스 생략.
**full:** 매트릭스 + 패턴 추출 + scorer 노이즈 매트릭스.

---

## 모드별 적용 요약

| 메커니즘 | turbo 모드 | light 모드 | full 모드 |
|---------|-----------|-----------|----------|
| Tree of Thoughts | 후보 1개, 약점 없음 | 후보 1개 + 약점 1문장 | 후보 2-3개 + 약점 + 반론 (단일 프롬프트) |
| ReAct | auto_scorable 결과 자동 | 수동 분석 | grep/수치화 분석 |
| Self-Consistency | 코드 채점 (다수결 없음) | 전 eval 1회 채점 | 내용적 eval 3회 채점 |
| Debate | 생략 | 생략 | 단일 프롬프트 내 |
| Decomposition | 매트릭스 자동 | 매트릭스 생성만 | 매트릭스 + 패턴 분석 |
| Constraint Injection | trigger-principles.md | trigger-principles.md | + 효과 추적 |
| Reflection Loop | 판정 이유 1문장만 | pre 1문장 + 판정 이유 | pre 상세(합침) + 판정 이유 |
| RAR | changelog 요약 | changelog 요약 | 매트릭스 + 패턴 + scorer 노이즈 |

---

## 메커니즘 조합 순서 (실험 루프 내, v4.0)

```
① Decomposition: eval×input 매트릭스로 실패 분해 + 이전 판정 이유 흡수  [step 4a]
② ReAct: 실패 출력 grep/수치화 (auto_scorable은 자동)                   [step 4a]
③ Constraint Injection: trigger-principles.md에서 원리 탐색               [step 4b 준비]
④ Tree of Thoughts + Reflection(pre) + Debate: 단일 프롬프트             [step 4b]
⑤ 실행 + Self-Consistency: 실행+채점 합침 (auto_scorable은 코드)         [step 4c]
⑥ keep/discard + 판정 이유 기록 (post-reflection 흡수)                   [step 4d]
⑦ RAR: (정체 시만) changelog 재분석                                       [step 4e]
```

v3.1 대비 ④가 3호출→1호출, ⑤가 N+1→N호출, ⑥이 1호출→0호출(기록만).
이 순서가 autoloop step 4의 내부 구조다.
