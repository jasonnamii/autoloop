# autoloop

**Automated skill optimization loop: execute → score → mutate → repeat.**

## Prerequisites

- **Claude Cowork or Claude Code** environment
- **Git** — required for version tracking during optimization loops

## Goal

autoloop continuously improves skill quality without manual intervention. Specify a metric and autoloop executes, scores, and mutates skills across iterations. v4.0 runs 2x faster with combined execution+scoring.

## When & How to Use

Trigger when optimizing skill performance. Three modes: full (8 iterations, analytical skills), light (4, formatting), turbo (2, auto-scorable). Input: skill + success metric + mode. Output: improved version with mutation history and score progression.

## Use Cases

| Scenario | Prompt | What Happens |
|---|---|---|
| Optimize analytical skill | `"Improve research-frame accuracy. Full mode."` | 8 iterations: execute→score→mutate→best version with 15-20% lift |
| Format refinement | `"Tighten deliverable-engine output. Light mode."` | 4 iterations: test→score readability→improve→finalize |
| Auto-score optimization | `"Maximize code scoring. Turbo mode."` | 2 iterations with auto-scoring; fastest cycle |

## Key Features

- 3 modes: full/light/turbo (8/4/2 iterations)
- Combined execution+scoring for 2x speed
- Code-based auto-scoring when metrics are evaluable
- Single-prompt mutation evolution
- Git integration: auto-commits optimized skill
- Full mutation history audit trail

## Works With

- **[skill-builder](https://github.com/jasonnamii/skill-builder)** — feeds improved skills for validation
- **[git-sync](https://github.com/jasonnamii/git-sync)** — commits and pushes optimized skills
- **[meta-skill](https://github.com/jasonnamii/meta-skill)** — detects optimization opportunities

## Installation

```bash
git clone https://github.com/jasonnamii/autoloop.git ~/.claude/skills/autoloop
```

## Update

```bash
cd ~/.claude/skills/autoloop && git pull
```

Skills placed in `~/.claude/skills/` are automatically available in Claude Code and Cowork sessions.

## Part of Cowork Skills

This is one of 25+ custom skills. See the full catalog: [github.com/jasonnamii/cowork-skills](https://github.com/jasonnamii/cowork-skills)

## License

MIT License — feel free to use, modify, and share.
