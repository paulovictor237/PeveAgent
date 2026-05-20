# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Repo Is

PeveAgent is a **config hub** — a single canonical source for skills, agents, commands, and settings across multiple AI tools (Claude Code, Pi/OpenCode, Cursor, Zed). It uses symlinks to deploy configs from `assets/` into each tool's home directory.

## Core Commands

```bash
bash scripts/link.sh                  # Link all tools
bash scripts/link.sh claude pi        # Link specific tools only
bash scripts/link.sh --dry-run        # Preview without changes
bash scripts/link.sh --reverse        # Pull live files back from targets, then re-link
```

No build step. No test suite. This is a config hub, not compiled software.

## Architecture

**Hub-and-spokes**: `assets/` is the canonical source. `tools/*.json` manifests define what links where. `scripts/link.sh` is idempotent and creates `.bkp` backups before overwriting.

```
assets/
├── skills/          # Claude Code skills (each: SKILL.md + scripts/)
├── agents/          # Agent definition .md files
├── commands/        # Slash command .md files
├── configs/         # Per-tool config files (claude-settings.json, pi-settings.json, etc.)
├── themes/          # Claude Code themes
├── extensions/      # Pi/OpenCode extensions (TypeScript)
├── marketplace/     # Pre-installed marketplace skills
└── docs/            # AGENT.md (master instructions), RTK.md

tools/               # Symlink manifests: define target_root and files per tool
scripts/
├── link.sh          # Main idempotent linking script
└── send-random-photo-to-simulator.sh
```

## Adding a New Skill

1. Create `assets/skills/skill-name/` with `SKILL.md` (YAML frontmatter + content) and `scripts/` directory
2. Skills auto-link to `~/.claude/skills/` via `tools/claude.json` — no manifest changes needed

## Adding a New Tool

1. Create `tools/toolname.json` with `target_root` and file mapping
2. Run `bash scripts/link.sh toolname`

## Key Config Files

- `assets/configs/claude-settings.json` — Claude Code permissions, hooks, plugins
- `assets/configs/claude-mcp.json` — MCP server definitions
- `assets/docs/AGENT.md` — Master instruction file (synced to `~/.claude/CLAUDE.md`)
- `tools/claude.json` — Defines what gets linked into `~/.claude/`
