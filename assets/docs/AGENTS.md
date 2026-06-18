<!--## English-Only & Vocabulary Enrichment Mode (STRICT)

- **Input must be English**: Non-English → reply only: "🚫 English, motherfucker, do you speak it?"
- **Output Format**: Only when responding directly to a **user message** (skip for skill/tool outputs and command invocations like `/foo`), start with a dedicated English Teacher section formatted EXACTLY like this:
  
  # 🎓 English Teacher

  - 🔍 **Original**: "<original text>"
  - ✨ **Corrected**: "<corrected text with bold edits>"

  ---

  💡 **Also natural**:
  - "<alternative 1>" — *brief note on tone/nuance*
  - "<alternative 2>" — *brief note on tone/nuance*

  ---

- **Visual Separation**: Always include the `---` horizontal rules exactly as shown above to cleanly separate the correction, the vocabulary enrichment, and your actual conversational response.
- Then converse. Correct + enrich before answering.-->

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

# graphify
- **graphify** (`~/.claude/skills/graphify/SKILL.md`) - any input to knowledge graph. Trigger: `/graphify`
When user types `/graphify`, invoke Skill tool with `skill: "graphify"` before anything else.
