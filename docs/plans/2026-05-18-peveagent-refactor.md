# PeveAgent Refactoring Plan

Goal: clean dual-agent (Claude Code + Pi/OpenCode) config hub with one canonical source per artifact, no stale files, and obvious structure.

## Target Structure

```
PeveAgent/
├── README.md                          # New: project overview, agent split, setup
├── claude/                            # Claude Code assets → symlinked to ~/.claude/
│   ├── CLAUDE.md                      # was AGENTS.md (canonical Claude instructions)
│   ├── settings.json                  # Claude Code harness config (hooks, permissions, plugins)
│   ├── .mcp.json                      # MCP server definitions
│   ├── RTK.md                         # RTK token optimizer docs
│   ├── skills/                        # Custom Claude Code skills
│   │   ├── atomic-commits/
│   │   ├── cli-github/
│   │   ├── cli-jira/
│   │   ├── db-executor/
│   │   ├── db-queries/
│   │   ├── pr-comments-flow/
│   │   ├── pr-description/
│   │   ├── resolve-conflicts/
│   │   └── smart-brevity/
│   ├── agents/                        # Custom Claude Code agents
│   │   └── planning-workflow-agent.md
│   ├── commands/                      # Slash command definitions
│   │   └── commit-merge.md
│   └── themes/                        # Claude Code themes (from pi/agent/themes/)
│       └── custom-pastel.json
├── pi/                                # Pi/OpenCode agent config and cache
│   └── agent/                         # (unchanged — managed by pi tooling)
├── marketplace/                       # was .agents/skills/ — marketplace-installed skills
│   ├── find-skills/
│   ├── frontend-slides/
│   ├── skill-creator/
│   └── yt-playlist-organizer/
├── .claude/                           # (unchanged — local-only overrides)
├── scripts/
│   ├── link.sh                        # was link-claude.sh — links claude/ → ~/.claude/
│   └── send-random-photo-to-simulator.sh
├── docs/                              # Docs in organized subdirs
│   ├── claude/                        # Claude Code reference docs
│   │   ├── settings-reference.md      # was docs/settings.json
│   │   └── lsp.md
│   ├── pi/                            # Pi/OpenCode reference docs
│   │   ├── cli-tools.md              # was docs/cli-tolls.md
│   │   └── lm-studio.md              # was docs/lm-studio.mdx
│   ├── plans/                         # Feature/spec plans (was docs/superpowers/plans)
│   └── specs/                         # Design specs (was docs/superpowers/specs)
├── AGENTS.md                           # Pi agent instruction file (symlinked to by Pi)
└── .gitignore
```

## Phase 1 — Cleanup (remove dead weight)

### 1.1 Delete stale artifacts
- [ ] Delete `.pytest_cache/` directory
- [ ] Delete `index.html` (stray file)
- [ ] Delete `.agents/skills-bkp/` — 11 stale skills, some duplicated in active sets
- [ ] Delete `docs/superpowers/` (absorbed into `docs/plans/` and `docs/specs/`)
- [ ] Delete `docs/todos.md` (personal todo, not config)

### 1.2 Archive unused files
- [ ] Move `src/opencode.json` to `pi/agent/` or delete if unused
- [ ] Move `src/ccstatusline.json` into `claude/` (status line config for Claude Code)

## Phase 2 — Reorganize Claude Code assets (src/ → claude/)

### 2.1 Create claude/ directory
- [ ] Move `src/AGENTS.md` → `claude/CLAUDE.md`
- [ ] Move `src/settings.json` → `claude/settings.json`
- [ ] Move `src/.mcp.json` → `claude/.mcp.json`
- [ ] Move `src/RTK.md` → `claude/RTK.md`
- [ ] Move `src/skills/` → `claude/skills/`
- [ ] Move `src/agents/` → `claude/agents/`
- [ ] Move `src/commands/` → `claude/commands/`
- [ ] Move `src/ccstatusline.json` → `claude/ccstatusline.json`
- [ ] Move `pi/agent/themes/` → `claude/themes/` (or keep in pi/ if Pi-specific)

