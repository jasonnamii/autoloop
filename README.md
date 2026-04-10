# Autoloop

**Automated skill optimization loop.**

Execute → Score → Mutate → Keep winners → Repeat. Modes: full (~8 iter), light (~4, default), turbo (~2).

### Example Prompts

```
"Run autoloop on research-frame" → test→execute→score→mutate→repeat
"Optimize this skill" → auto-detect mode based on skill type
```

**Output:** Improved `SKILL.md` + `results.tsv` + `changelog.md`

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

This is one of 25 custom skills. See the full catalog: [https://github.com/jasonnamii/cowork-skills](https://github.com/jasonnamii/cowork-skills)

## License

MIT License — feel free to use, modify, and share.
