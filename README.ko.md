# 스킬 자동최적화 루프

> 🇺🇸 [English README](./README.md)

**자동화된 스킬 최적화 루프: 실행 → 채점 → 변이 → 반복.**

## 사전 요구사항

- **Claude Cowork 또는 Claude Code** 환경
- **Git** — 최적화 루프 중 버전 추적에 필요

## 목적

autoloop는 수동 개입 없이 스킬 품질을 지속적으로 개선합니다. 지표를 지정하면 autoloop는 반복 전 스킬을 실행, 채점, 변이시킵니다. v4.0은 실행+채점 결합으로 2배 빠릅니다.

## 사용 시점 및 방법

스킬 성능을 최적화할 때 실행하세요. 3가지 모드: full (8 반복, 분석 스킬), light (4 반복, 포맷팅), turbo (2 반복, 자동 채점). 입력: 스킬 + 성공 지표 + 모드. 산출: 변이 이력 및 채점 진행률이 포함된 개선 버전.

## 사용 예시

| 상황 | 프롬프트 | 결과 |
|---|---|---|
| 분석 스킬 최적화 | `"research-frame 정확도 개선. Full 모드."` | 8 반복: 실행→채점→변이→15-20% 성능 향상의 최고 버전 |
| 포맷 정제 | `"deliverable-engine 산출 개선. Light 모드."` | 4 반복: 테스트→가독성 채점→개선→완성 |
| 자동 채점 최적화 | `"코드 채점 최대화. Turbo 모드."` | 2 반복 + 자동 채점; 최고 속도 사이클 |

## 핵심 기능

- 3가지 모드: full/light/turbo (8/4/2 반복)
- 실행+채점 결합으로 2배 속도 향상
- 평가 가능한 지표에 대한 코드 기반 자동 채점
- 단일 프롬프트 변이 진화
- Git 통합: 최적화 스킬 자동 commit
- 완전한 변이 이력 감사 추적

## 연관 스킬

- **[skill-builder](https://github.com/jasonnamii/skill-builder)** — 개선 스킬을 검증에 전달
- **[git-sync](https://github.com/jasonnamii/git-sync)** — 최적화 스킬을 commit 및 push
- **[meta-skill](https://github.com/jasonnamii/meta-skill)** — 최적화 기회 감지

## 설치

```bash
git clone https://github.com/jasonnamii/autoloop.git ~/.claude/skills/autoloop
```

## 업데이트

```bash
cd ~/.claude/skills/autoloop && git pull
```

`~/.claude/skills/`에 배치된 스킬은 Claude Code 및 Cowork 세션에서 자동으로 사용할 수 있습니다.

## Cowork 스킬 생태계

25개 이상의 커스텀 스킬 중 하나입니다. 전체 카탈로그: [github.com/jasonnamii/cowork-skills](https://github.com/jasonnamii/cowork-skills)

## 라이선스

MIT 라이선스 — 자유롭게 사용, 수정, 공유하세요.