### 2.2 Delete old src/ directory
- [ ] After all files moved, remove empty `src/`

## Phase 3 — Consolidate marketplace skills

### 3.1 Rename .agents/skills/ → marketplace/
- [ ] Rename `.agents/skills/` → `marketplace/`
- [ ] Rename `.agents/.skill-lock.json` → `marketplace/.skill-lock.json`
- [ ] Update `link.sh` to link `marketplace/` to `~/.agents/skills/`

## Phase 4 — Consolidate settings/permissions

### 4.1 Merge scattered settings
- [ ] Merge `.claude/settings.local.json` permissions into `claude/settings.json`
- [ ] Merge `.agents/settings.local.json` permissions into `claude/settings.json`
- [ ] Merge `.agents/settings.local.json` into `claude/settings.json`
- [ ] Delete `.claude/settings.local.json` (or keep as gitignored local-only)
- [ ] Delete `.agents/settings.local.json`

### 4.2 Link strategy
- [ ] `claude/settings.json` → `~/.claude/settings.json` (main config)
- [ ] `~/.claude/settings.local.json` stays as gitignored local-only (optional)

## Phase 5 — Rewrite link.sh

### 5.1 Simplify linking script
- [ ] Rename `scripts/link-claude.sh` → `scripts/link.sh`
- [ ] Update variables:
  - `SOURCE_DIR` = project `claude/`
  - `TARGET_DIR` = `$HOME/.claude`
  - `MARKETPLACE_DIR` = project `marketplace/`
  - `MARKETPLACE_TARGET` = `$HOME/.agents/skills`
- [ ] Subdir links: `skills` `agents` `commands` `themes`
- [ ] File links: `CLAUDE.md` `settings.json` `.mcp.json` `RTK.md`
- [ ] Custom links: nothing → everything lives in `claude/`
- [ ] Raw links: `zed.jsonc` → `$HOME/.config/zed/settings.json` (keep separate, Zed is unrelated to Claude)
- [ ] Remove the `src → ~/.agents` raw link — replace with targeted marketplace link

### 5.2 link.sh config block

```bash
ASSETS_DIR="claude"
TARGET_DIR="$HOME/.claude"

SUBDIR_LINKS=(
  "skills:skills"
  "agents:agents"
  "commands:commands"
  "themes:themes"
)

FILE_LINKS=(
  "CLAUDE.md:CLAUDE.md"
  "settings.json:settings.json"
  ".mcp.json:.mcp.json"
  "RTK.md:RTK.md"
)

CUSTOM_LINKS=()

RAW_LINKS=(
  "$PROJECT_DIR/claude/zed.jsonc:$HOME/.config/zed/settings.json"
)

MARKETPLACE_LINK_SRC="$PROJECT_DIR/marketplace"
MARKETPLACE_LINK_DST="$HOME/.agents/skills"
```

## Phase 6 — Fix AGENTS.md duplication

### 6.1 Canonical Pi agent config
The root `AGENTS.md` is read by Pi. Keep it as the canonical source for Pi agent rules at project level. But clarify the relationship:
- [ ] Root `AGENTS.md` = Pi agent instruction (stays, gets cleaned)
- [ ] `claude/CLAUDE.md` = Claude Code instruction (was `src/AGENTS.md`)
- [ ] Remove duplicate content from one to the other — AGENTS.md is for Pi, CLAUDE.md is for Claude

### 6.2 Root AGENTS.md content
Should be Pi-specific as it's read by Pi:
```
# PeveAgent — Pi Agent Context

## Agent Split
- `claude/` → Claude Code config (symlinked to ~/.claude/)
- `pi/agent/` → Pi/OpenCode native config and cache
- `marketplace/` → Shared marketplace-installed skills

## Pi-Specific Instructions
(Keep current rules: English-only, no comments, tool preferences, LSP, skill dev, config files)

@RTK.md
```

## Phase 7 — Docs organization

