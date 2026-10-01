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

## Config Files

- **CLAUDE.md / AGENTS.md must always be token-safe:** terse, no redundancy, no filler, no examples unless critical. Every line must justify its token cost.

# RTK - Rust Token Killer

**Usage**: Token-optimized CLI proxy (60-90% savings on dev operations)

## Meta Commands (always use rtk directly)

```bash
rtk gain              # Show token savings analytics
rtk gain --history    # Show command usage history with savings
rtk discover          # Analyze Claude Code history for missed opportunities
rtk proxy <cmd>       # Execute raw command without filtering (for debugging)
```

## Installation Verification

```bash
rtk --version         # Should show: rtk X.Y.Z
rtk gain              # Should work (not "command not found")
which rtk             # Verify correct binary
```

⚠️ **Name collision**: If `rtk gain` fails, you may have reachingforthejack/rtk (Rust Type Kit) installed instead.

## Hook-Based Usage

All other commands are automatically rewritten by the Claude Code hook.
Example: `git status` → `rtk git status` (transparent, 0 tokens overhead)

Refer to CLAUDE.md for full command reference.

## Code Style

- **NEVER add comments** — no inline, block, docstrings, or JSDoc. Code must be self-explanatory.

## Minimal Code (code only — never affects conversation tone or explanation length)

Simplest code that works. No over-engineering. Read the code the change touches and trace the real flow first; lazy about the solution, never about understanding.

Stop at the first rung that holds:
1. Needed at all? Speculative → skip (YAGNI).
2. Already in codebase (helper, util, type, pattern)? Reuse.
3. Stdlib? 4. Native platform feature (HTML input, CSS, DB constraint)? 5. Installed dependency? Use it.
6. One line? One line. 7. Only then: minimum that works.

- No unrequested abstractions: no single-impl interface, single-product factory, config for a constant, scaffolding "for later".
- Deletion over addition. Boring over clever. Fewest files, shortest correct diff.
- Bug fix = root cause in the shared function, not a patch per caller.
- Never cut: trust-boundary validation, data-loss error handling, security, accessibility, anything explicitly requested.
- Weigh the implementation before and after writing it: files, lines, new deps, abstractions added. When a heavier option was chosen or a lighter one skipped, state it in one line.

@/Users/paulo.duarte/.codex/RTK.md
