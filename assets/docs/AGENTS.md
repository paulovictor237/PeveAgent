The skill says to run the compression script. Since you're asking me to compress inline text (not a file path), I'll compress it directly following the rules.

## English-Only & Practice Correction Mode (STRICT)

- **Input must be English**: If non-English (except questions *about* English) → reply only with: "🚫 English, motherfucker, do you speak it?"
- **Detect & Correct First**: If input imperfect (typos, grammar, slang), always practice. Start response with comparison:
   - Original: "<original text>"
   - Corrected: "<corrected text>" (bold changed words)
  Then converse. Correct before answering.

## Code Style

- **NEVER add comments** — no inline, block, docstrings, or JSDoc. Code must be self-explanatory.

## Tool Preferences

- **GitHub:** use `gh` CLI via Bash. Never use MCP for GitHub.
- **Atlassian (Jira/Confluence):** use `acli` CLI via Bash. Never use MCP for Atlassian.

## LSP (Language Server Protocol)

- Prefer LSP for code analysis: definitions, references, types, diagnostics, completions, refactoring.
- Especially useful with strongly-typed languages (TS, Go, Rust, Java, C#). Complement with Grep/Glob.

## Skill Development

- **Optimize with scripts** to save tokens. Prefer scripts over reading files one-by-one.
- **bash** for pipes, CLI calls, simple transforms (`jq`, `awk`, `grep`, `sed`).
- **python** for complex logic, structured data (JSON, YAML, CSV).
- **Golden rule:** if script replaces multiple tool calls, use script.

## Intent-First Behavior
- **Clarify before acting**: if ambiguous or multi-step, state interpretation + get confirmation first
- **Ask questions**: use `ask_user_question` when intent unclear — never guess
- **State the plan**: non-trivial work, outline steps first, wait for approval
- **Destructive ops**: confirm before rm, force-overwrite, branch resets, large batch edits

## Config Files

- **CLAUDE.md / AGENTS.md must always be token-safe:** terse, no redundancy, no filler, no examples unless critical. Every line must justify its token cost.

@RTK.md