### 7.1 Reorganize docs/
- [ ] Create `docs/claude/` — move `lsp.md` there
- [ ] Create `docs/pi/` — move `cli-tolls.md` (fix typo: tools), `lm-studio.mdx`
- [ ] Move `docs/superpowers/plans/` → `docs/plans/`
- [ ] Move `docs/superpowers/specs/` → `docs/specs/`
- [ ] Delete `docs/settings.json` (redundant with `claude/settings.json`)
- [ ] Delete `docs/todos.md`

## Phase 8 — README

### 8.1 Create root README.md
Document:
- Project purpose: dual-agent config hub (Claude Code + Pi)
- Directory structure overview
- Setup: `bash scripts/link.sh` creates symlinks
- Skills: where they are, how they get loaded
- Reverse sync: `bash scripts/link.sh --reverse`

## Phase 9 — Update .gitignore

### 9.1 Clean .gitignore
- [ ] Add `node_modules/` to root (pi packages should not be committed)
- [ ] Remove stale entries no longer relevant after refactoring

## Summary of Changes

| From | To | Action |
|------|----|--------|
| `src/AGENTS.md` | `claude/CLAUDE.md` | move |
| `src/settings.json` | `claude/settings.json` | move + merge |
| `src/.mcp.json` | `claude/.mcp.json` | move |
| `src/RTK.md` | `claude/RTK.md` | move |
| `src/skills/*` | `claude/skills/*` | move |
| `src/agents/*` | `claude/agents/*` | move |
| `src/commands/*` | `claude/commands/*` | move |
| `src/ccstatusline.json` | `claude/ccstatusline.json` | move |
| `pi/agent/themes/*` | `claude/themes/*` | move |
| `.agents/skills/*` | `marketplace/*` | rename |
| `.agents/.skill-lock.json` | `marketplace/.skill-lock.json` | move |
| `.agents/skills-bkp/` | — | delete |
| `.agents/settings.local.json` | merged into `claude/settings.json` | merge + delete |
| `.claude/settings.local.json` | merged into `claude/settings.json` | merge + delete |
| `.pytest_cache/` | — | delete |
| `index.html` | — | delete |
| `docs/superpowers/` | `docs/plans/` + `docs/specs/` | split + move |
| `docs/settings.json` | — | delete |
| `docs/todos.md` | — | delete |
| `scripts/link-claude.sh` | `scripts/link.sh` | rewrite + rename |
| — | `README.md` | create |
| — | `.gitignore` | clean stale entries |

## File-Level Details

### Files that stay unchanged
- `pi/agent/**` — managed by pi tooling
- `.claude/` — local-only, auto-managed by Claude Code
- `.git/` — git repo
- `scripts/send-random-photo-to-simulator.sh`

### Skills inventory after refactoring
**claude/skills/** (9 custom, canonical):
- atomic-commits, cli-github, cli-jira, db-executor, db-queries,
  pr-comments-flow, pr-description, resolve-conflicts, smart-brevity

**marketplace/** (4 installed):
- find-skills, frontend-slides, skill-creator, yt-playlist-organizer

**pi/agent/pi-hermes-memory/skills/** (Pi-native, managed by skill tool):
- migrate-pi-agent-to-repo (project-scoped)

### Symlinks created by link.sh
```
~/.claude/CLAUDE.md         → claude/CLAUDE.md
~/.claude/settings.json     → claude/settings.json
~/.claude/.mcp.json         → claude/.mcp.json
~/.claude/RTK.md            → claude/RTK.md
~/.claude/skills/           → claude/skills/
~/.claude/agents/           → claude/agents/
~/.claude/commands/         → claude/commands/
~/.claude/themes/           → claude/themes/
~/.agents/skills/           → marketplace/
~/.config/zed/settings.json → claude/zed.jsonc
```

### What gets removed from symlinks
- **REMOVED:** `src → ~/.agents` (overly broad raw link)
- **REPLACED WITH:** targeted `marketplace → ~/.agents/skills` link
