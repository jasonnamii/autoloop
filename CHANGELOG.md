# CHANGELOG — autoloop

## v6.4 — 2026-04-28
### Added (autoresearch venom — github.com/olelehmann1337/autoresearch-skill 흡수)
- **`references/dashboard-template.html`** — Chart.js 라이브 HTML 대시보드. 10초 auto-refresh, 점수 progression 차트, keep(green)/discard(red)/baseline(blue) 색상바, per-eval breakdown, 상태 pill.
- **`scripts/gen_dashboard.py`** — `init`/`update`/`finish` 3 서브커맨드. results.tsv 파싱 → results.json 변환. lab 디렉토리에 dashboard.html 복사 + open.
- **§변이 가드 4종** (`references/loop-mechanics.md`) — bad mutation 즉시 폐기 룰: ①전체 재작성 ②다중룰 동시추가 ③길이 팽창만 ④모호 지시. step 4b 자체 점검 1줄 포함.
- **§탈출구 4갈래** (`references/loop-mechanics.md`) — RAR 후에도 막힐 때: ①재읽기 ②near-miss 결합 ③제거 방향 ④단순화 keep. ②는 탈출구에서만 다중 변이 일시 허용.
- **좋은 autoloop 실행 7체크** (`references/eval-guide.md`) — autoresearch "the test" 7항목 흡수.
- **SKILL.md 절대 규칙 #6·#7 추가** — 변이 가드·라이브 대시보드 강제 게이트.
- **step 3-bis 신설** (`references/execution-steps.md`) — baseline 직후 대시보드 init 강제. 4d마다 update 호출 강제.

### Changed
- description: v6.3 → v6.4 + P1에 `dashboard, 대시보드` 추가, P3에 `live dashboard`, P5에 `dashboard.html`.
- Gotchas 2건 추가: 대시보드 미생성·results.json 미갱신 함정.

### Context
신규 외부 스킬(autoresearch-skill, Karpathy autoresearch 어댑팅) 진단 결과 4종 베놈 식별:
- A급 #1 HTML 라이브 대시보드 (형 사용성 ↑↑) → 신설
- B급 #2 bad mutation 카탈로그 → loop-mechanics §변이 가드
- B급 #3 탈출구 처방 → loop-mechanics §탈출구
- B급 #4 eval-guide 차분 머지 → eval-guide 7체크 추가

기능 로직 무변경 — 가시성·가드만 강화. autoloop의 절대 규칙 5개·α 연속체·세션 분리·handoff·자체점검은 그대로 유지(autoresearch엔 없는 강점).

---

## v6.3 — 2026-04-17
### Changed
- **허브 축소 (⑤-1 비대 처방):** step 0~7 상세 프로토콜을 `references/execution-steps.md`로 분리. 허브 SKILL.md 15.3KB → ~5KB 목표.
- **본질 규칙 명시 (⑦-2):** 허브 상단에 "절대 규칙" 섹션 신설. 기존 "절대 금지" 단문을 구조화.
- **P1 키워드 본문 보강 (②-2):** description P1 키워드(optimize·improve·benchmark) 중 본문 미등장분을 핵심 작업·자동 종료 문구에 자연 등장시킴.

### Added
- `scripts/self_check_cases.json` — 3개 baseline 케이스 (α 판정·baseline 스킵·하드캡 종료). skill-doctor ⑦-3 처방 (패키징 관례상 `evals/*` 제외되므로 `scripts/`에 배치).
- `scripts/self_check.py` — 크기·스포크·cases·트리거·invariant 점검. skill-doctor ⑧-1 처방.
- `CHANGELOG.md` — 변경이력 추적 시작. skill-doctor ⑦-4 처방.

### Context
skill-doctor 진단 결과(🟠 69.4/100) 처방 적용. 레드플래그 3건(⑤-1·⑦-3·⑧-1) 해소 목표. 기능 로직 무변경 — 구조·자기진단·이력 추가만.

---

## v6.2 — prior
- reference 1회 캐싱 (step 1), iteration 하드캡 도입.

## v6.1 — prior
- 스킬빌더 핸드오프(handoff.json) step 7 추가.

## v6.0 — prior
- 코워크 세션 네이티브 전환. 볼트 Read(in) + Write(out) 2회로 축소. changelog 볼트 백업.

## v5.0 — prior
- α 연속체 모드. 1후보 집중형 변이 + 대안키워드. 병렬 실행. 귀인 검증. 단계별 프로파일.
