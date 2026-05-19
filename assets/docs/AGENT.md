## Default Language: English-Only

All user input MUST be in English. Non-English input → reply with block message, do nothing else. Correct user's English first.
Block message: 🚫 English, motherfucker, do you speak it?

**Exception:** questions *about* English (translation, vocabulary, grammar) are answered normally.

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
- **Golden rule:** if a script replaces multiple tool calls, use the script.

## Config Files

- **CLAUDE.md / AGENT.md must always be token-safe:** terse, no redundancy, no filler words, no examples unless critical. Every line must justify its token cost.

@RTK.md
