# PeveAgent

Multi-tool AI config hub. One canonical source for skills, agents, commands, and settings — symlinked into each AI tool's home directory.

## Structure

```
assets/
├── skills/       # custom skills (tool-agnostic)
├── agents/       # custom agents
├── commands/     # slash commands
├── configs/      # per-tool config files
└── docs/         # AGENTS.md, RTK.md (shared by all tools)

tools/
├── claude.json   # links assets → ~/.claude
├── pi.json       # links assets → pi/agent
├── opencode.json # links assets → ~/.config/opencode
└── zed.json      # links assets → ~/.config/zed
```

`assets/docs/AGENTS.md` is the single instruction file shared by all agent tools. Each tool's manifest maps it to whatever filename that tool expects (`CLAUDE.md`, `AGENTS.md`, etc.).

## Setup

```bash
bash scripts/link.sh
```

Links are idempotent — safe to re-run. Backs up any real file that would be overwritten.

## Adding a new tool

Drop a new manifest in `tools/<toolname>.json`:

```json
{
  "tool": "cursor",
  "target_root": "~/.cursor",
  "links": [
    { "from": "assets/docs/AGENTS.md", "to": "AGENTS.md" }
  ],
  "external_links": []
}
```

Then run `bash scripts/link.sh cursor`.

## Commands

```bash
bash scripts/link.sh              # link all tools
bash scripts/link.sh claude pi    # link specific tools
bash scripts/link.sh --dry-run    # preview without changes
bash scripts/link.sh --reverse    # pull live files back into assets/, then re-link
```

## Tools

### RTK

Token-optimized CLI proxy (60–90% savings).

- Docs: https://www.rtk-ai.app/#install

```bash
curl -fsSL https://raw.githubusercontent.com/rtk-ai/rtk/refs/heads/master/install.sh | sh
```

### ccstatusline

Status line for Claude Code.

```bash
npx -y ccstatusline@latest
```

### Peon Ping

Audio notifications for Claude Code.

```bash
brew install peonping/tap/peon-ping && peon-ping-setup
```
