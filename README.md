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
├── antigravity.json # links assets → ~/.gemini/config
├── claude.json      # links assets → ~/.claude
├── opencode.json    # links assets → ~/.config/opencode
└── zed.json         # links assets → ~/.config/zed
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
  "links": [{ "from": "assets/docs/AGENTS.md", "to": "AGENTS.md" }],
  "external_links": []
}
```

Then run `bash scripts/link.sh cursor`.

## Commands

```bash
bash scripts/link.sh              # link all tools
bash scripts/link.sh claude       # link specific tools
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

### context-mode

Repo: https://github.com/mksglu/context-mode

Claude Code (terminal, MCP-only — no hooks/auto-routing; run `/plugin marketplace add mksglu/context-mode` + `/plugin install context-mode@context-mode` inside a Claude Code session for the full plugin):

```bash
claude mcp add context-mode -- npx -y context-mode
```

opencode (add to `opencode.json`):

```json
{
  "$schema": "https://opencode.ai/config.json",
  "plugin": ["context-mode"]
}
```

OMP (Oh My Pi):

```bash
omp plugin install context-mode
```

### henrilhos/skills

Third-party skill collection.

- Repo: https://github.com/henrilhos/skills

### mattpocock/skills

Real-engineering skills: TDD, planning, domain modeling, codebase handoffs.

- Repo: https://github.com/mattpocock/skills

Install via skills.sh (any agent):

```bash
npx skills@latest add mattpocock/skills
```

Or as a Claude Code plugin:

```bash
claude plugin marketplace add mattpocock/skills
claude plugin install mattpocock-skills@mattpocock-skills
```

### Ponytail
Lazy-senior-dev ruleset — forces the minimal solution that works.

- Repo: https://github.com/DietrichGebert/ponytail

Claude Code:

```bash
claude plugin marketplace add DietrichGebert/ponytail
claude plugin install ponytail@ponytail
```

opencode:

```bash
git clone https://github.com/DietrichGebert/ponytail ~/ponytail
mkdir -p ~/.config/opencode/plugins ~/.config/opencode/command
ln -sf ~/ponytail/.opencode/plugins/ponytail.mjs ~/.config/opencode/plugins/
ln -sf ~/ponytail/.opencode/command/* ~/.config/opencode/command/
```

### LSP

Language servers installed via npm + Claude Code plugins.

PHP (intelephense):

```bash
npm install -g intelephense
/plugin install php-lsp@claude-plugins-official
```

TypeScript:

```bash
npm install -g typescript-language-server typescript
/plugin install typescript-lsp@claude-plugins-official
```
