## Vocabulary Enrichment Mode

- **Output Format**: Only when the user's phrasing is unusual, awkward, or clearly non-native (skip for clean English, skill/tool outputs, and command invocations like `/foo`), prefix the reply with one inline line, no header, no rule:

  🇺🇸 _"<alternative>"_ — brief tone/nuance note

- Then converse on the next line. Correct + enrich before answering.

## Code Style

- **NEVER add comments** — no inline, block, docstrings, or JSDoc. Code must be self-explanatory.

## Tool Preferences

- **GitHub:** use `gh` CLI via Bash.
- **Atlassian (Jira/Confluence):** use `acli` CLI via Bash.

## LSP (Language Server Protocol)

- Prefer LSP for code analysis: definitions, references, types, diagnostics, completions, refactoring.
- Especially useful with strongly-typed languages (TS, Go, Rust, Java, C#). Complement with Grep/Glob.

## Skill Development

- **Optimize with scripts** to save tokens. Prefer scripts over reading files one-by-one.
- **bash** for pipes, CLI calls, simple transforms (`jq`, `awk`, `grep`, `sed`).
- **python** for complex logic, structured data (JSON, YAML, CSV).
- **Golden rule:** script replaces multiple tool calls → use script.

## Frontend Validation

- **Always use `agent-browser` skill** for screenshots, screen recording, evidence gathering, or validating frontend changes.

## Intent-First Behavior

- **Clarify before acting**: ambiguous or multi-step → state interpretation + confirm first
- **Ask questions**: use `ask_user_question` when intent unclear — never guess
- **State the plan**: non-trivial work → outline steps first, wait for approval
- **Destructive ops**: confirm before rm, force-overwrite, branch resets, large batch edits

## Config Files

- **CLAUDE.md / AGENTS.md must always be token-safe:** terse, no redundancy, no filler, no examples unless critical. Every line must justify its token cost.

@RTK.md
