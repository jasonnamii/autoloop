# CHANGELOG — autoloop

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
